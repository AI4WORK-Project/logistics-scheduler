from dataclasses import dataclass

from dataclasses_json import DataClassJsonMixin


@dataclass
class DeliveryPickupOrder(DataClassJsonMixin):
    is_delivery: bool
    material: str
    quantity: int
    duration: int
    exchange_point: str | None = None

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.quantity > 0, "Order quantity must be positive."
        assert self.duration > 0, "Order duration must be positive."


@dataclass
class Truck(DataClassJsonMixin):
    id: str
    waiting_time: int
    order: DeliveryPickupOrder

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.waiting_time >= 0, "Truck waiting time cannot be negative."


@dataclass
class MaterialSite(DataClassJsonMixin):
    material: str
    stock_level: int
    stock_capacity: int

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.stock_level >= 0, "Stock level cannot be negative."
        assert self.stock_capacity >= 0, "Stock capacity cannot be negative."
        assert self.stock_capacity >= self.stock_level, (
            "Stock level cannot be greater than stock capacity."
        )


@dataclass
class ExchangePoint(DataClassJsonMixin):
    exchange_point: str
    materials: list[MaterialSite]

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert len({m.material for m in self.materials}) == len(self.materials), (
            f"Duplicate materials found in exchange point '{self.exchange_point}'."
        )


@dataclass
class OngoingOrder(DataClassJsonMixin):
    exchange_point: str
    remaining_duration: int

    def __post_init__(self):
        self.validate()

    def validate(self):
        assert self.remaining_duration > 0, "Remaining duration must be positive."


@dataclass
class LogisticsInstance(DataClassJsonMixin):
    warehouse: list[ExchangePoint]
    trucks: list[Truck]
    ongoing_orders: list[OngoingOrder]

    def __post_init__(self):
        self.validate()

    def validate(self):
        exchange_points = {ep.exchange_point for ep in self.warehouse}
        assert len(exchange_points) == len(self.warehouse), (
            "Duplicate exchange points found."
        )

        assert len({t.id for t in self.trucks}) == len(self.trucks), (
            "Duplicate trucks found."
        )

        materials = {m.material for ep in self.warehouse for m in ep.materials}
        for t in self.trucks:
            assert t.order.material in materials, (
                f"Truck '{t.id}' has an order with material '{t.order.material}', but this material does not exist in the warehouse."
            )

        exchange_point_to_materials = {}
        for ep in self.warehouse:
            exchange_point_to_materials[ep.exchange_point] = {
                m.material for m in ep.materials
            }

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

        assert len({o.exchange_point for o in self.ongoing_orders}) == len(
            self.ongoing_orders
        ), "Duplicate exchange points found in ongoing orders."
