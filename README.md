# printerpi_boot_script
Python script to be run the octopi. Will automatically connect to the HUB and activate it, providing the information needed to communicate back.
###Preinstallation
####Octopi
This api relies on Octopi and assumes you have some knowledge of it. Please visit https://github.com/guysoft/OctoPi for information on Octopi. Before installing this software you must have set up a default slicing and printer profile, along with the API-Key.
###Installation
####Requirements
Must be installed on a debian based distro, ie. raspbian, ubuntu
####Instructions
#####Interface
The interface to use for connecting to the HUB. This will most likely be your wireless adapter, ie. wlan0
#####Config file
The file to write command line configuration to. Default is recommended
#####Network SSID
The SSID of the Wireless Access Point that the HUB will be broadcasting. 
#####Network Password
The password of the Wireless Access Point.
#####Black Box UID
The UID of the blackbox that the printerpi and printer should be plugged into.
#####IP Address
The IP Address of the HUB's webserver
#####Port
The Port of the HUB's webserver
