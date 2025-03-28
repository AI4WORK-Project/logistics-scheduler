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
class LogisticsSolution:
    delivery_orders: List[ScheduledOrder]
    pickup_orders: List[ScheduledOrder]
