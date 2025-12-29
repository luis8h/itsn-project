from collections import defaultdict
from typing import Final
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.sendrecv import sendp
from scapy.main import load_contrib

from config.base import ECUConfig, MethodConfig, ServiceConfig
from config.cfg import MessageType, RetCode, cfg
from config.data import DataObject

load_contrib("automotive.someip")
from scapy.contrib.automotive.someip import SOMEIP


# TODO: first send a service discovery message
# the question is how often this needs to be sent (i guess it is the task of this script and not the remote device)


class SOMEIPSessionManager:
    # Session ID is 16-bit (0x0001 to 0xFFFF)
    MAX_SESSION_ID: Final[int] = 0xFFFF

    def __init__(self) -> None:
        # Key: (service_id, method_id), Value: current_session_id
        self._sessions: dict[tuple[int, int], int] = defaultdict(lambda: 1)

    def get_next_id(self, service_id: int, method_id: int) -> int:
        key: tuple[int, int] = (service_id, method_id)
        current: int = self._sessions[key]

        # Increment and wrap logic
        # If current is 65535, next is 1
        self._sessions[key] = (current % self.MAX_SESSION_ID) + 1

        return current


class SOMEIPForwarder:
    def __init__(self, interface: str, client_id: int):
        self.interface: str = interface
        self.client_id: int = client_id

        self.session_manager: SOMEIPSessionManager = SOMEIPSessionManager()
        self._registry: dict[
            type, list[tuple[ECUConfig, ServiceConfig, MethodConfig[DataObject]]]
        ] = {}

    def register_config(self, ecus: list[ECUConfig]) -> None:
        for ecu in ecus:
            for service in ecu.services:
                for data_type, method in service.methods.items():
                    if data_type not in self._registry:
                        self._registry[data_type] = []
                    self._registry[data_type].append((ecu, service, method))

    def send(self, data: DataObject) -> None:
        targets = self._registry.get(type(data))
        if not targets:
            return

        for ecu, service, method in targets:
            session_id = self.session_manager.get_next_id(service.id, method.id)

            # Construct SOME/IP Layer
            sip = SOMEIP(
                srv_id=service.id,
                sub_id=method.id,
                client_id=self.client_id,
                session_id=session_id,
                msg_type=MessageType.NOTIFICATION,
                proto_ver=cfg.proto_ver,
                iface_ver=service.iface_ver,
                retcode=RetCode.E_OK,
            )

            # Build and send full packet
            pkt = (
                Ether(dst=ecu.mac)
                / IP(dst=ecu.ip)
                / UDP(sport=30490, dport=30490)
                / sip
                / method.converter(data)
            )

            sendp(pkt, iface=self.interface, verbose=False)
