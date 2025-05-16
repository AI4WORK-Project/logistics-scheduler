from logistics import LogisticsInstance, LogisticsSolution, LogisticsSchedulingFactory
from logistics.solution import ScheduledOrder
import pathlib
import os
from typing import Tuple, List, Dict
import pytest


def solve_instance(
    instance: int,
) -> Tuple[LogisticsInstance, LogisticsSolution]:
    instances_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "instances")
    instance_path = os.path.join(instances_path, f"instance{instance}.json")

    with open(instance_path, "r") as f:
        instance = f.read()
    instance: LogisticsInstance = LogisticsInstance.from_json(instance)

    factory = LogisticsSchedulingFactory(instance)
    solution: LogisticsSolution = factory.get_solution()
    assert solution is not None
    return instance, solution


def truck_delivery_pickup_orders(
    solution: LogisticsSolution,
) -> Tuple[
    Dict[str, List[ScheduledOrder]],
    Dict[str, List[ScheduledOrder]],
    Dict[str, List[ScheduledOrder]],
]:

    def group_orders_by_truck(orders: List[ScheduledOrder]):
        truck_orders: Dict[str, List[ScheduledOrder]] = {}
        for order in orders:
            if order.truck_id not in truck_orders:
                truck_orders[order.truck_id] = []

            truck_orders[order.truck_id].append(order)
        return truck_orders

    truck_delivery_orders = group_orders_by_truck(solution.delivery_orders)
    truck_pickup_orders = group_orders_by_truck(solution.pickup_orders)

    truck_orders = {}
    for truck_id in truck_delivery_orders:
        truck_orders[truck_id] = truck_delivery_orders[truck_id].copy()

    for truck_id in truck_pickup_orders:
        if truck_id not in truck_orders:
            truck_orders[truck_id] = truck_pickup_orders[truck_id]
        else:
            truck_orders[truck_id] += truck_pickup_orders[truck_id]

    return truck_orders, truck_delivery_orders, truck_pickup_orders


def are_overlapped(activities: List[Tuple[int, int]]):
    activities.sort(key=lambda x: x[0])
    for i in range(len(activities) - 1):
        if activities[i][1] > activities[i + 1][0]:
            return True
    return False


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


def assert_delivery_before_pickup(
    truck_delivery_orders: Dict[str, List[ScheduledOrder]],
    truck_pickup_orders: Dict[str, List[ScheduledOrder]],
):
    for truck_id in truck_pickup_orders:
        if truck_id not in truck_delivery_orders:
            continue

        assert min(o.start_time for o in truck_pickup_orders[truck_id]) >= max(
            o.start_time + o.duration for o in truck_delivery_orders[truck_id]
        )


def assert_truck_orders_not_overlapped(truck_orders: Dict[str, List[ScheduledOrder]]):
    for orders in truck_orders.values():
        assert not are_overlapped(
            [(o.start_time, o.start_time + o.duration) for o in orders]
        )


@pytest.mark.parametrize(
    "instance, objective_value",
    [
        (0, 115),
        (1, 1497),
    ],
)
def test_instance(instance: int, objective_value: int):
    instance, solution = solve_instance(instance)
    truck_orders, truck_delivery_orders, truck_pickup_orders = (
        truck_delivery_pickup_orders(solution)
    )

    assert_equals_objective_value(solution, objective_value)
    assert_delivery_before_pickup(truck_delivery_orders, truck_pickup_orders)
    assert_truck_orders_not_overlapped(truck_orders)
