import struct
from config.base import ECUConfig, MethodConfig, ServiceConfig
from config.data import GPSCoordData, SpeedData, SteeringAngleData


ecu_1: ECUConfig = ECUConfig(
    "ecu_2",
    "192.168.1.10",
    "00:11:22:33:44:55",
    [
        ServiceConfig(
            0x0001,
            0x01,
            {
                SpeedData: MethodConfig[SpeedData](
                    0x0001, lambda data: struct.pack(">d", data.val)
                ),
                SteeringAngleData: MethodConfig[SteeringAngleData](
                    0x0002, lambda data: struct.pack(">f", data.val)
                ),
            },
        ),
        ServiceConfig(
            0x0002,
            0x01,
            {
                GPSCoordData: MethodConfig[GPSCoordData](
                    0x0001, lambda data: struct.pack(">dd", data.lat, data.lon)
                )
            },
        ),
    ],
)


ecu_2 = ECUConfig(
    "ecu_2",
    "192.168.1.11",
    "00:11:22:33:44:56",
    [
        ServiceConfig(
            0x0001,
            0x001,
            {
                SpeedData: MethodConfig[SpeedData](
                    0x0001, lambda data: struct.pack(">f", data.val)
                )
            },
        )
    ],
)
