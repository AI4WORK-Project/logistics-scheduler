from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List


@dataclass_json
@dataclass
class Material:
    material: str
    stock_level: int
    stock_capacity: int
    exchange_points: List[str]

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.stock_level >= 0, "Stock level cannot be negative"
        assert self.stock_capacity >= 0, "Stock capacity cannot be negative"
        assert (
            self.stock_capacity >= self.stock_level
        ), "Stock level cannot be greater than stock capacity"


@dataclass_json
@dataclass
class DeliveryPickupOrder:
    material: str
    quantity: int
    duration: int

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.quantity > 0, "Quantity must be positive"
        assert self.duration > 0, "Duration must be positive"


@dataclass_json
@dataclass
class Truck:
    id: str
    waiting_time: int
    delivery_orders: List[DeliveryPickupOrder]
    pickup_orders: List[DeliveryPickupOrder]

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.waiting_time >= 0, "Waiting time cannot be negative"


@dataclass_json
@dataclass
class LogisticsInstance:
    warehouse: List[Material]
    trucks: List[Truck]

    def __post_init__(self):
        self.validate()

    def validate(self):
        materials = set(material.material for material in self.warehouse)
        trucks = set(truck.id for truck in self.trucks)

        assert len(materials) == len(
            self.warehouse
        ), "Duplicate materials found in warehouse"
        assert len(trucks) == len(self.trucks), "Duplicate trucks found"

        for truck in self.trucks:
            for order in truck.delivery_orders + truck.pickup_orders:
                assert (
                    order.material in materials
                ), f"Material {order.material} not found in warehouse"
