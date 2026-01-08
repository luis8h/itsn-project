## ITSN Project


## Tips

#### Test Setup (VLAN)
```sh
# Create the virtual pair (veth-carla and veth-ecu)
sudo ip link add veth-carla type veth peer name veth-ecu

# Bring both ends "UP"
sudo ip link set veth-carla up
sudo ip link set veth-ecu up

# (Optional) Assign an IP to the 'carla' side if needed
sudo ip addr add 192.168.1.5/24 dev veth-carla
```
Now `veth-carla` can be used in the script to send packets and they should appear in wireshark under the interface `veth-ecu`.
Just run the [python script](./python-script/readme.md) and the [tcp-receiver](./tcp-receiver/readme.md). Make sure to configure the receiver to use the `veth-carla` interface.

#### Wireshark - SOME/IP
To make the SOME/IP packets visible in wireshark and show the service, method and session id follow these steps:
- Right-click on that "Data (xx bytes)" row.
- Select "Decode As...".
- In the table that appears, look at the "Current" column for Port 30490.
- Click the dropdown and select SOME/IP.
- Click OK.

#### Real Automotive Ethernet
When using a real automotive ethernet test if packets are received using:
```sh
sudo tcpdump -i <eth-interface> -XX
```
