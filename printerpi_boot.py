#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import getopt
import requests
import socket
import json
import netifaces as ni
from getpass import getuser
from wifi import Cell, Scheme
from uuid import getnode as get_mac
from time import sleep

def get_uuid(fpath):
    if os.path.isfile(fpath):
        with open(fpath, 'r') as f:
            uuid = long(f.read())
    else:
        uuid = get_mac()
        with open(fpath, 'w') as f:
            f.write(str(uuid))
    return str(uuid)

def get_ipaddress(interface):
    return str(ni.ifaddresses(interface)[ni.AF_INET][0].get('addr'))


if __name__ == "__main__":
    wifi_ssid        = "StratusPrint"
    wifi_pass        = ""
    wifi_interface   = "wlan0"
    wifi_profile     = "stratus"
    interface_dir    = "/etc/network"
    interface_file   = "/etc/network/interfaces"
    printer_activate = "/printers/activate"
    base_url         = "http://192.168.0.1:5000"
    #base_url = "http://stratuspi:5000"
    uuid_file        = ".uuid"
    api_key          = "THISISNOTAGOODKEY"
    port             = 80

    if getuser() != 'root':
        print("Must be run as root...")
        exit(1)

    try:
        # Short option syntax: "hv:"
        # Long option syntax: "help" or "verbose="
        opts, args = getopt.getopt(sys.argv[1:],
                                   "hs:p:i:a:",
                                   ["help","ssid=","pass="
                                       ,"interface=","apikey="])
    
    except(getopt.GetoptError, err):
        # Print debug info
        print str(err)
        error_action
    
    for opt, arg in opts:
        if opt in ["-h", "--help"]:
            print("Usage: run.py -h -s <ssid> -p <password>")
        elif opt in ["-s", "--ssid"]:
            wifi_ssid = arg
        elif opt in ["-p", "--pass", "--password"]:
            wifi_pass = arg
        elif opt in ["-i", "--interface"]:
            wifi_interface = arg
        elif opt in ["-a", "--apikey"]:
            API_KEY = arg

    if wifi_pass == "":
        print("No password was entered, please specify with '-p <password>'")
        exit(2)
    print("Connecting to " + wifi_ssid + " using " + wifi_interface)

    # Complicated way to account for the file not existing
    try:
        scheme = Scheme.find(wifi_interface, wifi_profile)
    except IOError:
        scheme = None
        if not os.path.isdir(interface_dir):
            os.mkdir(interface_dir, 0755)
            os.open(interface_file, 0644).close()
        elif not os.path.isfile(interface_file):
            os.open(interface_file, 0644).close()

    if scheme == None:
        cells = Cell.all(wifi_interface)
        for cell in cells:
            if cell.ssid == wifi_ssid:
                scheme = Scheme.for_cell(wifi_interface,
                                         wifi_profile,
                                         cell,
                                         passkey=wifi_pass)
                scheme.save()
            else:
                print("SSID " + wifi_ssid + " was not found. Exiting...")

    if scheme.activate() == False:
        print("Could not connect to " + wifi_ssid + ". Exiting...")
        exit(3)
    print("Connected!")

    payload = {
            "uuid": get_uuid(uuid_file),
            "ip": get_ipaddress(wifi_interface),
            "key": str(api_key),
            "port": str(port)
    }
    url = base_url + printer_activate + "?payload=" + json.dumps(payload)
    print("Activating printer, watch output of details")
    for i in range(100):
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == requests.codes.ok:
                print("Response was okay! Good to go. Exiting...")
                exit(0)
            else:
                #TODO make this more descriptive
                print("Response was " + r.status_code
                        + ". Something went wrong")
                exit(4)
        except:
            print("Error occured, will try " + str(100 - 1) + " more times.")
            sleep(1)
    print("No connection after 100 attempts. Call the ghostbusters")
    exit(5)

