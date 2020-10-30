#!/usr/bin/python

# This script can be used to read a (Dutch?) energy meter, using it's P1 port and a serial to usb cable.
# It is targeted at the DSMR version 5.0 meters, no clue if it works with older types as well.
# 
# on ubuntu flavors, install the needed python modules using:
#   sudo apt-get install python-serial
#   sudo apt-get install python-mysqldb
#   sudo apt-get install python-crcmo
#
# If the last line does not work anymore, try:
#
#   sudo pip install crcmo
#
# This script runs using python 2.x, not meant for python 3.
# This is a simple run-from-top-to-bottom script, lots of comments to explain it's inner workings,
# so hopefully easy to read and change where needed for your usecase. What's missing is nice
# error handling. Feel free to add it where needed. For me this works good enough, error means no data inserted.
#
# I am scheduling this script from the unix cron-tab to run every 15 minutes, but you can run it at any
# interval you like. My meter can be polled as fast as once every second (not recommended, it would need
# a changed script to just keep reading the data-stream, and not stop after each message).
# 
# Thijs Kaper, April 2018.

# Addition: also write the data to an influx-db, as that is better suitable to produce grafana graphs.
# Set the proper influx-db connect URL and user:password here at the top of the file:
# influx_host_port, influx_db, influx_user_password.
# The influx_db contains the name of your database in the influxdb. You need to have created that
# database inside influx, for example using command line interface, and entering "create database meter".
# Also make sure in the influx configuration to enable the http interface.
# When running in docker, use the hostname of influx with which you can read it. That's not localhost,
# as that would point to the python meter script container. So use the external IP of the host serving
# the influx, or make a docker network to bind both containers to. Too much to explain here ;-)
#
# In addition to adding influx, you now can enable/disable the influx and sql storage separately
# by setting the values of store_in_influx and store_in_postgres
#
# Thijs Kaper, 30 October 2020.

import serial
import crcmod
import re
import MySQLdb
import httplib
import base64

# enable/disable database backends, use values True or False
store_in_influx = True
store_in_postgres = True

# influx data submit configuration
influx_host_port = "192.168.0.120:8086"
influx_db = "meter"
influx_user_password = "admin:SomePassword18"
# set influx_use_credentials to False if you did not set up a secured influx, but keep it open
influx_use_credentials = True

# open serial port
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=30, parity=serial.PARITY_NONE, rtscts=0)

# connect to mysql database
if store_in_postgres:
  db = MySQLdb.connect("192.168.0.120","root","MyMeter18", "meter")

# list of known obis code's, translated to more readable field names
# this is the set as found in a "P1 Companion Standard" version 5.0.2 document for DSMR 5.0
obis_codemap = {
        "1-3:0.2.8":   "DSMR_VERSION",
        "0-0:1.0.0":   "TIMESTAMP",
        "0-0:96.1.1":  "METER_ID",
        "1-0:1.8.1":   "TOTAL_DELIVERY_LOW_KWH",
        "1-0:1.8.2":   "TOTAL_DELIVERY_HIGH_KWH",
        "1-0:2.8.1":   "TOTAL_BACKDELIVERY_LOW_KWH",
        "1-0:2.8.2":   "TOTAL_BACKDELIVERY_HIGH_KWH",
        "0-0:96.14.0": "TARIFF_INDICATOR",
        "1-0:1.7.0":   "ACTUAL_DELIVERY_KW",
        "1-0:2.7.0":   "ACTUAL_BACKDELIVERY_KW",
        "0-0:96.7.21": "NR_POWERFAILURES",
        "0-0:96.7.9":  "NR_POWERFAILURES_LONG",
        "1-0:99.97.0": "POWERFAILURE_LOG", 
        "1-0:32.32.0": "NR_VOLTAGE_SAGS_L1",
        "1-0:52.32.0": "NR_VOLTAGE_SAGS_L2",
        "1-0:72.32.0": "NR_VOLTAGE_SAGS_L3",
        "1-0:32.36.0": "NR_VOLTAGE_SWELLS_L1",
        "1-0:52.36.0": "NR_VOLTAGE_SWELLS_L2",
        "1-0:72.36.0": "NR_VOLTAGE_SWELLS_L3",
        "1-0:32.7.0":  "VOLTAGE_L1_V",
        "1-0:52.7.0":  "VOLTAGE_L2_V",
        "1-0:72.7.0":  "VOLTAGE_L3_V",
        "1-0:31.7.0":  "CURRENT_L1_A",
        "1-0:51.7.0":  "CURRENT_L2_A",
        "1-0:71.7.0":  "CURRENT_L3_A",
        "1-0:21.7.0":  "ACT_POWER_L1_KW",
        "1-0:41.7.0":  "ACT_POWER_L2_KW",
        "1-0:61.7.0":  "ACT_POWER_L3_KW",
        "1-0:22.7.0":  "ACT_POWER_BACKDELIVERY_L1_KW",
        "1-0:42.7.0":  "ACT_POWER_BACKDELIVERY_L2_KW",
        "1-0:62.7.0":  "ACT_POWER_BACKDELIVERY_L3_KW",
        "0-0:96.13.0": "TEXT_MESSAGE",
        "0-1:24.1.0":  "MBUS1_DEVICE_TYPE",
        "0-1:96.1.0":  "MBUS1_METER_ID",
        "0-1:24.2.1":  "MBUS1_VALUE",
        "0-2:24.1.0":  "MBUS2_DEVICE_TYPE",
        "0-2:96.1.0":  "MBUS2_METER_ID",
        "0-2:24.2.1":  "MBUS2_VALUE",
        "0-3:24.1.0":  "MBUS3_DEVICE_TYPE",
        "0-3:96.1.0":  "MBUS3_METER_ID",
        "0-3:24.2.1":  "MBUS3_VALUE",
        "0-4:24.1.0":  "MBUS4_DEVICE_TYPE",
        "0-4:96.1.0":  "MBUS4_METER_ID",
        "0-4:24.2.1":  "MBUS4_VALUE",
    }

# define value parser, to give uniform parsed values
def parse_value(value):
    # if length is 13, and value ends in W or S, assume it is a timestamp, and reformat suitable for MYSQL/MARIADB inserts.
    if len(value) == 13 and (value.endswith("W") or value.endswith("S")):
        return "20" + value[0:2] + "-" + value[2:4] + "-" + value[4:6] + " " + value[6:8] + ":" + value[8:10] + ":" + value[10:12]

    # remove leading zeroes for numbers like 000123.123
    value = re.sub("^0*([1-9])", "\\1", value)
    # remove leading zeroes (except the last one) for numbers like 000000.123
    value = re.sub("^0*([0-9]\.)", "\\1", value)
    # remove trailing unit's like "*kWh", "*kW", "*V", "*A", "*m3", "*s",...
    value = re.sub("\*.*", "", value)
    return value

# initialize result value set, and some other helper variables
values = { }
found_start = False
found_end = False
full_message = "-"
mbus_device_type = "-"

# this outer while serves to read a full message
while not found_end:

    # first line MUST start with a /, if not found, ignore lines until we find one
    # this inner while reads until the first line is found, and after that is inactive
    while not found_start:
        raw_line = ser.readline()
        if raw_line.startswith('/'):
           found_start = True
           values["HEADER"] = raw_line.strip()
           full_message = raw_line
           print values["HEADER"]

    # read next data-line
    raw_line = ser.readline()

    # get rid of cr/lf's
    line = raw_line.strip()

    # use () to split line in array fields (remove close brackets, and split on open brackets)
    # this parses a line like this nicely: "0-1:24.2.1(101209112500W)(12785.123*m3)"
    fields = line.replace(")", "").split("(")

    # for (optionally) printing a line with two data fields, use a helper variable "extra_print_data"
    extra_print_data = ""

    # do we have a known fieldname for the received obis code? if so, parse line, else just print the line
    if fields[0] in obis_codemap:
        field_name = obis_codemap[fields[0]]

        # handle the optional MBUS child meter value field naming
        # the postfix will indicate in the fieldname what type of meter it is, and what unit it measures in
        if mbus_device_type == "3" and field_name.startswith("MBUS") and field_name.endswith("_VALUE"):
            mbus_postfix = "_GAS_M3"
        # TODO: fix/add elif's for _THERMAL_GJ, _WATER_M3, _ELECTR_KWH or other device_types when needed
        # I could not find the needed type numbers, so you are on your own here, feel free to let me know the correct numbers
        elif mbus_device_type == "<TODO:fill-in-proper-value-here>" and field_name.startswith("MBUS") and field_name.endswith("_VALUE"):
            mbus_postfix = "_WATER_M3"
        else:
            mbus_postfix = ""

        # start parsing field values:
        # if we have 3 fields, and second is 13 long, assume we have a timestamp and value
        # if fieldname ends with LOG, then do not parse, but just copy stringyfied array as data
        # otherwise assume it is a single data value

        if len(fields) == 3 and len(fields[1]) == 13:
            values[field_name + "_TIMESTAMP"] = parse_value(fields[1])
            extra_print_data = ", " + field_name + "_TIMESTAMP = \"" + parse_value(fields[1]) +"\""
            values[field_name + mbus_postfix] = parse_value(fields[2])
        elif field_name.endswith("LOG"):
            values[field_name] = str(fields[1:])
        else:   
            values[field_name] = parse_value(fields[1])

        # store the last encountered MBUS child device type (mbus can have up to 4 different plugged in meters)
        # by convention, the type field will always be passed to us before the value field
        if field_name.startswith("MBUS") and field_name.endswith("_DEVICE_TYPE"):
            mbus_device_type = values[field_name]

        # show the input line, together with the parsed result
        print line + " --> " + field_name + mbus_postfix + " = \"" + values[field_name + mbus_postfix] + "\"" + extra_print_data
    else:
        # unknown obis code, just print the input line
        print line

    # did we find the final line yet? it starts with a "!"
    # add raw input data up-to-and-including the "!" to the full_message variable for CRC checking
    if line.startswith('!'):
        full_message = full_message + "!"
        inputchecksum = line[1:]
        found_end = True
    else:
        full_message = full_message + raw_line

# ready reading, close the serial port
ser.close()

# print parsed result key-value-pairs as json data
print "\n" + str(values) + "\n"

# go and check the checksum, we do not want to use flakey data...
crc16_function = crcmod.mkCrcFun(0x18005, rev=True, initCrc=0x0000, xorOut=0x0000)
calculated_checksum = '{0:0{1}X}'.format((crc16_function(full_message)), 4)
checksum_ok = (inputchecksum == calculated_checksum)

# is the checksum ok?
if not checksum_ok:
    # panic... wrong checksum, now what? just exit for now...
    print "CHECKSUM ERROR, expected " + calculated_checksum
    exit(1)

print "CHECKSUM OK\n"


# insert into influx database
# to do this, create a message body with all fields as "KEYNAME value=VALUE", with one line per key, and the value
# needs to be quoted for strings, and not quoted for numeric values.
# An auto-detect function is made to do this. Minor catch (which I hope never happens), is if a value changes
# between numeric and non-numeric for different measurements, the first one will win for the datatype.
# Influx will not change data-type after initial create.
# For my meter this will not happen as far as I can see.
# If this happens for your meter, then you will need to change the script to configure fields which should be string
# in some way, instead of using auto-detect. I added as examples all fields ending in _ID, and the HEADER field.

def quote_string(key, value):
  if key.endswith("_ID"):
    return "\"" + value.replace("\"", "'") + "\""

  if key == "HEADER":
    return "\"" + value.replace("\"", "'") + "\""

  try:
    # try parsing as number, if OK, return the value, if fail, return the quoted value
    float(value)
    return value
  except:
    return "\"" + value.replace("\"", "'") + "\""

# loop throug all fields, and append to post body
if store_in_influx:
  body = ""
  for key, value in values.items():
    body = body + key + " value=" + quote_string(key, value) + "\n"

  print("Influx post body:\n\n" + body)

  # post the data
  conn = httplib.HTTPConnection(influx_host_port)
  if influx_use_credentials:
    auth_header = { "Authorization": "Basic " + base64.b64encode(influx_user_password.encode('ascii')).decode('ascii') }
    conn.request('POST', '/write?db=' + influx_db, body, auth_header)
  else:
    conn.request('POST', '/write?db=' + influx_db, body)

  response = conn.getresponse()
  print("influx postresponse " + str(response.status) + "\n")


if store_in_postgres:
  # insert into sql database
  cursor = db.cursor()

  insert_result = cursor.execute("""INSERT INTO `METER` (`TIMESTAMP`, `TOTAL_DELIVERY_LOW_KWH`, `TOTAL_DELIVERY_HIGH_KWH`, `TOTAL_BACKDELIVERY_LOW_KWH`, `TOTAL_BACKDELIVERY_HIGH_KWH`, `TARIFF_INDICATOR`, `ACTUAL_DELIVERY_KW`, `ACTUAL_BACKDELIVERY_KW`, `NR_POWERFAILURES`, `NR_POWERFAILURES_LONG`, `POWERFAILURE_LOG`, `NR_VOLTAGE_SAGS_L1`, `NR_VOLTAGE_SWELLS_L1`, `TEXT_MESSAGE`, `VOLTAGE_L1_V`, `CURRENT_L1_A`, `MBUS1_VALUE_GAS_M3`, `MBUS1_VALUE_TIMESTAMP`, `JSON`) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""", (values['TIMESTAMP'], values['TOTAL_DELIVERY_LOW_KWH'], values['TOTAL_DELIVERY_HIGH_KWH'], values['TOTAL_BACKDELIVERY_LOW_KWH'], values['TOTAL_BACKDELIVERY_HIGH_KWH'], values['TARIFF_INDICATOR'], values['ACTUAL_DELIVERY_KW'], values['ACTUAL_BACKDELIVERY_KW'], values['NR_POWERFAILURES'], values['NR_POWERFAILURES_LONG'], values['POWERFAILURE_LOG'], values['NR_VOLTAGE_SAGS_L1'], values['NR_VOLTAGE_SWELLS_L1'], values['TEXT_MESSAGE'], values['VOLTAGE_L1_V'], values['CURRENT_L1_A'], values['MBUS1_VALUE_GAS_M3'], values['MBUS1_VALUE_TIMESTAMP'], str(values)))

  print("inserted " + str(insert_result) + " rows in db\n")

  db.commit()
  db.close()

print ("\n---\n");

