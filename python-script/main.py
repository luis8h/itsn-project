from communicator import TCPCommunicator
from packager import SOMEIPPackager
import time
import logging

from config.cfg import cfg
from config.data import SpeedData, SteeringAngleData


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main():
    packager = SOMEIPPackager(cfg.client_id, cfg.proto_ver, cfg.ecus)

    def receive_callback(data: bytes):
        logger.debug(f"Received message: {data}")
        payload = packager.unpackage(data)
        logger.info(f"Received payload: {payload}")

    communicator = TCPCommunicator(cfg.cmd.remote_host, cfg.cmd.remote_port, receive_callback)

    while True:
        data_speed = SpeedData(10)
        data_steer = SteeringAngleData(120)

        packages = packager.package(data_speed)
        communicator.send_packets(packages)

        time.sleep(0.5)

        packages = packager.package(data_steer)
        communicator.send_packets(packages)

        time.sleep(1)


if __name__ == '__main__':
    main()
