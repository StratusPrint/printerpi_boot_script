#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import getopt
import requests
import socket
import json
import netifaces as ni
import thread
from Logger import Log
from getpass import getuser
from wifi import Cell, Scheme
from uuid import getnode as get_mac
from time import sleep

WIFI_SSID        = "StratusPrint"
WIFI_PASS        = ""
WIFI_INTERFACE   = "wlan0"
WIFI_PROFILE     = "stratus"
INTERFACE_DIR    = "/etc/network"
INTERFACE_FILE   = "/etc/network/interfaces"
PRINTER_ACTIVATE = "/printers/activate"
BASE_IP          = "192.168.0.1"
BASE_PORT        = "5000"
BASE_URL         = "http://" + BASE_IP + ":" + BASE_PORT
#BASE_URL = "http://stratuspi:5000"
UUID_FILE        = ".uuid"
API_KEY          = "THISISNOTAGOODKEY"
PORT             = 80

def get_uuid():
    if os.path.isfile(UUID_FILE):
        with open(UUID_FILE, 'r') as f:
            uuid = long(f.read())
    else:
        uuid = get_mac()
        with open(UUID_FILE, 'w') as f:
            f.write(str(uuid))
    return str(uuid)

def get_ipaddress():
    return str(ni.ifaddresses(WIFI_INTERFACE)[ni.AF_INET][0].get('addr'))

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
    if scheme == None or scheme.activate() == False:
        cells = Cell.all(WIFI_INTERFACE)
        for cell in cells:
            if cell.ssid == WIFI_SSID:
                scheme = Scheme.for_cell(WIFI_INTERFACE,
                                         WIFI_PROFILE,
                                         cell,
                                         passkey=WIFI_PASS)
                scheme.save()
            else:
                log.log("ERROR: SSID " + WIFI_SSID + " was not found.")
                return False

        if scheme.activate() == False:
            log.log("ERROR: Could not connect to " + WIFI_SSID + ".")
            return False

    log.log("Successfully connected to " + WIFI_SSID + ".")
    return True

def persist_connection(log):
    """Should spawn as it's own thread and ensure it's IP doesn't change or
    that connection is dropped. If it is, continuously try to reconnect"""

    ip = get_ipaddress
    while(True):
        r = os.system("ping -c 1 " + BASE_IP)
        if r != 0:
            log.log("Cannot ping " + BASE_IP + ". Will try to reconnect")
            # Continue trying to connect to the AP
            res = connect_to_ap(log)
            while not res:
                res = connect_to_ap(log)
            res = activate(log)

        try:
            r = requests.get(BASE_URL + "/ok", timeout=3)
        except requests.ConnectionError:
            log.log("ERROR: Server not responding. Will attempt to activate.")
            res = activate(log)
            if not res:
                log.log("ERROR: Still no connection... Sleeping for 10 seconds")
                sleep(10)
        sleep(10)

def activate(log):
    """Will attempt to activate on the HUB"""

    payload = {
            "uuid": get_uuid(),
            "ip": get_ipaddress(),
            "key": str(API_KEY),
            "port": str(PORT)
    }
    url = BASE_URL + PRINTER_ACTIVATE + "?payload=" + json.dumps(payload)
    log.log("Activating printer on " + str(url) + ".")
    for i in range(20):
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == requests.codes.ok:
                log.log("Response was okay! Good to go.")
                return True
            else:
                #TODO make this more descriptive
                log.log("ERROR: Response was " + r.status_code
                      + ". Something went wrong. ")
                return False
        except requests.ConnectionError:
            if i % 5 == 0 or i < 5:
                log.log("Error: Can't reach server, will try "
                        + str(20 - i) + " more times.")
            sleep(1)
    log.log("ERROR: No connection after 20 attempts."
          + "Will attempt to reconnect to AP.")
    return False


if __name__ == "__main__":
    print_enabled    = False

    if getuser() != 'root':
        print("Must be run as root...")
        exit(1)

    try:
        # Short option syntax: "hv:"
        # Long option syntax: "help" or "verbose="
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hvs:p:i:a:",
                                   ["help","ssid=","pass="
                                       ,"interface=","apikey="
                                       ,"verbose"])
    
    except(getopt.GetoptError):
        # Print debug info
        print("Usage: run.py -h -s <ssid> -p <password>")
        exit(1)
    
    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            print("Usage: run.py -h -s <ssid> -p <password>")
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

    log = Log(print_enabled=print_enabled)
    if WIFI_PASS == "":
        print("No password was entered, please specify with '-p <password>'")
        exit(2)
    res = connect_to_ap(log)
    while not res:
        res = connect_to_ap(log)
    res = activate(log)
    persist_connection(log)
    # YOU WILL NEVER GET PASSED THIS

