from communicator import TCPCommunicator
from packager import SOMEIPPackager
import time
import logging

from config.cfg import cfg
from config.data import SpeedData


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def receive_callback(data: bytes):
    logger.info(f"Received message: {data}")


def main():
    packager = SOMEIPPackager(cfg.client_id, cfg.proto_ver, cfg.ecus)
    communicator = TCPCommunicator(cfg.cmd.remote_host, cfg.cmd.remote_port, receive_callback)

    while True:
        data = SpeedData(10)

        packages = packager.package(data)
        communicator.send_packets(packages)

        time.sleep(1)


if __name__ == '__main__':
    main()
