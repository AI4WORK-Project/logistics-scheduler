import dataclasses
import dataclasses_json
from typing import List


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class ScheduledOrder:
    truck_id: str
    material: str
    quantity: int
    duration: int
    start_time: int
    exchange_point: str


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class TruckScheduleSolution:
    delivery_orders: List[ScheduledOrder]
    pickup_orders: List[ScheduledOrder]


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class TruckExchangePoint:
    truck_id: str
    exchange_point: str


@dataclasses_json.dataclass_json
@dataclasses.dataclass
class LogisticsSolution:
    truck_entrance_order: List[TruckExchangePoint]
