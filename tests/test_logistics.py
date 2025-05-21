from logistics import LogisticsInstance, LogisticsSolution, LogisticsSchedulingFactory
from logistics.solution import ScheduledOrder
import pathlib
import os
from typing import Tuple, List, Dict, Optional
from collections import defaultdict
from collections.abc import Callable
import pytest


def solve_instance(
    instance: int, time_limit: Optional[int] = None
) -> Tuple[LogisticsInstance, LogisticsSolution]:
    instances_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "instances")
    instance_path = os.path.join(instances_path, f"instance{instance}.json")

    with open(instance_path, "r") as f:
        instance = f.read()
    instance: LogisticsInstance = LogisticsInstance.from_json(instance)

    factory = LogisticsSchedulingFactory(instance)
    solution: LogisticsSolution = factory.get_solution(time_limit)
    assert solution is not None
    return instance, solution


def group_orders_by_truck(
    orders: List[ScheduledOrder],
) -> Dict[str, List[ScheduledOrder]]:
    return group_orders(orders, get_group_id=lambda order: order.truck_id)


def group_orders_by_exchange_point(
    orders: List[ScheduledOrder],
) -> Dict[str, List[ScheduledOrder]]:
    return group_orders(orders, get_group_id=lambda order: order.exchange_point)


def group_orders(
    orders: List[ScheduledOrder], get_group_id: Callable[[ScheduledOrder], str]
) -> Dict[str, List[ScheduledOrder]]:
    grouped_orders: Dict[str, List[ScheduledOrder]] = {}
    for order in orders:
        group_id = get_group_id(order)
        if group_id not in grouped_orders:
            grouped_orders[group_id] = []

        grouped_orders[group_id].append(order)
    return grouped_orders


def assert_material_present_in_exchange_point(
    instance: LogisticsInstance, solution: LogisticsSolution
):
    exchange_points_materials = defaultdict(list)
    for material in instance.warehouse:
        for exchange_point in material.exchange_points:
            exchange_points_materials[exchange_point].append(material.material)

    for order in solution.delivery_orders + solution.pickup_orders:
        assert order.material in exchange_points_materials[order.exchange_point]


def assert_equals_objective_value(solution: LogisticsSolution, value: int):
    truck_makespan: Dict[str, int] = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        if order.truck_id not in truck_makespan:
            truck_makespan[order.truck_id] = 0
        truck_makespan[order.truck_id] = max(
            truck_makespan[order.truck_id], order.start_time + order.duration
        )

    makespan_sum = sum(truck_makespan.values())
    assert makespan_sum == value


def assert_delivery_before_pickup(solution: LogisticsSolution):
    truck_delivery_orders = group_orders_by_truck(solution.delivery_orders)
    truck_pickup_orders = group_orders_by_truck(solution.pickup_orders)

    for truck_id in truck_pickup_orders:
        if truck_id not in truck_delivery_orders:
            continue

        assert min(o.start_time for o in truck_pickup_orders[truck_id]) >= max(
            o.start_time + o.duration for o in truck_delivery_orders[truck_id]
        )


def assert_truck_orders_not_overlapped(solution: LogisticsSolution):
    truck_orders = group_orders_by_truck(
        solution.delivery_orders + solution.pickup_orders
    )
    assert_orders_not_overlapped(truck_orders)


def assert_exchange_point_orders_not_overlapped(solution: LogisticsSolution):
    exchange_point_orders = group_orders_by_exchange_point(
        solution.delivery_orders + solution.pickup_orders
    )
    assert_orders_not_overlapped(exchange_point_orders)


def assert_orders_not_overlapped(orders: Dict[str, List[ScheduledOrder]]):
    for sub_orders in orders.values():
        assert not are_overlapped(
            [(o.start_time, o.start_time + o.duration) for o in sub_orders]
        )


def are_overlapped(activities: List[Tuple[int, int]]):
    activities.sort(key=lambda x: x[0])
    for i in range(len(activities) - 1):
        if activities[i][1] > activities[i + 1][0]:
            return True
    return False


@pytest.mark.parametrize(
    "instance, objective_value",
    [
        (0, 115),
        (1, 1497),
    ],
)
def test_instance_and_objective(instance: int, objective_value: int):
    instance, solution = solve_instance(instance)

    assert_equals_objective_value(solution, objective_value)
    assert_material_present_in_exchange_point(instance, solution)
    assert_delivery_before_pickup(solution)
    assert_truck_orders_not_overlapped(solution)
    assert_exchange_point_orders_not_overlapped(solution)


@pytest.mark.parametrize("instance", [2, 3, 4, 5, 6, 7])
def test_instance(instance: int):
    instance, solution = solve_instance(instance, time_limit=60)

    assert_material_present_in_exchange_point(instance, solution)
    assert_delivery_before_pickup(solution)
    assert_truck_orders_not_overlapped(solution)
    assert_exchange_point_orders_not_overlapped(solution)
