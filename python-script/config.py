from dataclasses import dataclass
import struct
from typing import Callable, Generic, TypeVar


class DataObject:
    pass


@dataclass
class SpeedData(DataObject):
    val: float


@dataclass
class SteeringAngleData(DataObject):
    val: int


@dataclass
class GPSCoordData(DataObject):
    lat: float
    lon: float


T = TypeVar("T", bound="DataObject", covariant=True)


@dataclass
class MethodConfig(Generic[T]):
    id: int
    converter: Callable[[T], bytes]


@dataclass
class ServiceConfig:
    id: int
    methods: dict[type, MethodConfig[DataObject]]  # NOTE: this could also be extended to support multiple methods per type


@dataclass
class ECUConfig:
    name: str
    ip: str  # TODO: add a type/format check/validation
    mac: str  # TODO: add a type/format check/validation
    services: list[ServiceConfig]


def conv_speed(data: SpeedData) -> bytes:
    return struct.pack(">d", data.val)


def conv_speed_2(data: SpeedData) -> bytes:
    return struct.pack(">f", data.val)


def conv_steering_angle(data: SteeringAngleData) -> bytes:
    return struct.pack(">f", data.val)


def conv_gpscoord(data: GPSCoordData) -> bytes:
    return struct.pack(">dd", data.lat, data.lon)


@dataclass
class Config:
    client_id: int = 0x0001  # id of the carla client (same for all messages)
    ecus: list[ECUConfig] = [
        ECUConfig(
            "kombi",
            "192.168.1.10",
            "00:11:22:33:44:55",
            [
                ServiceConfig(
                    0x0001,
                    {
                        SpeedData: MethodConfig[SpeedData](
                            0x0001, conv_speed
                        ),
                        SteeringAngleData: MethodConfig[SteeringAngleData](
                            0x0002, conv_steering_angle
                        ),
                    },
                ),
                ServiceConfig(
                    0x0002,
                    {GPSCoordData: MethodConfig[GPSCoordData](0x0001, conv_gpscoord)},
                ),
            ],
        ),
        ECUConfig(
            "kombi2",
            "192.168.1.11",
            "00:11:22:33:44:56",
            [
                ServiceConfig(
                    0x0001, {SpeedData: MethodConfig[SpeedData](0x0001, conv_speed_2)}
                )
            ],
        ),
    ]

    # TODO: potential performance improvement (maybe use caching)
    # def __post_init__(self):
    #     # Create a flattened lookup: {DataType: [(ecu_ip, service_id, method), ...]}
    #     self._lookup = {}
    #     for ecu in self.ecus:
    #         for service in ecu.services:
    #             for dtype, method in service.methods.items():
    #                 if dtype not in self._lookup:
    #                     self._lookup[dtype] = []
    #                 self._lookup[dtype].append((ecu, service, method))
    #
    # def get_destinations(self, data: DataObject):
    #     return self._lookup.get(type(data), [])

    # use like this:
    # def send_to_ecu_someip(data: DataObject):
    # for ecu, service, method in cfg.get_destinations(data):
    #     payload = method.converter(data)
    #     # socket.sendto(...)


cfg = Config()
