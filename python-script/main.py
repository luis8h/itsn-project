from communicator import TCPCommunicator
from packager import SOMEIPPackager
import time
import logging

from config.cfg import cfg
from config.data import SpeedData

# TODO: add retry after some time if it fails, so that the script can also be started before carla
# TODO: add proper logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main():
    packager = SOMEIPPackager(cfg.client_id, cfg.proto_ver, cfg.ecus)
    communicator = TCPCommunicator(cfg.remote_host, cfg.remote_port)

    while True:
        data = SpeedData(10)

        packages = packager.package(data)
        communicator.send_packets(packages)

        time.sleep(1)


if __name__ == '__main__':
    main()
