#!/usr/bin/env python
# -*- coding: utf-8 -*-

# general imports
import datetime
import sys

# imports for Modbus
from pymodbus.constants import Endian
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.client import ModbusTcpClient as ModbusClient

# imports for using enumerations
from enum import Enum

# enumeration by using a class. value of the enum ( 1-8 ) is irrelevant!
# use the method getRegisterLength() instead
class DataType(Enum):
    String8 = 1
    String16 = 2
    String32 = 3
    Int16 = 4
    UInt16 = 5
    Int32 = 6
    UInt32 = 7
    Float32 = 8
    UInt64 = 7

    # Returns the length (amount) of the registers.
    # This corresponds to the value from the Fronius Excel list (column "Size").
    # This refers to how many registers the Mobus function read_holding_registers() must read to get the complete value
    def getRegisterLength(self):

        if (self == DataType.String8) or (self == DataType.UInt64):
            return int(4)
        elif (self == DataType.String16):
            return int(8)
        elif (self == DataType.String32):
            return int(16)
        elif (self == DataType.Int16) or (self == DataType.UInt16):
            return int(1)
        elif (self == DataType.Int32) or (self == DataType.UInt32) or (self == DataType.Float32):
            return int(2)


# -------------------------------------------------------------------------------------------------------[ private ]---
# | Gets a value from the inverter                                                                                    |
# | ----------------------------------------------------------------------------------------------------------------- |
# | Input parameters:                                                                                                 |
# | -> device           ModbusClient  An open connection to the modbus device (inverter or smartmeter)                |
# | -> address          INT           The starting address to read from                                               |
# | -> dataType         DataType      The DataType of registers to read                                               |
# | -> humidity         INT           The slave unit this request is targeting                                        |
# | ----------------------------------------------------------------------------------------------------------------- |
# | Return value:                                                                                                     |
# | <- result           STRING        Value of the defined address                                                    |
# ---------------------------------------------------------------------------------------------------------------------
def getRegisterValue(device, address, dataType, unitNo):

    #print ("  Adr: " + str(address) + "  Name: " + dataType.name)

    # Now we can read the data of the register with a Modbus function
    # In the fronius documentation it is described that you have to subtract 1 from the actual address.
    result = device.read_holding_registers(address-1, dataType.getRegisterLength(), unitNo)

    if (result.isError()) :
        return "n.a."

    #print ("  value: " + str(result.registers))

    # The values from Modbus must now be reformatted accordingly
    # How to do this reformatting depends on the DataType
    decoder = BinaryPayloadDecoder.fromRegisters(result.registers, byteorder=Endian.Big, wordorder=Endian.Big)

    if (dataType == DataType.String8) or (dataType == DataType.String16) or (dataType == DataType.String32):
        return str(decoder.decode_string(16).decode('utf-8'))

    elif (dataType == DataType.Int16):
        return decoder.decode_16bit_int()

    elif (dataType == DataType.UInt16):
        return decoder.decode_16bit_uint()

    elif (dataType == DataType.Int32):
        return decoder.decode_32bit_int()

    elif (dataType == DataType.UInt32):
        return decoder.decode_32bit_uint()

    elif (dataType == DataType.Float32):
        return decoder.decode_32bit_float()

    else:
        return str(decoder.decode_bits())


# -------------------------------------------------------------------------------------------------------[ private ]---
# | Formats the given nuber (powerValue) into a well-formed and readable text                                         |
# | ----------------------------------------------------------------------------------------------------------------- |
# | Input parameters:                                                                                                 |
# | -> powerValue       FLOAT   The value to format                                                                   |
# | ----------------------------------------------------------------------------------------------------------------- |
# | Return value:                                                                                                     |
# | <- formatedText     STRING  A well-formed and readable text containing the powerValue                             |
# ---------------------------------------------------------------------------------------------------------------------
def formatPowerText(powerValue):

    formatedText = ""

    # Over 1000 'kilo Watt' will be displayed instead of 'Watt'
    if abs(powerValue) > 1000:
        formatedText = "{0} kW".format(str('{:0.2f}'.format(powerValue / 1000))).replace('.', ',')
    else:
        formatedText = "{0} W".format(str('{:.0f}'.format(powerValue))).replace('.', ',')

    return formatedText


# -------------------------------------------------------------------------------------------------------[ private ]---
# | The Main Entry Point                                                                                              |
# ---------------------------------------------------------------------------------------------------------------------
def main():

    print ("Current Time: " + datetime.datetime.now().strftime('%H:%M:%S'))

    # Open a new Modbus connection to the fronius inverter (e.g. Symo 10.3)
    modbusClient = ModbusClient(sys.argv[1], port=502, timeout=10)
    modbusClient.connect()

    # The modbus addresses of the registers are documented in the following lists:
    # - Inverter_Register_Map_Float_v1.0_with_SYMOHYBRID_MODEL_124.xlsx
    # - Meter_Register_Map_Float_v1.0.xlsx
    # Goto: https://www.fronius.com/en/photovoltaics/downloads and search for "Modbus Sunspec Maps, State Codes und Events"
    # Downloads the hole ZIP package and enjoy the documentation ;-)
    #
    # Note: In this script you have to specify a data type when calling the method getRegisterValue(). This corresponds
    #       to the value from the Fronius Excel list (column "Type").
    #
    #       The optional parameter "unitNo" of method getRegisterValue() is used to specify from which device the
    #       data is to be read. The default value is 1 which corresponds to the inverter.
    #       If you want to read data from the SmartMeter, 240 must be used instead.

    # Manufacturer + Device model of the inverter
    manufacturer = getRegisterValue(modbusClient, 40005, DataType.String32, 1)         # Manufacturer
    deviceModel = getRegisterValue(modbusClient, 40021, DataType.String32, 1)          # Device model
    versionString = getRegisterValue(modbusClient, 40045, DataType.String16, 1)        # SW version of inverter
    print ("Inverter: " + manufacturer + " - " + deviceModel + " - SW Version: " + versionString)

    # Manufacturer + Device model of the SmartMeter
    manufacturer = getRegisterValue(modbusClient, 40005, DataType.String32, 240)    # Manufacturer
    deviceModel = getRegisterValue(modbusClient, 40021, DataType.String32, 240)     # Device model
    versionString = getRegisterValue(modbusClient, 40045, DataType.String16, 240)   # SW version of inverter
    print ("SmartMeter: " + manufacturer + " - " + deviceModel + " - SW Version: " + versionString)

    # AC Power value of the inverter - Current production in Watt
    powerProduction = getRegisterValue(modbusClient, 40092, DataType.Float32, 1)
    print ()
    print (powerProduction)
    print ("Production: " + formatPowerText(powerProduction)) # in my case 40092 is the same as 500 because i only have one inverter

    # Power consumption in the whole house - Total power consumption in Watt
    # This value must be read from the SmartMeter, as the inverter does not have this information
    powerConsumption = getRegisterValue(modbusClient, 40098, DataType.Float32, 240)
    print ()
    print (powerConsumption)
    print ("Consumption: " + formatPowerText(powerConsumption))

    # Now we try to calculate what amount of electricity we get from the grid or delivered to the grid
    # A positive value means that electricity is delivered to the grid.
    # A negative value means that power is being taken from the grid.
    print ()
    try:
        powerDifference = powerProduction - powerConsumption

        if (powerDifference > 0):
            print ("Supply to the power grid: " + formatPowerText(powerDifference) + "   --->")
        else:
            print ("Consumption from the power grid: " + formatPowerText(powerDifference) + "   <---")

    except Exception as e:
        print ("Unexpected error occured while calculate the 'powerDifference': " + str(e))

#    print("- AC Phase A   Current    : " + str(int(getRegisterValue(modbusClient, 40074, DataType.Float32))) + " A")
#    print("- AC Phase B   Current    : " + str(int(getRegisterValue(modbusClient, 40076, DataType.Float32))) + " A")
#    print("- AC Phase C   Current    : " + str(int(getRegisterValue(modbusClient, 40078, DataType.Float32))) + " A")

#    print("- AC Phase A <-> B        : " + str(int(getRegisterValue(modbusClient, 40080, DataType.Float32))) + " V")
#    print("- AC Phase B <-> C        : " + str(int(getRegisterValue(modbusClient, 40082, DataType.Float32))) + " V")
#    print("- AC Phase C <-> A        : " + str(int(getRegisterValue(modbusClient, 40084, DataType.Float32))) + " V")

#    print("- AC Phase A <-> n        : " + str(int(getRegisterValue(modbusClient, 40086, DataType.Float32))) + " V")
#    print("- AC Phase B <-> n        : " + str(int(getRegisterValue(modbusClient, 40088, DataType.Float32))) + " V")
#    print("- AC Phase C <-> n        : " + str(int(getRegisterValue(modbusClient, 40090, DataType.Float32))) + " V")

#    print("- AC Power                : " + str(int(getRegisterValue(modbusClient, 40092, DataType.Float32))) + " W")
#    print("- AC Frequency            : " + str(int(getRegisterValue(modbusClient, 40094, DataType.Float32))) + " Hz")

    # Close the connection
    modbusClient.close()


# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# | Call the main function to start this script                                                                       |
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
main()
