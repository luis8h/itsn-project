from config.base import ECUConfig
from config.ecus import ecu_1, ecu_2
import enum


# TODO: use a library here that lets all config values be set from the command line
class Config:
    client_id: int = 0x0001  # id of the carla client (same for all messages)
    ecus: list[ECUConfig] = [ecu_1, ecu_2]
    eth_interface: str = "veth-carla"  # optional (only required if the script is connected to automotive ethernet directly)
    proto_ver: int = 0x01
    remote_host: str = "127.0.0.1"
    remote_port: int = 9000

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
