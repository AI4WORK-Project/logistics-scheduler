from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import List, Optional

# TODO: not ideal to use error class from apiflask here. server.py should be
# adapted to catch the assertion errors, and return a corresponding error response.
from apiflask import HTTPError


@dataclass_json
@dataclass
class DeliveryPickupOrder:
    is_delivery: bool
    material: str
    quantity: int
    duration: int
    exchange_point: Optional[str] = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        try:
            assert self.quantity > 0, "Order quantity must be positive."
            assert self.duration > 0, "Order duration must be positive."
        except Exception as e:
            raise HTTPError(status_code=422, message="Validation error", detail=str(e))


@dataclass_json
@dataclass
class Truck:
    id: str
    waiting_time: int
    order: DeliveryPickupOrder

    def __post_init__(self):
        self.validate()

    def validate(self):
        try:
            assert self.waiting_time >= 0, "Truck waiting time cannot be negative."
        except Exception as e:
            raise HTTPError(status_code=422, message="Validation error", detail=str(e))


@dataclass_json
@dataclass
class MaterialSite:
    material: str
    stock_level: int
    stock_capacity: int

    def __post_init__(self):
        self.validate()

    def validate(self):
        try:
            assert self.stock_level >= 0, "Stock level cannot be negative."
            assert self.stock_capacity >= 0, "Stock capacity cannot be negative."
            assert self.stock_capacity >= self.stock_level, (
                "Stock level cannot be greater than stock capacity."
            )
        except Exception as e:
            raise HTTPError(status_code=422, message="Validation error", detail=str(e))


@dataclass_json
@dataclass
class ExchangePoint:
    exchange_point: str
    materials: List[MaterialSite]

    def __post_init__(self):
        self.validate()

    def validate(self):
        try:
            assert len(set(m.material for m in self.materials)) == len(
                self.materials
            ), f"Duplicate materials found in exchange point '{self.exchange_point}'."
        except Exception as e:
            raise HTTPError(status_code=422, message="Validation error", detail=str(e))


@dataclass_json
@dataclass
class OngoingOrder:
    exchange_point: str
    remaining_duration: int

    def __post_init__(self):
        self.validate()

    def validate(self):
        try:
            assert self.remaining_duration > 0, "Remaining duration must be positive."
        except Exception as e:
            raise HTTPError(status_code=422, message="Validation error", detail=str(e))


@dataclass_json
@dataclass
class LogisticsInstance:
    warehouse: List[ExchangePoint]
    trucks: List[Truck]
    ongoing_orders: List[OngoingOrder]

    def __post_init__(self):
        self.validate()

    def validate(self):
        try:
            exchange_points = set(ep.exchange_point for ep in self.warehouse)
            assert len(exchange_points) == len(self.warehouse), (
                "Duplicate exchange points found."
            )

            assert len(set(t.id for t in self.trucks)) == len(self.trucks), (
                "Duplicate trucks found."
            )

            materials = set(m.material for ep in self.warehouse for m in ep.materials)
            for t in self.trucks:
                assert t.order.material in materials, (
                    f"Truck '{t.id}' has an order with material '{t.order.material}', but this material does not exist in the warehouse."
                )

            exchange_point_to_materials = {}
            for ep in self.warehouse:
                exchange_point_to_materials[ep.exchange_point] = set(
                    m.material for m in ep.materials
                )

            for t in self.trucks:
                if t.order.exchange_point is not None:
                    assert t.order.exchange_point in exchange_points, (
                        f"The exchange point '{t.order.exchange_point}' required by truck '{t.id}' does not exist."
                    )

                    assert (
                        t.order.material
                        in exchange_point_to_materials[t.order.exchange_point]
                    ), (
                        f"The exchange point '{t.order.exchange_point}' required by truck '{t.id}' does not provide material '{t.order.material}'."
                    )

            for order in self.ongoing_orders:
                assert order.exchange_point in exchange_points, (
                    f"The exchange point '{order.exchange_point}' does not exist."
                )

            assert len(set(o.exchange_point for o in self.ongoing_orders)) == len(
                self.ongoing_orders
            ), "Duplicate exchange points found in ongoing orders."
        except Exception as e:
            raise HTTPError(status_code=422, message="Validation error", detail=str(e))
