import socket
import struct
import logging


logger = logging.getLogger(__name__)


class TCPCommunicator:
    def __init__(self, remote_host: str, remote_port: int, max_retries: int = 1):
        self.remote_host: str = remote_host
        self.remote_port: int = remote_port
        self.max_retries: int = max_retries

        if self.max_retries < 0:
            raise ValueError("max_retries needs to be at least 1")

        self.sock: socket.socket | None = None
        self._connect()

    def _connect(self):
        for attempt in range(1, self.max_retries + 1):
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect((self.remote_host, self.remote_port))
                logger.info(f"Connection to {self.remote_host}:{self.remote_port} was successful after {attempt} attempts")
                return  # success
            except Exception as e:
                self.sock = None
                if attempt >= self.max_retries:
                    logger.info(f"Connection to {self.remote_host}:{self.remote_port} failed")
                    raise


    def send_packets(self, payloads: list[bytes]):
        for payload in payloads:
            # Pack length into 4 bytes, Big Endian (!I)
            length_header = struct.pack('!I', len(payload))

            if self.sock is None:
                self._connect()
            if self.sock is None:
                return

            try:
                self.sock.sendall(length_header + payload)

            except (BrokenPipeError, ConnectionResetError):
                self._connect()
                self.sock.sendall(length_header + payload)
                return

            logger.debug(f"Sent package to {self.remote_host}:{self.remote_port}")
