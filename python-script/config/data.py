from dataclasses import dataclass


# Only used to ensure typesafety
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
