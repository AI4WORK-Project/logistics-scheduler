from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin


@dataclass
class ScheduledOrder(DataClassJsonMixin):
    truck_id: str
    material: str
    quantity: int
    duration: int
    start_time: int
    exchange_point: str


@dataclass
class TruckScheduleSolution(DataClassJsonMixin):
    delivery_orders: list[ScheduledOrder]
    pickup_orders: list[ScheduledOrder]


@dataclass
class TruckExchangePoint(DataClassJsonMixin):
    truck_id: str
    exchange_point: str


@dataclass
class LogisticsSolution(DataClassJsonMixin):
    truck_entrance_order: list[TruckExchangePoint]
