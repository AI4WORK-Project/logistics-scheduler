from dataclasses import dataclass
from typing import List
from dataclasses_json import dataclass_json


@dataclass_json
@dataclass
class Material:
    material: str
    stock_level: int
    stock_capacity: int
    exchange_points: List[str]


@dataclass_json
@dataclass
class DeliveryPickupOrder:
    material: str
    quantity: int
    duration: int


@dataclass_json
@dataclass
class Truck:
    id: str
    waiting_time: int
    delivery_orders: List[DeliveryPickupOrder]
    pickup_orders: List[DeliveryPickupOrder]


@dataclass_json
@dataclass
class LogisticsInstance:
    warehouse: List[Material]
    trucks: List[Truck]

    def __post_init__(self):
        self.validate()

    def validate(self):
        # TODO
        pass