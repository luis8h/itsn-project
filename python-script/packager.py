import enum
from collections import defaultdict
from typing import Final

from config.base import ECUConfig, MethodConfig, ServiceConfig
from config.data import DataObject
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.main import load_contrib

load_contrib("automotive.someip")
from scapy.contrib.automotive.someip import SOMEIP


class MessageType(int, enum.Enum):
    NOTIFICATION = 0x02

class RetCode(int, enum.Enum):
    E_OK = 0x00


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


class SOMEIPPackager:
    def __init__(self, client_id: int, proto_version: int, ecus: list[ECUConfig]):
        self.client_id: int = client_id
        self.proto_version: int = proto_version
        self.session_manager: SOMEIPSessionManager = SOMEIPSessionManager()

        self._ecu_registry: dict[
            type, list[tuple[ECUConfig, ServiceConfig, MethodConfig[DataObject]]]
        ] = {}
        self.register_config(ecus)

    def register_config(self, ecus: list[ECUConfig]) -> None:
        for ecu in ecus:
            for service in ecu.services:
                for data_type, method in service.methods.items():
                    if data_type not in self._ecu_registry:
                        self._ecu_registry[data_type] = []
                    self._ecu_registry[data_type].append((ecu, service, method))

    def package(self, data: DataObject) -> list[bytes]:
        targets = self._ecu_registry.get(type(data))
        packets: list[bytes] = []

        for ecu, service, method in targets:
            session_id = self.session_manager.get_next_id(service.id, method.id)

            # Construct SOME/IP Layer
            sip = SOMEIP(
                srv_id=service.id,
                sub_id=method.id,
                client_id=self.client_id,
                session_id=session_id,
                msg_type=MessageType.NOTIFICATION,
                proto_ver=self.proto_version,
                iface_ver=service.iface_ver,
                retcode=RetCode.E_OK,
            )

            # Build packet
            pkt = (
                Ether(dst=ecu.mac)
                / IP(dst=ecu.ip)
                / UDP(sport=30490, dport=30490)
                / sip
                / method.converter(data)
            )

            raw_payload = bytes(pkt)
            packets.append(raw_payload)

        return packets

