#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import getopt
import requests
import subprocess
import socket
import json
import netifaces as ni
import thread
from logger import Log
from getpass import getuser
from wifi import Cell, Scheme
from wifi.exceptions import ConnectionError, InterfaceError
from uuid import getnode as get_mac
from time import sleep

WIFI_SSID        = "StratusPrint"
WIFI_PASS        = ""
WIFI_INTERFACE   = "wlan0"
WIFI_PROFILE     = "stratus"
INTERFACE_DIR    = "/etc/network"
INTERFACE_FILE   = "/etc/network/interfaces"
PRINTER_ACTIVATE = "/printers"
PRINTER_LIST     = "/printers"
BASE_IP          = "192.168.0.1"
BASE_PORT        = "5000"
BASE_URL         = "http://" + BASE_IP + ":" + BASE_PORT
#BASE_URL = "http://stratuspi:5000"
UUID_FILE        = ".uuid"
API_KEY          = "THISISNOTAGOODKEY"
UUID             = None
PORT             = 80

def get_uuid():
    global UUID
    if UUID:
        return str(UUID)
    if os.path.isfile(UUID_FILE):
        with open(UUID_FILE, 'r') as f:
            uuid = long(f.read())
    else:
        uuid = get_mac()
        with open(UUID_FILE, 'w') as f:
            f.write(str(uuid))
    UUID = uuid
    return str(uuid)

def get_ipaddress(log):
    try:
        ip = ni.ifaddresses(WIFI_INTERFACE)[ni.AF_INET][0].get('addr')
    # if this throws an error, your ip broke. Idk what the error is
    except:
        log.log("ERROR: Could not retrieve IP address")
        ip = ""
    return str(ip)

def connect_to_ap(log):
    """Function that will connect to wifi with the given parameters"""

    log.log("Connecting to " + WIFI_SSID + " using " + WIFI_INTERFACE)

    # Complicated way to account for the file not existing
    # Just tries to find if a scheme exists in interfaces
    try:
        scheme = Scheme.find(WIFI_INTERFACE, WIFI_PROFILE)
    except(IOError,err):
        log.log(err)
        log.log("WARNING: Most likely file was not found. Making one.")
        scheme = None
        if not os.path.isdir(INTERFACE_DIR):
            os.mkdir(INTERFACE_DIR, 0755)
            os.open(INTERFACE_FILE, 0644).close()
        elif not os.path.isfile(INTERFACE_FILE):
            os.open(INTERFACE_FILE, 0644).close()

    # If the scheme was not found or if it was found and didn't activate,
    # look for the ssid, save it, and connect to it.
    if scheme == None:
        cells = Cell.all(WIFI_INTERFACE)
        for cell in cells:
            if cell.ssid == WIFI_SSID:
                scheme = Scheme.for_cell(WIFI_INTERFACE,
                                         WIFI_PROFILE,
                                         cell,
                                         passkey=WIFI_PASS)
                scheme.save()
                break
    if scheme == None:
        log.log("ERROR: SSID " + WIFI_SSID + " was not found.")
        return False

        if scheme.activate() == False:
            log.log("ERROR: Could not connect to " + WIFI_SSID + ".")
            return False
    else:
        try:
            res = scheme.activate()
        # This can throw a lot of errors, let's just catch them all for now
        except:
            scheme.delete()
            #TODO delete the old scheme and add a new one. Possibly for password change
            log.log("ERROR: Could connect to " + WIFI_SSID)
            return False

    log.log("Successfully connected to " + WIFI_SSID + ".")
    return True

def persist_connection(log):
    """Should spawn as it's own thread and ensure it's IP doesn't change or
    that connection is dropped. If it is, continuously try to reconnect"""

    ip = get_ipaddress(log)
    while(True):
        # Every 30 seconds send an activation in case connection was lost
        temp_ip = get_ipaddress(log)
        if ip != temp_ip:
            if len(temp_ip):
                ip = temp_ip
                activate(log)
            else:
                log.log("ERROR: Did not receive a valid IP address.")

        with open("/dev/null") as f:
            r = subprocess.call(["ping","-c","1",BASE_IP],stdout=f)
        if r != 0:
            log.log("Cannot ping " + BASE_IP + ". Will try to reconnect")
            # Continue trying to connect to the AP
            res = connect_to_ap(log)
            while not res:
                res = connect_to_ap(log)
        res = verify(log)
        sleep(30)

def verify(log):
    """Will make sure the data the server has is still valid"""
    url = BASE_URL + PRINTER_LIST
    params = {
            'online_only': 'true',
            'internal': 'true'
    }
    try:
        r = requests.get(url, params=params, timeout=10)
    except requests.ConnectionError:
        log.log("ERROR: Could not make a connection with the server")
        return False
    except requests.Timeout:
        log.log("ERROR: Took over 10 seconds for server to respond.")
        return False

    if r.status_code != 200:
        log.log("ERROR: Status code of " + url + " was " + str(r.status_code))
        return False
    printers = r.json().get("printers")
    id = get_uuid()
    ip   = get_ipaddress(log)

    for printer in printers:
        if printer.get("id") == int(id):
            if len(ip):
                if printer.get('ip') != ip:
                    log.log("ERROR: Server has wrong IP.")
                    return activate(log)
            else:
                log.log("ERROR: Did not receive a valid IP address.")
                return False
            return True
    log.log("ERROR: Server doesn't know about me!")
    return activate(log)

def activate(log):
    """Will attempt to activate on the HUB"""

    data = {
            "id": get_uuid(),
            "ip": get_ipaddress(log),
            "key": str(API_KEY),
            "port": str(PORT)
    }

    url = BASE_URL + PRINTER_ACTIVATE
    log.log("Activating printer on " + str(url) + ".")
    for i in range(20):
        try:
            r = requests.post(url, data=data, timeout=10)
            if not r:
                log.log("ERROR: No data was received")
            elif r.status_code == requests.codes.ok:
                log.log("Successfully activated on the HUB")
                return True
            else:
                #TODO make this more descriptive
                log.log("ERROR: Response was " + str(r.status_code)
                      + ". Something went wrong. ")
                return False

        except requests.ConnectionError:
            if i % 5 == 0 or i > 20 - 5:
                log.log("ERROR: Can't reach server, will try "
                        + str(20 - i) + " more times.")
            sleep(1)
        except requests.Timeout:
            log.log("ERROR: Took over 10 seconds for server to respond."
                  + " Trying again.")
            sleep(1)
            
    log.log("ERROR: No connection after 20 attempts."
          + "Will attempt to reconnect to AP.")
    return False


def set_args(args):
    global config
    global print_enabled
    global WIFI_SSID
    global WIFI_INTERFACE
    global WIFI_PASS
    global API_KEY

    opts, args = getopt.getopt(args, "hvs:p:i:a:c:",
                                   ["help","ssid=","pass="
                                       ,"interface=","apikey="
                                       ,"verbose","config="])
    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            print("Usage: run.py -h -s <ssid> -p <password>")
        elif opt in ["-c", "--config"]:
            config = arg
        elif opt in ["-v", "--verbose"]:
            print_enabled = True
        elif opt in ["-s", "--ssid"]:
            WIFI_SSID = arg
        elif opt in ["-p", "--pass", "--password"]:
            WIFI_PASS = arg
        elif opt in ["-i", "--interface"]:
            WIFI_INTERFACE = arg
        elif opt in ["-a", "--apikey"]:
            API_KEY = arg


def load_config(config):
    path = os.path.abspath(config)
    l = []
    with open(path, "r") as f:
        for line in f:
            if line[0] == "#":
                continue
            l.extend(line.split())
    set_args(l)
    return 0

print_enabled    = False

if getuser() != 'root':
    print("Must be run as root...")
    exit(1)

config = None
set_args(sys.argv[1:])
if config != None:
    load_config(config)


if WIFI_PASS == "":
    print("No password was entered, please specify with '-p <password>'")
    exit(2)
log = Log(print_enabled=print_enabled)
log.log("Starting connect.py")
res = connect_to_ap(log)
while not res:
    res = connect_to_ap(log)
res = activate(log)
persist_connection(log)
# YOU WILL NEVER GET PASSED THIS

