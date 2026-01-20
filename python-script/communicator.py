import socket
import struct
import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

class TCPCommunicator:
    def __init__(self, remote_host: str, remote_port: int, on_recv: Callable[[bytes], None], reconnect_interval: int = 5):
        self.remote_host: str = remote_host
        self.remote_port: int = remote_port
        self.reconnect_interval: int = reconnect_interval
        self.on_recv: Callable[[bytes], None] = on_recv

        self.sock: socket.socket | None = None
        self._stop_event: threading.Event = threading.Event()
        self._receive_thread: threading.Thread | None = None

        # Start the background management thread immediately
        self._start_receiver()

    def _connect(self) -> bool:
        self.close_socket() # Ensure any old socket is cleaned up first

        try:
            new_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            new_sock.settimeout(5.0) # Timeout for the connection attempt
            new_sock.connect((self.remote_host, self.remote_port))

            # Connection successful
            new_sock.settimeout(None) # Set back to blocking mode for recv
            self.sock = new_sock
            logger.info(f"Connected to {self.remote_host}:{self.remote_port}")
            return True
        except (socket.error, ConnectionRefusedError) as e:
            logger.warning(f"Connection failed to {self.remote_host}:{self.remote_port} ({e}). Retrying in {self.reconnect_interval}s...")
            return False

    def _start_receiver(self):
        self._stop_event.clear()
        self._receive_thread = threading.Thread(target=self._receive_loop, daemon=True)
        self._receive_thread.start()

    def _receive_loop(self):
        while not self._stop_event.is_set():
            if self.sock is None:
                if not self._connect():
                    time.sleep(self.reconnect_interval)
                    continue

            try:
                # 1. Read 4-byte header
                header = self._recv_all(4)
                if header is None:
                    raise ConnectionError("Lost connection (empty header)")

                payload_len = struct.unpack('!I', header)[0]

                # 2. Read payload
                payload = self._recv_all(payload_len)
                if payload is None:
                    raise ConnectionError("Lost connection (empty payload)")

                self.on_recv(payload)

            except (ConnectionError, socket.error) as e:
                logger.error(f"Socket error in receiver: {e}")
                self.close_socket()
                time.sleep(self.reconnect_interval)

        logger.info("Receiver thread exiting.")

    def _recv_all(self, n: int) -> bytes | None:
        data = bytearray()
        while len(data) < n:
            current_sock = self.sock # Local reference to prevent NoneType mid-loop
            if not current_sock:
                return None
            try:
                packet = current_sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except socket.error:
                return None
        return bytes(data)

    def send_packets(self, payloads: list[bytes]):
        current_sock = self.sock
        if not current_sock:
            # Silently skip sending if not connected (avoiding ERROR spam)
            return

        for payload in payloads:
            length_header = struct.pack('!I', len(payload))
            try:
                current_sock.sendall(length_header + payload)
            except Exception as e:
                logger.error(f"Send failed: {e}")
                self.close_socket()
                break

    def close_socket(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def close(self):
        self._stop_event.set()
        self.close_socket()
        if self._receive_thread:
            self._receive_thread.join()
