from collections import defaultdict
import struct
import socket
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


# TODO: separate package builder and forwarder into separate components

class SOMEIPForwarder:
    def __init__(self, remote_host: str, remote_port: int, client_id: int):
        self.remote_host: str = remote_host
        self.remote_port: int = remote_port
        # self.interface: str = interface
        self.client_id: int = client_id

        self.sock: socket.socket | None = None

        self.session_manager: SOMEIPSessionManager = SOMEIPSessionManager()
        self._registry: dict[
            type, list[tuple[ECUConfig, ServiceConfig, MethodConfig[DataObject]]]
        ] = {}

        self._connect()

    def register_config(self, ecus: list[ECUConfig]) -> None:
        for ecu in ecus:
            for service in ecu.services:
                for data_type, method in service.methods.items():
                    if data_type not in self._registry:
                        self._registry[data_type] = []
                    self._registry[data_type].append((ecu, service, method))

    def _connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.remote_host, self.remote_port))
            print(f"Connected to forwarder at {self.remote_host}:{self.remote_port}")
        except Exception as e:
            print(f"Failed to connect: {e}")
            self.sock = None

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

            # Send to automotive ethernet directly
            # sendp(pkt, iface=self.interface, verbose=False)

            raw_payload = bytes(pkt)
            self._send_over_tcp(raw_payload)

    def _send_over_tcp(self, payload: bytes) -> None:
        if self.sock is None:
            print("Socket not connected, attempting reconnect...")
            self._connect()
            if self.sock is None:
                return # Still failed
        try:
            # Pack length into 4 bytes, Big Endian (!I)
            length_header = struct.pack('!I', len(payload))

            # Send Length + Payload
            self.sock.sendall(length_header + payload)

        except (BrokenPipeError, ConnectionResetError):
            print("Connection lost. Reconnecting...")
            self.sock.close()
            self._connect()
            if self.sock:
                # Retry once
                self.sock.sendall(struct.pack('!I', len(payload)) + payload)
