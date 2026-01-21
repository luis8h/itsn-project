import enum
from collections import defaultdict
from typing import Final

from config.base import (
    ECUConfig,
    PublisherMethod,
    PublisherService,
    ServiceConfig,
    SubscriberMethod,
    SubscriberService,
)
from config.data import DataObject
from scapy.layers.l2 import Ether
from scapy.layers.inet import IP, UDP
from scapy.main import load_contrib
import logging

load_contrib("automotive.someip")
from scapy.contrib.automotive.someip import SOMEIP


logger = logging.getLogger(__name__)


class MessageType(int, enum.Enum):
    NOTIFICATION = 0x02


class RetCode(int, enum.Enum):
    E_OK = 0x00



# This Component manages the session ids and can provide the next available SOME/IP Session ID over a method
class SOMEIPSessionManager:
    # Session ID is 16-bit (0x0001 to 0xFFFF)
    MAX_SESSION_ID: Final[int] = 0xFFFF

    def __init__(self) -> None:
        # Key: (service_id, method_id), Value: current_session_id
        self._sessions: dict[tuple[int, int], int] = defaultdict(lambda: 1)

    def get_next_id(self, service_id: int, method_id: int) -> int:
        # Session ids are unique per method
        key: tuple[int, int] = (service_id, method_id)
        current: int = self._sessions[key]

        # Increment and wrap logic
        # If current is 65535, next is 1
        self._sessions[key] = (current % self.MAX_SESSION_ID) + 1

        return current


# This Component can be used to package and unpackage data.
# It needs the list of configured ECUs
class SOMEIPPackager:
    def __init__(self, client_id: int, proto_version: int, ecus: list[ECUConfig]):
        self.client_id: int = client_id
        self.proto_version: int = proto_version
        self.session_manager: SOMEIPSessionManager = SOMEIPSessionManager()

        # holds all methods which data needs to be sent
        self._ecu_send_registry: dict[
            type, list[tuple[ECUConfig, ServiceConfig, SubscriberMethod[DataObject]]]
        ] = {}
        # holds full ecu config to determine where the message is coming from afterwards
        self._ecu_recv_registry: dict[
            tuple[int, int],  # (service_id, method_id)
            list[
                tuple[ECUConfig, PublisherService, PublisherMethod[DataObject]]
            ],
        ] = {}
        self.register_config(ecus)

    def register_config(self, ecus: list[ECUConfig]) -> None:
        for ecu in ecus:
            for service in ecu.services:
                # --- SENDER REGISTRY (Subscribers) ---
                if isinstance(service, SubscriberService):
                    for data_type, method in service.methods.items():
                        self._ecu_send_registry.setdefault(data_type, []).append(
                            (ecu, service, method)
                        )

                # --- RECEIVER REGISTRY (Publishers) ---
                elif isinstance(service, PublisherService):
                    for data_type, method in service.methods.items():
                        key = (service.id, method.id)

                        if key not in self._ecu_recv_registry:
                            self._ecu_recv_registry[key] = []

                        self._ecu_recv_registry[key].append((ecu, service, method))

    def package(self, data: DataObject) -> list[bytes]:
        targets = self._ecu_send_registry.get(type(data))
        packets: list[bytes] = []

        if targets is None:
            return []

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

    # NOTE: This method currently can return a list of DataObjects, but this could be restricted to one DataObject in the future
    def unpackage(self, raw_data: bytes) -> list[DataObject]:
        pkt = Ether(raw_data)

        if not pkt.haslayer(SOMEIP):
            return []

        # Get the SOME/IP header object for ID lookup
        sip = pkt[SOMEIP]
        src_ip = pkt[IP].src

        # Get the full UDP payload (Header + Data + Padding) as raw bytes
        full_udp_payload = bytes(pkt[UDP].payload)

        key = (sip.srv_id, sip.sub_id)
        targets = self._ecu_recv_registry.get(key)

        if not targets:
            logger.warning(
                f"Received unknown SOME/IP Service/Method ID: {key} from IP {src_ip}"
            )
            return []

        unpacked_objects: list[DataObject] = []

        for ecu, _, method in targets:
            if ecu.ip == src_ip:
                # sip.len covers bytes starting AFTER the Length field.
                # The header fields after Length (ReqID..RetCode) take up 8 bytes.
                payload_len = sip.len - 8

                # The SOME/IP header is exactly 16 bytes long.
                header_offset = 16
                actual_payload = full_udp_payload[
                    header_offset : header_offset + payload_len
                ]

                if len(actual_payload) != payload_len:
                    logger.error(
                        f"Payload mismatch! Expected {payload_len}, got {len(actual_payload)}"
                    )
                    continue

                try:
                    data_obj = method.converter(actual_payload)
                    unpacked_objects.append(data_obj)
                except Exception as e:
                    logger.error(f"Converter failed: {e}")

        return unpacked_objects
