import socket
import struct
import logging
import threading
from typing import Callable


logger = logging.getLogger(__name__)


class TCPCommunicator:
    def __init__(self, remote_host: str, remote_port: int, on_recv: Callable[[bytes], None], max_retries: int = 1):
        self.remote_host: str = remote_host
        self.remote_port: int = remote_port
        self.max_retries: int = max_retries
        self.sock: socket.socket | None = None

        self.on_recv: Callable[[bytes], None] = on_recv

        # Threading control
        self._stop_event: threading.Event = threading.Event()
        self._receive_thread: threading.Thread | None = None

        self._connect()
        self._start_receiver()

    def _connect(self):
        for attempt in range(1, self.max_retries + 1):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.remote_host, self.remote_port))
                logger.info(f"Connected to {self.remote_host}")
                return
            except Exception:
                self.sock = None
                if attempt >= self.max_retries:
                    raise

    def _start_receiver(self):
        self._stop_event.clear()
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def _receive_loop(self):
        logger.info("Receiver thread started.")
        while not self._stop_event.is_set():
            if self.sock is None:
                continue
            try:
                # 1. Read the 4-byte header
                header = self._recv_all(4)
                if not header:
                    break # Connection closed

                payload_len = struct.unpack('!I', header)[0]

                # 2. Read the actual payload
                payload = self._recv_all(payload_len)
                if not payload:
                    break

                self.on_message_received(payload)

            except Exception as e:
                logger.error(f"Receiver error: {e}")
                break
        logger.info("Receiver thread stopped.")

    def _recv_all(self, n: int) -> bytes | None:
        data = bytearray()
        while len(data) < n:
            if not self.sock:
                return None
            try:
                # Request only what is remaining
                packet = self.sock.recv(n - len(data))
                if not packet:
                    return None  # Connection closed prematurely
                data.extend(packet)
            except (socket.error, ConnectionResetError):
                return None

        # Convert to immutable bytes before returning
        return bytes(data)

    def on_message_received(self, payload: bytes):
        logger.debug(f"Received packet: {len(payload)} bytes")
        self.on_recv(payload)

    def send_packets(self, payloads: list[bytes]):
        for payload in payloads:
            length_header = struct.pack('!I', len(payload))
            try:
                if self.sock:
                    self.sock.sendall(length_header + payload)
            except Exception as e:
                logger.error(f"Send failed: {e}")

    def close(self):
        self._stop_event.set()
        if self.sock:
            self.sock.close()
        if self._receive_thread:
            self._receive_thread.join()
