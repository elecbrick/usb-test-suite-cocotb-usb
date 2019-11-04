# The MIT License (MIT)
#
# Copyright (c) 2017 Scott Shawcroft for Adafruit Industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import struct

from cocotb_usb.descriptors import Descriptor
from cocotb_usb.utils import getVal

"""
CDC specific descriptors
========================

This PDF is a good reference:
    https://cscott.net/usb_dev/data/devclass/usbcdc11.pdf

* Author(s): Scott Shawcroft
"""


class CDC(Descriptor):
    """Base class for storing common CDC definitions."""

    class Type:
        DEVICE = 0x02
        COMM = 0x02
        DATA = 0x0A

    class Subtype:
        HEADER = 0x00
        CM = 0x01
        ACM = 0x02
        DLM = 0x03
        TR = 0x04
        TCLSRC = 0x05
        UNION = 0x06
        CS = 0x07
        TOM = 0x08
        USBT = 0x09
        NCT = 0x0A
        PUF = 0x0B
        EU = 0x0C
        MCM = 0x0D
        CAPIC = 0x0E
        EN = 0x0F
        ATMN = 0x10
        # 0x11-0xFF Reserved (future use)

    class Subclass:
        UNUSED = 0x00  # Only for Data Interface Class
        DLCM = 0x01
        ACM = 0x02  # Abstract Control Model
        TCM = 0x03
        MCCM = 0x04
        CCM = 0x05
        ETH = 0x06
        ATM = 0x07
        # 0x08-0x7F Reserved (future use)
        # 0x80-0xFE Reserrved (vendor-specific)

    class Protocol:
        NONE = 0x0
        V25TER = 0x01   # Common AT commands
        # Many other protocols omitted.


class Header(CDC):
    """Descriptor representing start of CDC class-specific section."""
    FORMAT = "<BBB" + "H"

    def __init__(self,
                 bcdCDC,
                 bLength=struct.calcsize(FORMAT),
                 bDescriptorType=Descriptor.Types.CLASS_SPECIFIC_INTERFACE,
                 bDescriptorSubtype=CDC.Subtype.HEADER
                 ):
        self.bLength = bLength
        self.bDescriptorType = bDescriptorType
        self.bDescriptorSubtype = bDescriptorSubtype
        self.bcdCDC = bcdCDC

    def notes(self):
        return [str(self)]

    def __bytes__(self):
        """
        >>> h = Header(bcdCDC=0x0110)
        >>> bytes(h)
        b'\\x05$\\x00\\x10\\x01'
        >>> h.get()
        [5, 36, 0, 16, 1]
        """
        return struct.pack(self.FORMAT,
                           self.bLength,
                           self.bDescriptorType,
                           self.bDescriptorSubtype,
                           self.bcdCDC)


class CallManagement(CDC):
    """Describes call processing for the Communication interface.
    See section 5.2.3.2  of CDC specification for details.
    """
    FORMAT = "<BBB" + "BB"

    def __init__(self,
                 bmCapabilities,
                 bDataInterface,
                 bLength=struct.calcsize(FORMAT),
                 bDescriptorType=Descriptor.Types.CLASS_SPECIFIC_INTERFACE,
                 bDescriptorSubtype=CDC.Subtype.CM
                 ):
        self.bLength = bLength
        self.bDescriptorType = bDescriptorType
        self.bDescriptorSubtype = bDescriptorSubtype
        self.bmCapabilities = bmCapabilities
        self.bDataInterface = bDataInterface

    def notes(self):
        return [str(self)]

    def __bytes__(self):
        """
        >>> cm = CallManagement(
        ... bmCapabilities=0,
        ... bDataInterface=1)
        >>> bytes(cm)
        b'\\x05$\\x01\\x00\\x01'
        >>> cm.get()
        [5, 36, 1, 0, 1]
        """
        return struct.pack(self.FORMAT,
                           self.bLength,
                           self.bDescriptorType,
                           self.bDescriptorSubtype,
                           self.bmCapabilities,
                           self.bDataInterface)


class AbstractControlManagement(CDC):
    """Describes commands supported by the ACM subclass.
    See section 5.2.3.3  of CDC specification for details.
    """
    FORMAT = "<BBB" + "B"

    def __init__(self,
                 bmCapabilities,
                 bLength=struct.calcsize(FORMAT),
                 bDescriptorType=Descriptor.Types.CLASS_SPECIFIC_INTERFACE,
                 bDescriptorSubtype=CDC.Subtype.ACM
                 ):
        self.bLength = bLength
        self.bDescriptorType = bDescriptorType
        self.bDescriptorSubtype = bDescriptorSubtype
        self.bmCapabilities = bmCapabilities

    def notes(self):
        return [str(self)]

    def __bytes__(self):
        """
        >>> acm = AbstractControlManagement(bmCapabilities=6)
        >>> bytes(acm)
        b'\\x04$\\x02\\x06'
        >>> acm.get()
        [4, 36, 2, 6]
        """
        return struct.pack(self.FORMAT,
                           self.bLength,
                           self.bDescriptorType,
                           self.bDescriptorSubtype,
                           self.bmCapabilities)


class DirectLineManagement(CDC):
    """Describes commands supported by the DLCM subclass.
    See section 5.2.3.4  of CDC specification for details.
    """
    FORMAT = "<BBB" + "B"

    def __init__(self,
                 bmCapabilities,
                 bLength=struct.calcsize(FORMAT),
                 bDescriptorType=Descriptor.Types.CLASS_SPECIFIC_INTERFACE,
                 bDescriptorSubtype=CDC.Subtype.DLM
                 ):
        self.bLength = bLength
        self.bDescriptorType = bDescriptorType
        self.bDescriptorSubtype = bDescriptorSubtype
        self.bmCapabilities = bmCapabilities

    def notes(self):
        return [str(self)]

    def __bytes__(self):
        """
        >>> dlm = DirectLineManagement(bmCapabilities=1)
        >>> bytes(dlm)
        b'\\x04$\\x03\\x01'
        >>> dlm.get()
        [4, 36, 3, 1]
        """
        return struct.pack(self.FORMAT,
                           self.bLength,
                           self.bDescriptorType,
                           self.bDescriptorSubtype,
                           self.bmCapabilities)


class Union(CDC):
    """This descriptor enables grouping interfaces that can be treated as
    a functional unit.
    See section 5.2.3.8  of CDC specification for details.
    """
    FIXED_FORMAT = "<BBB" + "B"     # not including bSlaveInterface_list
    FIXED_BLENGTH = struct.calcsize(FIXED_FORMAT)

    @property
    def bLength(self):
        return self.FIXED_BLENGTH + len(self.bSlaveInterface_list)

    def __init__(self,
                 bMasterInterface,
                 bSlaveInterface_list,
                 bDescriptorType=Descriptor.Types.CLASS_SPECIFIC_INTERFACE,
                 bDescriptorSubtype=CDC.Subtype.UNION
                 ):
        self.bDescriptorType = bDescriptorType
        self.bDescriptorSubtype = bDescriptorSubtype
        self.bMasterInterface = bMasterInterface
        # bSlaveInterface_list is a list of one or more slave interfaces.
        self.bSlaveInterface_list = bSlaveInterface_list

    def notes(self):
        return [str(self)]

    def __bytes__(self):
        """
        >>> u = Union(
        ... bMasterInterface=0,
        ... bSlaveInterface_list=[1])
        >>> bytes(u)
        b'\\x05$\\x06\\x00\\x01'
        >>> u.get()
        [5, 36, 6, 0, 1]
        """
        desc = struct.pack(self.FIXED_FORMAT,
                           self.bLength,
                           self.bDescriptorType,
                           self.bDescriptorSubtype,
                           self.bMasterInterface)
        return desc + bytes(self.bSlaveInterface_list)


def parseCDC(field):
    """Parser function to read values of supported CDC descriptors for
    the device from config file.

    Args:
        field:  JSON structure for this class to be parsed.


    .. doctest:

        >>> f =  {
        ... "name": "Header Functional",
        ... "bLength":                5,
        ... "bDescriptorType":   "0x24",
        ... "bDescriptorSubtype":     0,
        ... "bcdCDC":          "0x0110"
        ... }
        >>> h = parseCDC(f)
        >>> h.get()
        [5, 36, 0, 16, 1]

        >>> f = {
        ... "name": "Call Management Functional",
        ... "bLength":                         5,
        ... "bDescriptorType":            "0x24",
        ... "bDescriptorSubtype":              1,
        ... "bmCapabilities":                  0,
        ... "bDataInterface":                  1
        ... }
        >>> cm = parseCDC(f)
        >>> cm.get()
        [5, 36, 1, 0, 1]

        >>> f = {
        ... "name":  "ACM Functional",
        ... "bLength":              4,
        ... "bDescriptorType": "0x24",
        ... "bDescriptorSubtype":   2,
        ... "bmCapabilities":       6
        ... }
        >>> acm = parseCDC(f)
        >>> acm.get()
        [4, 36, 2, 6]

        >>> f = {
        ... "name": "Union Functional",
        ... "bLength":               5,
        ... "bDescriptorType":  "0x24",
        ... "bDescriptorSubtype":    6,
        ... "bMasterInterface":      0,
        ... "bSlaveInterface":   [ 1 ]
        ... }
        >>> u = parseCDC(f)
        >>> u.get()
        [5, 36, 6, 0, 1]
    """
    bDescriptorSubtype = getVal(field["bDescriptorSubtype"], 0, 0xFF)
    if bDescriptorSubtype == CDC.Subtype.HEADER:
        return Header(
                 bLength=getVal(field["bLength"], 0, 0xFF),
                 bDescriptorType=getVal(field["bDescriptorType"], 0, 0xFF),
                 bDescriptorSubtype=getVal(field["bDescriptorSubtype"],
                                           0, 0xFF),
                 bcdCDC=getVal(field["bcdCDC"], 0, 0xFFFF)
                 )
    elif bDescriptorSubtype == CDC.Subtype.CM:
        return CallManagement(
                 bLength=getVal(field["bLength"], 0, 0xFF),
                 bDescriptorType=getVal(field["bDescriptorType"], 0, 0xFF),
                 bDescriptorSubtype=getVal(field["bDescriptorSubtype"],
                                           0, 0xFF),
                 bmCapabilities=getVal(field["bmCapabilities"], 0, 0xFF),
                 bDataInterface=getVal(field["bDataInterface"], 0, 0xFF)
                 )
    elif bDescriptorSubtype == CDC.Subtype.ACM:
        return AbstractControlManagement(
                 bLength=getVal(field["bLength"], 0, 0xFF),
                 bDescriptorType=getVal(field["bDescriptorType"], 0, 0xFF),
                 bDescriptorSubtype=getVal(field["bDescriptorSubtype"],
                                           0, 0xFF),
                 bmCapabilities=getVal(field["bmCapabilities"], 0, 0xFF)
                 )
    elif bDescriptorSubtype == CDC.Subtype.DLM:
        return DirectLineManagement(
                 bLength=getVal(field["bLength"], 0, 0xFF),
                 bDescriptorType=getVal(field["bDescriptorType"], 0, 0xFF),
                 bDescriptorSubtype=getVal(field["bDescriptorSubtype"],
                                           0, 0xFF),
                 bmCapabilities=getVal(field["bmCapabilities"], 0, 0xFF)
                 )
    elif bDescriptorSubtype == CDC.Subtype.UNION:
        bSlaveInterface_list = [getVal(i, 0, 0xFF)
                                for i in field["bSlaveInterface"]]
        return Union(
                 bDescriptorType=getVal(field["bDescriptorType"], 0, 0xFF),
                 bDescriptorSubtype=getVal(field["bDescriptorSubtype"],
                                           0, 0xFF),
                 bMasterInterface=getVal(field["bMasterInterface"], 0, 0xFF),
                 bSlaveInterface_list=bSlaveInterface_list
                 )
    else:
        print("Unsupported CDC subclass")


cdcParsers = {Descriptor.Types.CLASS_SPECIFIC_INTERFACE: parseCDC,
              # CDC.Type.Data uses standard endpoints
              }

if __name__ == "__main__":
    import doctest
    doctest.testmod()