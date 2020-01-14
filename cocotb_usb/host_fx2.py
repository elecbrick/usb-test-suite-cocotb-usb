import enum
from collections import namedtuple

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, Timer, ClockCycles, NullTrigger
from cocotb.result import ReturnValue, TestFailure
from cocotb.monitors import BusMonitor
from cocotb.utils import get_sim_time

from cocotb_usb.usb.pid import PID
from cocotb_usb.usb.packet import (wrap_packet, token_packet, data_packet,
                                   sof_packet, handshake_packet)
from cocotb_usb.usb.pp_packet import pp_packet

from cocotb_usb.wishbone import WishboneMaster
from cocotb_usb.host import UsbTest
from cocotb_usb.utils import parse_csr,assertEqual
from cocotb_usb import usb

from cocotb_usb.usb_decoder import decode_packet


class RegisterAccessMonitor(BusMonitor):
    """
    Monitors wishbone bus for access to registers in given address ranges.

    Args:
        address_ranges: list of tuples (address_min, address_max), inclusive
    """

    RegisterAccess = namedtuple('RegisterAccess', ['adr', 'dat_r', 'dat_w', 'we'])

    def __init__(self, dut, address_ranges, *args, **kwargs):
        self.address_ranges = address_ranges
        self.dut = dut
        super().__init__(*[dut, *args], **kwargs)

        self.wb_adr = self.dut.wishbone_cpu_adr
        self.wb_dat_r = self.dut.wishbone_cpu_dat_r
        self.wb_dat_w = self.dut.wishbone_cpu_dat_w
        self.wb_we = self.dut.wishbone_cpu_we
        self.wb_cyc = self.dut.wishbone_cpu_cyc
        self.wb_stb = self.dut.wishbone_cpu_stb
        self.wb_ack = self.dut.wishbone_cpu_ack

        self.address_override = None

    @cocotb.coroutine
    def _monitor_recv(self):
        yield FallingEdge(self.dut.reset)

        while True:
            yield RisingEdge(self.clock)

            if self.wb_cyc == 1 and self.wb_stb == 1 and self.wb_ack == 1:
                adr, dat_r, dat_w, we = map(int, (self.wb_adr, self.wb_dat_r, self.wb_dat_w, self.wb_we))
                if self.is_monitored_address(adr):
                    self._recv(self.RegisterAccess(adr, dat_r, dat_w, we))

    def is_monitored_address(self, adr):
        address_ranges = self.address_ranges if self.address_override is None else self.address_override
        for adr_min, adr_max in address_ranges:
            if adr_min <= adr <= adr_max:
                return True
        return False


class FX2USB:
    # implements FX2 USB peripheral outside of the simulation
    # TODO: CRC checks

    class IRQ(enum.IntEnum):
        SUDAV = 1
        SOF = 2
        SUTOK = 3

    class TState(enum.Enum):
        # each transaction (except isosynchronous transfers) has 3 steps,
        # first one is always sent by host
        # read the values as "waiting for X", so TOKEN can be interpreted as idle state
        TOKEN = 1
        DATA = 2
        HANDSHAKE = 3

    #  class TDir(enum.Enum):
    #      OUT = 1  # host -> dev
    #      IN = 2   # dev -> host

    def __init__(self, dut, csrs):
        """
        dut: the actual dut from dut.v (not tb.v)
        """
        self.dut = dut
        self.csrs = csrs

        usb_adr_ranges = [
            (0xe500, 0xe6ff),
            (0xe740, 0xe7ff),
            (0xf000, 0xffff),
        ]
        self.monitor = RegisterAccessMonitor(self.dut, usb_adr_ranges,
                                             name='wishbone', clock=dut.sys_clk,
                                             callback=self.monitor_handler)
        self.reset_state()

    def reset_state(self):
        # host always starts transactions
        self.tstate = self.TState.TOKEN
        # store previous packets of a transaction between invocations
        self.token_packet = None
        self.data_packet = None

    def monitor_handler(self, wb):
        # clear interrupt flags on writes instead of setting register value
        clear_on_write_regs = ['ibnirq', 'nakirq', 'usbirq', 'epirp', 'gpifirq',
                               *('ep%dfifoirq' % i for i in [2, 4, 6, 8])]
        for reg in clear_on_write_regs:
            if reg in self.csrs.keys():  # only implemented registers
                if wb.adr == self.csrs[reg] and wb.we:
                    # use the value that shows up on read signal as last register value
                    last_val = wb.dat_r
                    new_val = last_val & (~wb.dat_w)
                    # we can set the new value now, as at this moment value from wishbone bus
                    # has already been written
                    setattr(self.dut, 'fx2csr_' + reg, new_val)


    def handle_token(self, p):
        # TODO: handle addr/endp token fields
        # it always comes from host

        if p.pid == PID.SOF:
            # update USBFRAMEH:L (FIXME: should also be incremented on missing/garbled frames, see docs)
            frameh, framel = ((p.framenum & 0xff00) >> 8), (p.framenum & 0xff)
            self.dut.fx2csr_usbframeh = frameh
            self.dut.fx2csr_usbframel = framel
            # generate interrupt
            self.assert_interrupt(self.IRQ.SOF)
            # no data/handshake
            self.reset_state()
            return True

        elif p.pid == PID.SETUP:
            self.token_packet = p
            # interrupt generated after successful SETUP packet
            self.assert_interrupt(self.IRQ.SUTOK)
            # clear hsnak and stall bits, TODO: do this without writing data bus? or at least hold cpu clock?
            self.dut.fx2csr_ep0cs = int(self.dut.fx2csr_ep0cs) & (~((1 << 7) | (1 << 0)))
            self.tstate = self.TState.DATA
            return True

        return False

    def handle_data(self, p):
        assert self.token_packet

        tp = self.token_packet
        if tp.pid == PID.SETUP:
            assert tp.endp == 0 and p.pid == PID.DATA0
            self.data_packet = p
            # copy data to SETUPDAT
            for i, b in enumerate(p.data):
                setattr(self.dut, "fx2csr_setupdat%d" % i, b)
            self.assert_interrupt(self.IRQ.SUDAV)
            # ack
            self.to_send = handshake_packet(PID.ACK)
            self.reset_state()
            return True

        return False

    def handle_handshake(self, p):
        assert self.token_packet
        assert self.data_packet
        #  yield NullTrigger()

    @cocotb.coroutine
    def receive_host_packet(self, packet):
        # this is called when host sends data, we should set self.send_to in this method
        p = decode_packet(packet)
        print('p =', end=' '); __import__('pprint').pprint(p)

        # check packet category and decide wheather it is correct for the current state
        if p.category == 'TOKEN':
            if self.tstate != self.TState.TOKEN:
                raise Exception('received %s token in state %s' % (p.pid, self.tstate))

            if not self.handle_token(p):
                self.reset_state() # transactions must be complete, else reset state
        elif p.category == 'DATA':
            if self.tstate != self.TState.DATA:
                raise Exception('received %s token in state %s' % (p.pid, self.tstate))

            if not self.handle_data(p):
                self.reset_state() # transactions must be complete, else reset state
        elif p.category == 'HANDSHAKE':
            if self.tstate != self.TState.HANDSHAKE:
                raise Exception('received %s token in state %s' % (p.pid, self.tstate))

            if not self.handle_handshake(p):
                self.reset_state() # transactions must be complete, else reset state
        else:
            raise NotImplementedError('Received unhandled %s token in state %s' % (p.pid, self.tstate))

        yield ClockCycles(self.dut.sys_clk, 1)

    @cocotb.coroutine
    def expect_device_packet(self, timeout):
        #  #  if self.tstate == self.TState.HANDSHAKE:
        #  self.monitor.address_override = [(0xe6a0, 0xe6a0)] # ep0cs
        #  reg = yield self.monitor.wait_for_recv(timeout)
        yield NullTrigger()
        to_send = self.to_send
        self.to_send = None
        return to_send

    def assert_interrupt(self, irq):
        print('FX2 interrupt: ', irq)
        if irq == self.IRQ.SUDAV:
            self.dut.fx2csr_usbirq = int(self.dut.fx2csr_usbirq) | (1 << 0)
        elif irq == self.IRQ.SOF:
            self.dut.fx2csr_usbirq = int(self.dut.fx2csr_usbirq) | (1 << 1)
        elif irq == self.IRQ.SUTOK:
            self.dut.fx2csr_usbirq = int(self.dut.fx2csr_usbirq) | (1 << 2)


class UsbTestFX2(UsbTest):
    """
    Host implementation for FX2 USB tests.
    It is used for testing higher level USB logic of FX2 firmware,
    instead of testing the USB peripheral. Wishbone data bus is used
    to intercept USB communication at register level.
    """
    def __init__(self, dut, csr_file, **kwargs):
        self.dut = dut

        self.clock_period = 20830  # ps, ~48MHz
        cocotb.fork(Clock(dut.clk, self.clock_period, 'ps').start())

        self.wb = WishboneMaster(dut, "wishbone", dut.clk, timeout=20)
        self.fx2_usb = FX2USB(self.dut.dut, parse_csr(csr_file))

    @cocotb.coroutine
    def wait_cpu(self, clocks):
        yield ClockCycles(self.dut.dut.oc8051_top.wb_clk_i, clocks, rising=True)

    @cocotb.coroutine
    def wait(self, time, units="us"):
        yield super().wait(time // 10, units=units)

    @cocotb.coroutine
    def reset(self):
        self.address = 0
        self.dut.reset = 1
        yield ClockCycles(self.dut.clk, 10, rising=True)
        self.dut.reset = 0
        yield ClockCycles(self.dut.clk, 10, rising=True)

    @cocotb.coroutine
    def port_reset(self, time=10e3, recover=False):
        yield NullTrigger()

        self.dut._log.info("[Resetting port for {} us]".format(time))

        #  yield self.wait(time, "us")
        yield self.wait(1, "us")
        self.connect()
        if recover:
            #  yield self.wait(1e4, "us")
            yield self.wait(1, "us")

    @cocotb.coroutine
    def connect(self):
        yield NullTrigger()

    @cocotb.coroutine
    def disconnect(self):
        """Simulate device disconnect, both lines pulled low."""
        yield NullTrigger()
        self.address = 0

    # Host->Device
    @cocotb.coroutine
    def _host_send_packet(self, packet):
        yield self.fx2_usb.receive_host_packet(packet)

    # Device->Host
    @cocotb.coroutine
    def host_expect_packet(self, packet, msg=None):
        result = yield self.fx2_usb.expect_device_packet(timeout=1e9) # 1ms max

        if result is None:
            current = get_sim_time("us")
            raise TestFailure(f"No full packet received @{current}")

        # Check the packet received matches
        expected = pp_packet(wrap_packet(packet))
        actual = pp_packet(wrap_packet(result))
        nak = pp_packet(wrap_packet(handshake_packet(PID.NAK)))
        if (actual == nak) and (expected != nak):
            self.dut._log.warn("Got NAK, retry")
            yield Timer(self.RETRY_INTERVAL, 'us')
            return
        else:
            self.retry = False
            assertEqual(expected, actual, msg)
