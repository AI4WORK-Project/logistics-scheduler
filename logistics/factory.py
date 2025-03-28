import collections
from typing import List, Dict, Optional
from ortools.sat.python import cp_model
from .instance import LogisticsInstance, DeliveryPickupOrder
from .solution import LogisticsSolution, ScheduledOrder


optional_activity_type = collections.namedtuple(
    "optional_activity_type", "start duration interval is_present params"
)


class LogisticsSchedulingFactory:

    def __init__(self, instance: LogisticsInstance):
        self.instance = instance
        self.materials = dict(map(lambda m: (m.material, m), self.instance.warehouse))
        self.exchange_points = set(
            p for m in self.materials.values() for p in m.exchange_points
        )
        self.upper_bound = self.calculate_upper_bound()
        self.delivery_activities: List[optional_activity_type] = []
        self.pickup_activities: List[optional_activity_type] = []
        self.model = self.get_optimization_model()

    def calculate_upper_bound(self) -> int:
        upper_bound = 0
        for truck in self.instance.trucks:
            for order in truck.delivery_orders + truck.pickup_orders:
                upper_bound += order.duration
        return upper_bound

    def add_optional_activity(
        self, model: cp_model.CpModel, name, duration, params=None
    ) -> optional_activity_type:
        """Add an optional activity to the model."""

        start_var = model.new_int_var(0, self.upper_bound, "start_" + name)
        is_present_var = model.new_bool_var("is_present_" + name)
        interval_var = model.new_optional_fixed_size_interval_var(
            start_var, duration, is_present_var, "interval_" + name
        )
        return optional_activity_type(
            start=start_var,
            duration=duration,
            interval=interval_var,
            is_present=is_present_var,
            params=params,
        )

    def add_delivery_pickup_activities(
        self,
        model: cp_model.CpModel,
        orders: List[DeliveryPickupOrder],
        truck_id: str,
        prefix: str,
    ):
        activities = []
        for order in orders:
            order_activities = []
            for exchange_point in self.materials[order.material].exchange_points:
                activity = self.add_optional_activity(
                    model,
                    f"{prefix}_{truck_id}_{order.material}_{exchange_point}",
                    order.duration,
                    params={
                        "truck_id": truck_id,
                        "exchange_point": exchange_point,
                        "order": order,
                    },
                )
                order_activities.append(activity)
            model.add_exactly_one(map(lambda a: a.is_present, order_activities))
            activities += order_activities
        return activities

    def enforce_delivery_before_pickup(
        self, model: cp_model.CpModel, delivery_activities, pickup_activities, truck_id
    ):
        if len(delivery_activities) == 0 or len(pickup_activities) == 0:
            return

        delivery_end = model.new_int_var(
            0, self.upper_bound, f"delivery_end_{truck_id}"
        )
        pickup_start = model.new_int_var(
            0, self.upper_bound, f"pickup_start_{truck_id}"
        )
        model.add_min_equality(
            pickup_start, map(lambda act: act.start, pickup_activities)
        )
        model.add_max_equality(
            delivery_end, map(lambda act: act.start + act.duration, delivery_activities)
        )
        model.add(pickup_start >= delivery_end)

    def enforce_exchange_point_constraints(self, model: cp_model.CpModel):
        activities = self.delivery_activities + self.pickup_activities
        for exchange_point in self.exchange_points:
            exchange_point_activities = filter(
                lambda act: act.params["exchange_point"] == exchange_point, activities
            )
            model.add_no_overlap(
                map(lambda act: act.interval, exchange_point_activities)
            )

    def enforce_stock_constraints(self, model: cp_model.CpModel):
        for material in self.instance.warehouse:
            delivery_activities = list(
                filter(
                    lambda act: act.params["order"].material == material.material,
                    self.delivery_activities,
                )
            )
            pickup_activities = list(
                filter(
                    lambda act: act.params["order"].material == material.material,
                    self.pickup_activities,
                )
            )

            times = [0] + list(
                map(
                    lambda act: act.start + act.duration,
                    delivery_activities + pickup_activities,
                )
            )
            level_changes = (
                [material.stock_level]
                + list(
                    map(lambda act: act.params["order"].quantity, delivery_activities)
                )
                + list(
                    map(lambda act: -act.params["order"].quantity, pickup_activities)
                )
            )

            actives = [True] + list(
                map(lambda act: act.is_present, delivery_activities + pickup_activities)
            )
            model.add_reservoir_constraint_with_active(
                times,
                level_changes,
                actives,
                min_level=0,
                max_level=material.stock_capacity,
            )

    def add_quality_metric(self, model: cp_model.CpModel):
        """Sets the objective of the model to minimize."""

        makespan_var = model.new_int_var(0, self.upper_bound, "makespan")
        activities = self.delivery_activities + self.pickup_activities
        model.add_max_equality(
            makespan_var,
            [activity.start + activity.duration for activity in activities],
        )

        truck_makespan_vars = []
        for truck in self.instance.trucks:
            truck_makespan_var = model.new_int_var(
                0, self.upper_bound, f"makespan_{truck.id}"
            )
            truck_makespan_vars.append(truck_makespan_var)
            truck_activities = filter(
                lambda act: act.params["truck_id"] == truck.id, activities
            )
            model.add_max_equality(
                truck_makespan_var,
                [activity.start + activity.duration for activity in truck_activities],
            )

        # model.minimize(10 * makespan_var + sum(truck_makespan_vars))
        model.minimize(sum(truck_makespan_vars))

    def get_optimization_model(self) -> cp_model.CpModel:
        model = cp_model.CpModel()
        for truck in self.instance.trucks:
            delivery_activities = self.add_delivery_pickup_activities(
                model, truck.delivery_orders, truck.id, "delivery"
            )
            pickup_activities = self.add_delivery_pickup_activities(
                model, truck.pickup_orders, truck.id, "pickup"
            )
            model.add_no_overlap(
                map(lambda a: a.interval, delivery_activities + pickup_activities)
            )
            self.enforce_delivery_before_pickup(
                model, delivery_activities, pickup_activities, truck.id
            )
            self.delivery_activities += delivery_activities
            self.pickup_activities += pickup_activities

        self.enforce_exchange_point_constraints(model)
        self.enforce_stock_constraints(model)
        self.add_quality_metric(model)

        return model

    def get_solution(
        self, time_limit: Optional[int] = None
    ) -> Optional[LogisticsSolution]:
        solver = cp_model.CpSolver()
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = time_limit

        status = solver.solve(self.model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:

            def construct_scheduled_orders(activities):
                scheduled_orders = []
                for activity in activities:
                    if solver.value(activity.is_present):
                        truck_id = activity.params["truck_id"]
                        exchange_point = activity.params["exchange_point"]
                        order: ScheduledOrder = activity.params["order"]
                        scheduled_order = ScheduledOrder(
                            truck_id,
                            order.material,
                            order.quantity,
                            order.duration,
                            solver.value(activity.start),
                            exchange_point,
                        )
                        scheduled_orders.append(scheduled_order)
                return scheduled_orders

            delivery_orders = construct_scheduled_orders(self.delivery_activities)
            pickup_orders = construct_scheduled_orders(self.pickup_activities)
            return LogisticsSolution(delivery_orders, pickup_orders)

        else:
            return None
