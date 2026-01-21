import struct
from communicator import TCPCommunicator
from config.base import ECUConfig, PublisherMethod, PublisherService, SubscriberMethod, SubscriberService
from packager import SOMEIPPackager
import time
import logging

from config.cfg import cfg
from config.data import GPSCoordData, SpeedData, SteeringAngleData


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)



# Configuring a subscriber here, so that this script will send the mocked GPS Data to this ecu.
ecu_sending = ECUConfig(
    "GPS Subscriber",
    "192.168.1.11",
    "00:11:22:33:44:56",
    [
        SubscriberService(
            0x0002,
            0x001,
            {
                GPSCoordData: SubscriberMethod[GPSCoordData](
                    0x0001, lambda data: struct.pack(">dd", data.lat, data.lon)
                )
            },
        ),
        # In theory it would be possible to configure a PublisherService here too, but as this script should inpersonate this ECU, it does not make sense because this would mean that this script wants to receive data from itself ECU.
    ],
)

# Also configrue a receiving ecu
ecu_receiving = ECUConfig(
    "Speed Publisher",
    "192.168.1.5",
    "00:11:22:33:44:56",
    [
        PublisherService(
            0x0001,
            0x001,
            {
                SpeedData: PublisherMethod[SpeedData](
                    0x0001, lambda data_bytes: struct.unpack(">d", data_bytes)[0]
                ),
                SteeringAngleData: PublisherMethod[SteeringAngleData](
                    0x0002, lambda data_bytes: struct.unpack(">f", data_bytes)[0]
                )
            },
        )
    ],
)


def main():
    packager = SOMEIPPackager(cfg.client_id, cfg.proto_ver, [ecu_receiving, ecu_sending])

    def receive_callback(data: bytes):
        logger.debug(f"Received message: {data}")
        payload = packager.unpackage(data)
        logger.info(f"Received payload: {payload}")

    communicator = TCPCommunicator(cfg.cmd.remote_host, cfg.cmd.remote_port, receive_callback)

    while True:
        data = GPSCoordData(10.0, 7.1)

        packages = packager.package(data)
        communicator.send_packets(packages)

        time.sleep(1)


if __name__ == '__main__':
    main()
