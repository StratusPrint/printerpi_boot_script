#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import subprocess
from getpass import getuser

def systemd_setup(config):
    try:
        with open("/dev/null","w") as out:
            subprocess.call(['systemctl'],stdout=out)
    except OSError:
        return False
    new = []
    cwd = os.getcwd()
    command = "/usr/bin/python2 " + cwd + "/connect.py -c " + config
    with open("systemd.unit", "r") as f:
        for line in f:
            line = line.replace("$DIRECTORY$",cwd)
            line = line.replace("$COMMAND$", command)
            new.append(line)
    with open("/usr/lib/systemd/system/stratusprint-printer.service", "w+") as f:
        f.writelines(new)
    with open("/dev/null","w") as out:
        subprocess.call(['systemctl','daemon-reload'],stdout=out)
        subprocess.call(['systemctl','enable','stratusprint-printer.service'],stdout=out)
    return True

def initd_setup(config):
    new = []
    cwd = os.getcwd()
    command = "/usr/bin/python2 " + cwd + "/connect.py -c " + config
    script_path = "/etc/init.d/stratusprint-printer"
    with open("init.d.script", "r") as f:
        for line in f:
            line = line.replace("$COMMAND$", command)
            new.append(line)
    with open(script_path, "w+") as f:
        f.writelines(new)
    os.chmod(script_path, 0755)
    with open("/dev/null","w") as out:
        subprocess.call(["update-rc.d","stratusprint-printer","defaults"])
    return True


if __name__ == "__main__":
    if getuser() != 'root':
        print("Must be run as root...")
        exit(1)
    interface = raw_input("Interface[wlan0]:")
    config    = raw_input("Config File[arguments.config]:")
    ssid      = raw_input("Network SSID[REQUIRED]:")
    wpass     = raw_input("Network Password[REQUIRED]:")
    api_key   = raw_input("Octoprint API-Key[REQUIRED]: ")

    if api_key == "":
        print("Did not provide an api_key...Exiting")
        exit(1)
    if ssid == "":
        print("Did not provide an SSID...Exiting")
        exit(1)
    if wpass == "":
        print("Did not provide a Password...Exiting")
        exit(1)
    if interface == "":
        interface = "wlan0"
    if config == "":
        config = "arguments.config"
    with open(config,"w+") as f:
        f.writelines(["-a " + str(api_key) + "\n"
                    , "-i " + str(interface) + "\n"
                    , "-s " + str(ssid) + "\n"
                    , "-p " + str(wpass) + "\n"])

    if systemd_setup(config):
        print("Finished systemd setup")
        run = raw_input("All set, run now and test? [y/n]:")
        if run.lower() in ["y", "yes"]:
            subprocess.call(['systemctl','start','stratusprint-printer'])
    else:
        if initd_setup(config):
            pass


