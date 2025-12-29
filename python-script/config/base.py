
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from config.data import DataObject


T = TypeVar("T", bound="DataObject", covariant=True)


@dataclass
class MethodConfig(Generic[T]):
    id: int
    converter: Callable[[T], bytes]


@dataclass
class ServiceConfig:
    id: int
    iface_ver: int
    methods: dict[type, MethodConfig[DataObject]]  # NOTE: this could also be extended to support multiple methods per type


@dataclass
class ECUConfig:
    name: str
    ip: str  # TODO: add a type/format check/validation
    mac: str  # TODO: add a type/format check/validation
    services: list[ServiceConfig]
