import struct
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.sendrecv import sendp
from scapy.main import load_contrib

from config import DataObject, cfg

# Load the automotive contribution
load_contrib('automotive.someip')

# Now import SOMEIP
from scapy.contrib.automotive.someip import SOMEIP




# should be configured on device because it depends directly on the device
INTERFACE = "veth-carla"

# can be configured in the carla script -> does not depend on the devices hardware, but only on the circuit it is connected to
ECU_MAC = "00:11:22:33:44:55"
SERVICE_ID = 0x1234
METHOD_ID = 0x0001
CLIENT_ID = 0x0000
SESSION_ID = 0x0001


# TODO: first send a service discovery message
# the question is how often this needs to be sent (i guess it is the task of this script and not the remote device)


def send_to_ecu_someip(vehicle_id: int, data: DataObject):
    # 1. Create the SOME/IP Header
    # msg_type=0x02 is 'Notification' (standard for sensor data)
    # Updated snippet for ethernet.py
    sip = SOMEIP(
        srv_id=SERVICE_ID,    # Changed from service_id
        sub_id=METHOD_ID,     # Changed from method_id (sub_id is used for Method/Event)
        client_id=CLIENT_ID,
        session_id=SESSION_ID,
        msg_type=0x02,
        proto_ver=0x01,
        iface_ver=0x01,
        retcode=0x00         # Changed from return_code
    )

    # 2. Pack the Payload (CARLA Data)
    # ECU usually expects specific scaling (e.g., speed * 100 for fixed-point)

    for ecu in cfg.ecus:
        for service in ecu.services:
            if type(data) not in service.methods:
                continue
            payload = service.methods[type(data)].converter(data)

    # payload = struct.pack('!f', float(data))

    # 3. Build the full Ethernet Frame
    # Automotive Ethernet often bypasses OS routing, so we build the whole stack
    pkt = (Ether(dst=ECU_MAC) /
           IP(dst="192.168.1.10") /
           UDP(sport=30490, dport=30490) /
           sip /
           payload)

    # all above this line will always be done, but this line should only be executed when the adapter is directly connected to the host that runs the python script
    # when using the network mode, the whole pkt should be sent over tcp to the other device so that it just needs to be forwarded
    sendp(pkt, iface=INTERFACE, verbose=False)
