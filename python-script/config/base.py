
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from config.data import DataObject


## --- Method Config ---

T = TypeVar("T", bound="DataObject", covariant=True)


@dataclass
class MethodConfig():
    id: int


@dataclass
class SubscriberMethod(MethodConfig, Generic[T]):
    converter: Callable[[T], bytes]


@dataclass
class PublisherMethod(MethodConfig, Generic[T]):
    converter: Callable[[bytes], T]


## --- Service Config ---

@dataclass
class ServiceConfig:
    id: int
    iface_ver: int


@dataclass
class SubscriberService(ServiceConfig):
    methods: dict[type, SubscriberMethod[DataObject]]  # NOTE: this could also be extended to support multiple methods per type


@dataclass
class PublisherService(ServiceConfig):
    methods: dict[type, PublisherMethod[DataObject]]  # NOTE: this could also be extended to support multiple methods per type


## --- ECU Confug ---

@dataclass
class ECUConfig:
    name: str
    ip: str
    mac: str
    services: list[ServiceConfig]
