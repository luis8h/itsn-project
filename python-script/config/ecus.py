import struct
from config.base import (
    ECUConfig,
    PublisherMethod,
    PublisherService,
    SubscriberMethod,
    SubscriberService,
)
from config.data import GPSCoordData, SpeedData, SteeringAngleData


ecu_1: ECUConfig = ECUConfig(
    "ecu_2",
    "192.168.1.10",
    "00:11:22:33:44:55",
    [
        SubscriberService(
            0x0001,
            0x01,
            {
                SpeedData: SubscriberMethod[SpeedData](
                    0x0001, lambda data: struct.pack(">d", data.val)
                ),
                SteeringAngleData: SubscriberMethod[SteeringAngleData](
                    0x0002, lambda data: struct.pack(">f", data.val)
                ),
            },
        ),
    ],
)


# Confoguring a publisher which means that the script is expecting packets from this ecu.
ecu_2 = ECUConfig(
    "GPS Publisher",
    "192.168.1.5", # Important to set this correctly
    "00:11:22:33:44:56",
    [
        PublisherService(
            0x0002,
            0x001,
            {
                GPSCoordData: PublisherMethod[GPSCoordData](
                    0x0001,
                    lambda data_bytes: GPSCoordData(*struct.unpack(">dd", data_bytes[:16])),
                )
            },
        )
    ],
)
