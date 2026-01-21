
from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from config.data import DataObject


# NOTE: Publisher vs Subscriber
# When a service is configured as a Publisher, this script will try to receive data from it. Publisher does not mean that the script is publishing to this service, it means that the configured ecu is publishing on this service and this script wants to receive the data from this ecu.
# In contrast, Subscriber means that this script sends data to this ecu, because the ecu will subscribe to this service.


## --- Method Config ---

# To ensure type safety, this Generic Type is expected to be a DataObject
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
# A service can either contain only publisher or only subscriber methods. This is because ECUs either publish a service aor subscribe to it.

@dataclass
class ServiceConfig:
    id: int
    iface_ver: int


@dataclass
class SubscriberService(ServiceConfig):
    methods: dict[type, SubscriberMethod[DataObject]]


@dataclass
class PublisherService(ServiceConfig):
    methods: dict[type, PublisherMethod[DataObject]]


## --- ECU Config ---
# An ECU can have publisher and subscriber services. This script will send to its Subscriber methods and expect to receive packets over its publisher methods

@dataclass
class ECUConfig:
    name: str
    ip: str
    mac: str
    services: list[ServiceConfig]
