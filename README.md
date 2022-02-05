# network-automation
Make repetitive and time consuming tasks easily with network automation. I am working with Cisco switches. Feel free to use the code as you want.

## takeNetworkSnapshot

Connects to the switches defined in switchList.txt file, and gets configuration backups. It also list switches connected to current switch and create network topology diagram. You can select which feature you want to use.

This script is actually combination of createTopologyDiagram and getConfigBackups.

## createTopolgyDiagram
This script connects to the switches by using provided IP addresses, username, and password. It fetches CDP neighbor information. Create a topology that can be seen in a browser.

## getConfigBackups
This script connects to the switches by using provided IP addresses, username, and password. It fetches the full configuration and save it to a 'configBackups' folder.

## configSender

Connects to the switches defined in switchList.txt file, and applies the configuration in configFile.txt file.

## multiConfigSender

Gets multiConfigFile.txt file as input. It connects to the switches and applies the related switch-special configuration. A number sign (#) should be placed at the beginning of the IP address, after that the configuration for that switch can be entered below its IP address.

