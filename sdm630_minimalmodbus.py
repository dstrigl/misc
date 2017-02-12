#!/usr/bin/env python
# -*- coding: utf-8 -*-

import struct
from timeit import default_timer as timer
import minimalmodbus
import serial


class ModbusReg:
    def __init__(self, address, unit):
        self.address = address
        self.unit = unit

# ------------------------------------------------------------------------------------
#  Dict of all SDM630-Modbus Input Registers (Function Code 04):
#    http://bg-etech.de/download/manual/SDM630Register.pdf
#
SDM630_REGISTER = {

    "Phase 1 line to neutral volts"       : ModbusReg( 0x0000, unit = "Volts"       ),  # !
    "Phase 2 line to neutral volts"       : ModbusReg( 0x0002, unit = "Volts"       ),  # !
    "Phase 3 line to neutral volts"       : ModbusReg( 0x0004, unit = "Volts"       ),  # !
    "Phase 1 current"                     : ModbusReg( 0x0006, unit = "Amps"        ),  # !
    "Phase 2 current"                     : ModbusReg( 0x0008, unit = "Amps"        ),  # !
    "Phase 3 current"                     : ModbusReg( 0x000A, unit = "Amps"        ),  # !
    "Phase 1 power"                       : ModbusReg( 0x000C, unit = "Watts"       ),  # !
    "Phase 2 power"                       : ModbusReg( 0x000E, unit = "Watts"       ),  # !
    # --------------------------------------------------------------------------------
    "Phase 3 power"                       : ModbusReg( 0x0010, unit = "Watts"       ),  # !
    "Phase 1 volt amps"                   : ModbusReg( 0x0012, unit = "VA"          ),  # !
    "Phase 2 volt amps"                   : ModbusReg( 0x0014, unit = "VA"          ),  # !
    "Phase 3 volt amps"                   : ModbusReg( 0x0016, unit = "VA"          ),  # !
    "Phase 1 volt amps reactive"          : ModbusReg( 0x0018, unit = "VAr"         ),  # !
    "Phase 2 volt amps reactive"          : ModbusReg( 0x001A, unit = "VAr"         ),  # !
    "Phase 3 volt amps reactive"          : ModbusReg( 0x001C, unit = "VAr"         ),  # !
    "Phase 1 power factor"                : ModbusReg( 0x001E, unit = None          ),  # !
    # --------------------------------------------------------------------------------
    "Phase 2 power factor"                : ModbusReg( 0x0020, unit = None          ),  # !
    "Phase 3 power factor"                : ModbusReg( 0x0022, unit = None          ),  # !
    "Phase 1 phase angle"                 : ModbusReg( 0x0024, unit = "Degrees"     ),  # !
    "Phase 2 phase angle"                 : ModbusReg( 0x0026, unit = "Degrees"     ),  # !
    "Phase 3 phase angle"                 : ModbusReg( 0x0028, unit = "Degrees"     ),  # !
    "Average line to neutral volts"       : ModbusReg( 0x002A, unit = "Volts"       ),
    #                                     : ModbusReg( 0x002C, unit = None          ),
    "Average line current"                : ModbusReg( 0x002E, unit = "Amps"        ),
    # --------------------------------------------------------------------------------
    "Sum of line currents"                : ModbusReg( 0x0030, unit = "Amps"        ),
    #                                     : ModbusReg( 0x0032, unit = None          ),
    "Total system power"                  : ModbusReg( 0x0034, unit = "Watts"       ),
    #                                     : ModbusReg( 0x0036, unit = None          ),
    "Total system volt amps"              : ModbusReg( 0x0038, unit = "VA"          ),
    #                                     : ModbusReg( 0x003A, unit = None          ),
    "Total system VAr"                    : ModbusReg( 0x003C, unit = "VAr"         ),
    "Total system power factor"           : ModbusReg( 0x003E, unit = None          ),
    # --------------------------------------------------------------------------------
    #                                     : ModbusReg( 0x0040, unit = None          ),
    "Total system phase angle"            : ModbusReg( 0x0042, unit = "Degrees"     ),
    #                                     : ModbusReg( 0x0044, unit = None          ),
    "Frequency of supply voltages"        : ModbusReg( 0x0046, unit = "Hz"          ),  # !
    "Import Wh since last reset"          : ModbusReg( 0x0048, unit = "kWh/MWh"     ),  # !
    "Export Wh since last reset"          : ModbusReg( 0x004A, unit = "kWH/MWh"     ),  # !
    "Import VArh since last reset"        : ModbusReg( 0x004C, unit = "kVArh/MVArh" ),  # !
    "Export VArh since last reset"        : ModbusReg( 0x004E, unit = "kVArh/MVArh" ),  # !
    # --------------------------------------------------------------------------------
    "VAh since last reset"                : ModbusReg( 0x0050, unit = "kVAh/MVAh"   ),
    "Ah since last reset"                 : ModbusReg( 0x0052, unit = "Ah/kAh"      ),
    "Total system power demand"           : ModbusReg( 0x0054, unit = "W"           ),
    "Maximum total system power demand"   : ModbusReg( 0x0056, unit = "VA"          ),
    #                                     : ModbusReg( 0x0058, unit = None          ),
    #                                     : ModbusReg( 0x005A, unit = None          ),
    #                                     : ModbusReg( 0x005C, unit = None          ),
    #                                     : ModbusReg( 0x005E, unit = None          ),
    # --------------------------------------------------------------------------------
    #                                     : ModbusReg( 0x0060, unit = None          ),
    #                                     : ModbusReg( 0x0062, unit = None          ),
    "Total system VA demand"              : ModbusReg( 0x0064, unit = "VA"          ),
    "Maximum total system VA demand"      : ModbusReg( 0x0066, unit = "VA"          ),
    "Neutral current demand"              : ModbusReg( 0x0068, unit = "Amps"        ),
    "Maximum neutral current demand"      : ModbusReg( 0x006A, unit = "Amps"        ),
    #                                     : ModbusReg( 0x006C, unit = None          ),
    #                                     : ModbusReg( 0x006E, unit = None          ),
    # --------------------------------------------------------------------------------
    # ... 0x0070
    # ... 0x0080
    # ... 0x0090
    # ... 0x00A0
    # ... 0x00B0
    # --------------------------------------------------------------------------------
    #                                     : ModbusReg( 0x00C0, unit = None          ),
    #                                     : ModbusReg( 0x00C2, unit = None          ),
    #                                     : ModbusReg( 0x00C4, unit = None          ),
    #                                     : ModbusReg( 0x00C6, unit = None          ),
    "Line 1 to Line 2 volts"              : ModbusReg( 0x00C8, unit = "Volts"       ),
    "Line 2 to Line 3 volts"              : ModbusReg( 0x00CA, unit = "Volts"       ),
    "Line 3 to Line 1 volts"              : ModbusReg( 0x00CC, unit = "Volts"       ),
    "Average line to line volts"          : ModbusReg( 0x00CE, unit = "Volts"       ),
    # --------------------------------------------------------------------------------
    # ... 0x00D0
    # --------------------------------------------------------------------------------
    "Neutral current"                     : ModbusReg( 0x00E0, unit = "Amps"        ),
    #                                     : ModbusReg( 0x00E2, unit = None          ),
    #                                     : ModbusReg( 0x00E4, unit = None          ),
    #                                     : ModbusReg( 0x00E6, unit = None          ),
    #                                     : ModbusReg( 0x00E8, unit = None          ),
    "Phase 1 L/N volts THD"               : ModbusReg( 0x00EA, unit = "%"           ),
    "Phase 2 L/N volts THD"               : ModbusReg( 0x00EC, unit = "%"           ),
    "Phase 3 L/N volts THD"               : ModbusReg( 0x00EE, unit = "%"           ),
    # --------------------------------------------------------------------------------
    "Phase 1 Current THD"                 : ModbusReg( 0x00F0, unit = "%"           ),
    "Phase 2 Current THD"                 : ModbusReg( 0x00F2, unit = "%"           ),
    "Phase 3 Current THD"                 : ModbusReg( 0x00F4, unit = "%"           ),
    #                                     : ModbusReg( 0x00F6, unit = None          ),
    "Average line to neutral volts THD"   : ModbusReg( 0x00F8, unit = "%"           ),
    "Average line current THD"            : ModbusReg( 0x00FA, unit = "%"           ),
    #                                     : ModbusReg( 0x00FC, unit = None          ),
    "Total system power factor degree"    : ModbusReg( 0x00FE, unit = "Degree"      ),  # duplicated entry? (see 0x003E)
    # --------------------------------------------------------------------------------
    #                                     : ModbusReg( 0x0100, unit = None          ),
    "Phase 1 current demand"              : ModbusReg( 0x0102, unit = "Amps"        ),
    "Phase 2 current demand"              : ModbusReg( 0x0104, unit = "Amps"        ),
    "Phase 3 current demand"              : ModbusReg( 0x0106, unit = "Amps"        ),
    "Maximum phase 1 current demand"      : ModbusReg( 0x0108, unit = "Amps"        ),
    "Maximum phase 2 current demand"      : ModbusReg( 0x010A, unit = "Amps"        ),
    "Maximum phase 3 current demand"      : ModbusReg( 0x010C, unit = "Amps"        ),
    # --------------------------------------------------------------------------------
    # ... 0x0110
    # ... 0x0120
    # ... 0x0130
    # --------------------------------------------------------------------------------
    #                                     : ModbusReg( 0x0140, unit = None          ),
    #                                     : ModbusReg( 0x0142, unit = None          ),
    #                                     : ModbusReg( 0x0144, unit = None          ),
    #                                     : ModbusReg( 0x0146, unit = None          ),
    #                                     : ModbusReg( 0x0148, unit = None          ),
    #                                     : ModbusReg( 0x014A, unit = None          ),
    #                                     : ModbusReg( 0x014C, unit = None          ),
    "Line 1 to line 2 volts THD"          : ModbusReg( 0x014E, unit = "%"           ),
    # --------------------------------------------------------------------------------
    "Line 2 to line 3 volts THD"          : ModbusReg( 0x0150, unit = "%"           ),
    "Line 3 to line 1 volts THD"          : ModbusReg( 0x0152, unit = "%"           ),
    "Average line to line volts THD"      : ModbusReg( 0x0154, unit = "%"           ),
    "Total kwh"                           : ModbusReg( 0x0156, unit = "kwh"         ),
    "Total kvarh"                         : ModbusReg( 0x0158, unit = "kvarh"       ),
    "L1 import kwh"                       : ModbusReg( 0x015A, unit = "kwh"         ),  # !
    "L2 import kwh"                       : ModbusReg( 0x015C, unit = "kwh"         ),  # !
    "L3 import kWh"                       : ModbusReg( 0x015E, unit = "kwh"         ),  # !
    # --------------------------------------------------------------------------------
    "L1 export kWh"                       : ModbusReg( 0x0160, unit = "kwh"         ),  # !
    "L2 export kwh"                       : ModbusReg( 0x0162, unit = "kwh"         ),  # !
    "L3 export kWh"                       : ModbusReg( 0x0164, unit = "kwh"         ),  # !
    "L1 total kwh"                        : ModbusReg( 0x0166, unit = "kwh"         ),
    "L2 total kWh"                        : ModbusReg( 0x0168, unit = "kwh"         ),
    "L3 total kwh"                        : ModbusReg( 0x016A, unit = "kwh"         ),
    "L1 import kvarh"                     : ModbusReg( 0x016C, unit = "kvarh"       ),  # !
    "L2 import kvarh"                     : ModbusReg( 0x016E, unit = "kvarh"       ),  # !
    # --------------------------------------------------------------------------------
    "L3 import kvarh"                     : ModbusReg( 0x0170, unit = "kvarh"       ),  # !
    "L1 export kvarh"                     : ModbusReg( 0x0172, unit = "kvarh"       ),  # !
    "L2 export kvarh"                     : ModbusReg( 0x0174, unit = "kvarh"       ),  # !
    "L3 export kvarh"                     : ModbusReg( 0x0176, unit = "kvarh"       ),  # !
    "L1 total kvarh"                      : ModbusReg( 0x0178, unit = "kvarh"       ),
    "L2 total kvarh"                      : ModbusReg( 0x017A, unit = "kvarh"       ),
    "L3 total kvarh"                      : ModbusReg( 0x017C, unit = "kvarh"       ),
    #                                     : ModbusReg( 0x017E, unit = None          ),
}

SDM630_BLOCKS = {
    0x0000 : 40,
    0x0050 : 16,
    0x00C0 : 40,
    0x0140 : 32,
}


def main():

    instr = minimalmodbus.Instrument('/dev/ttyAMA0', 1, minimalmodbus.MODE_RTU) # port name, slave address (in decimal)
    instr.serial.baudrate = 38400
    instr.serial.parity = serial.PARITY_NONE
    instr.serial.bytesize = 8
    instr.serial.stopbits = 2
    instr.serial.timeout = 1 # seconds
    #instr.debug = True

    # request modbus register values from device
    start = timer()
    reg_values = {}
    for addr, size in SDM630_BLOCKS.items():
        block = instr.read_registers(addr, size * 2, functioncode=4)
        reg_values.update({ (addr + i): block[i] for i in range(0, len(block)) })
    request_time = timer() - start

    # convert modbus register values to float
    start = timer()
    mod_values = {}
    for name, r in SDM630_REGISTER.items():
        w0 = reg_values[r.address + 0]
        w1 = reg_values[r.address + 1]
        mod_values[name] = struct.unpack('>f', struct.pack('>HH', w0, w1))[0]
    conversion_time = timer() - start

    # print all values in order of their modbus address
    for (name, _) in sorted(SDM630_REGISTER.items(), key = lambda x: x[1].address):
        v = mod_values[name]
        u = SDM630_REGISTER[name].unit
        print("{:40}: {:10.2f} {}".format(name, v, "" if u is None else str(u)))

    print("request took %.3f seconds" % request_time)
    #print("conversion took %.3f seconds" % conversion_time)


if __name__ == '__main__':
    main()
