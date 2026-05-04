import collections
from typing import List, Tuple, Dict, Optional, Iterator
from ortools.sat.python import cp_model
from .instance import (
    LogisticsInstance,
    DeliveryPickupOrder,
    ExchangePoint,
    MaterialSite,
)
from .solution import (
    TruckScheduleSolution,
    ScheduledOrder,
    LogisticsSolution,
    TruckExchangePoint,
)


optional_activity_type = collections.namedtuple(
    "optional_activity_type", "start duration interval is_present params"
)


class LogisticsSchedulingFactory:

    def __init__(self, instance: LogisticsInstance):
        self.instance = instance

        self.material_to_exchange_point: Dict[str, List[ExchangePoint]] = {}
        for ep in self.instance.warehouse:
            for m in ep.materials:
                if m.material not in self.material_to_exchange_point:
                    self.material_to_exchange_point[m.material] = []
                self.material_to_exchange_point[m.material].append(ep.exchange_point)

        self.material_sites: Dict[Tuple[str, str], MaterialSite] = {}
        for ep in self.instance.warehouse:
            for m in ep.materials:
                self.material_sites[(ep.exchange_point, m.material)] = m

        self.exchange_point_busy_duration = {
            o.exchange_point: o.remaining_duration for o in self.instance.ongoing_orders
        }
        for ep in self.instance.warehouse:
            if ep.exchange_point not in self.exchange_point_busy_duration:
                self.exchange_point_busy_duration[ep.exchange_point] = 0

        self.upper_bound = self.calculate_upper_bound()
        self.model, self.activities = self.get_optimization_model()
        self.truck_schedule_solution = None

    def calculate_upper_bound(self) -> int:
        # TODO: improve estimation
        upper_bound = 0
        for truck in self.instance.trucks:
            upper_bound += truck.order.duration
        return upper_bound

    def add_optional_activity(
        self,
        model: cp_model.CpModel,
        name: str,
        duration: int,
        start_lower_bound: int = 0,
        params: Optional[Dict] = None,
    ) -> optional_activity_type:
        """Add an optional activity to the model."""

        start_var = model.new_int_var(
            start_lower_bound, self.upper_bound, "start_" + name
        )
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

    def add_delivery_pickup_activity(
        self, model: cp_model.CpModel, order: DeliveryPickupOrder, truck_id: str
    ) -> List[optional_activity_type]:
        prefix = "delivery" if order.is_delivery else "pickup"
        activities = []

        exchange_points = (
            [order.exchange_point]
            if order.exchange_point is not None
            else self.material_to_exchange_point[order.material]
        )
        for exchange_point in exchange_points:
            activity = self.add_optional_activity(
                model,
                f"{prefix}_{truck_id}_{order.material}_{exchange_point}",
                order.duration,
                start_lower_bound=self.exchange_point_busy_duration[exchange_point],
                params={
                    "truck_id": truck_id,
                    "exchange_point": exchange_point,
                    "order": order,
                },
            )
            activities.append(activity)
        model.add_exactly_one(map(lambda a: a.is_present, activities))

        return activities

    def enforce_exchange_point_constraints(
        self, model: cp_model.CpModel, activities: List[optional_activity_type]
    ):
        exchange_point_activities = {}
        for act in activities:
            exchange_point = act.params["exchange_point"]
            if exchange_point not in exchange_point_activities:
                exchange_point_activities[exchange_point] = []
            exchange_point_activities[exchange_point].append(act)

        for activities in exchange_point_activities.values():
            model.add_no_overlap(map(lambda act: act.interval, activities))

    def enforce_stock_constraints(
        self, model: cp_model.CpModel, activities: List[optional_activity_type]
    ):
        material_site_activities = {}
        for act in activities:
            material_site = (act.params["exchange_point"], act.params["order"].material)
            if material_site not in material_site_activities:
                material_site_activities[material_site] = []
            material_site_activities[material_site].append(act)

        for material_site, activities in material_site_activities.items():
            material_site = self.material_sites[material_site]
            times = [0] + list(map(lambda act: act.start + act.duration, activities))
            level_changes = [material_site.stock_level] + [
                (
                    act.params["order"].quantity
                    * (1 if act.params["order"].is_delivery else -1)
                )
                for act in activities
            ]
            actives = [True] + list(map(lambda act: act.is_present, activities))
            model.add_reservoir_constraint_with_active(
                times,
                level_changes,
                actives,
                min_level=0,
                max_level=material_site.stock_capacity,
            )

    def add_quality_metric(
        self, model: cp_model.CpModel, activities: List[optional_activity_type]
    ):
        """Sets the objective of the model to minimize."""

        # makespan_var = model.new_int_var(0, self.upper_bound, "makespan")
        # model.add_max_equality(
        #     makespan_var,
        #     [activity.start + activity.duration for activity in activities],
        # )

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

        model.minimize(
            sum(
                (truck.waiting_time + 1) * truck_makespan_vars[i]
                for i, truck in enumerate(self.instance.trucks)
            )
        )

    def get_optimization_model(
        self,
    ) -> Tuple[cp_model.CpModel, List[optional_activity_type]]:
        model = cp_model.CpModel()
        activities = []
        for truck in self.instance.trucks:
            truck_activities = self.add_delivery_pickup_activity(
                model, truck.order, truck.id
            )
            activities += truck_activities

        self.enforce_exchange_point_constraints(model, activities)
        self.enforce_stock_constraints(model, activities)
        self.add_quality_metric(model, activities)

        return model, activities

    def get_solution(
        self, time_limit: Optional[int] = None
    ) -> Optional[LogisticsSolution]:
        self.truck_schedule_solution = None
        solver = cp_model.CpSolver()
        if time_limit is not None:
            solver.parameters.max_time_in_seconds = time_limit
        # solver.parameters.log_search_progress = True

        status = solver.solve(self.model)
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:

            def construct_scheduled_orders(
                activities: Iterator[optional_activity_type],
            ) -> List[ScheduledOrder]:
                scheduled_orders = []
                for activity in activities:
                    if solver.value(activity.is_present):
                        truck_id = activity.params["truck_id"]
                        exchange_point = activity.params["exchange_point"]
                        order: DeliveryPickupOrder = activity.params["order"]
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

            delivery_orders = construct_scheduled_orders(
                filter(lambda act: act.params["order"].is_delivery, self.activities)
            )
            pickup_orders = construct_scheduled_orders(
                filter(lambda act: not act.params["order"].is_delivery, self.activities)
            )
            self.truck_schedule_solution = TruckScheduleSolution(
                delivery_orders, pickup_orders
            )

            truck_entrance_order = list(
                map(
                    lambda o: TruckExchangePoint(o.truck_id, o.exchange_point),
                    sorted(delivery_orders + pickup_orders, key=lambda o: o.start_time),
                )
            )

            return LogisticsSolution(truck_entrance_order)

        else:
            return None
