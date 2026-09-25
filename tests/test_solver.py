import os
import pathlib

import pytest

from logistics import LogisticsInstance, LogisticsSchedulingFactory, LogisticsSolution


def solve_instance(
    instance: int, time_limit: int | None = None
) -> tuple[LogisticsInstance, LogisticsSolution]:
    instances_path = os.path.join(pathlib.Path(__file__).parent.resolve(), "instances")
    instance_path = os.path.join(instances_path, f"instance{instance}.json")

    with open(instance_path, "r") as f:
        instance_json = f.read()
    logistics_instance: LogisticsInstance = LogisticsInstance.from_json(instance_json)

    factory = LogisticsSchedulingFactory(logistics_instance)
    solution: LogisticsSolution | None = factory.get_solution(time_limit)
    assert solution is not None
    return logistics_instance, solution


def check_stock_level_constraints(
    instance: LogisticsInstance, solution: LogisticsSolution
):
    stock_level = {}
    stock_capacity = {}
    for ep in instance.warehouse:
        for m in ep.materials:
            stock_level[(ep.exchange_point, m.material)] = [m.stock_level]
            stock_capacity[(ep.exchange_point, m.material)] = m.stock_capacity

    trucks = {t.id: t for t in instance.trucks}
    for t in solution.truck_entrance_order:
        order = trucks[t.truck_id].order
        warehouse_key = (t.exchange_point, order.material)
        assert warehouse_key in stock_level
        stock_level[warehouse_key].append(
            order.quantity * (1 if order.is_delivery else -1)
        )

    for k, increments in stock_level.items():
        stock = 0
        for inc in increments:
            stock += inc
            assert 0 <= stock <= stock_capacity[k]


def check_truck_entrance_order(
    instance: LogisticsInstance, solution: LogisticsSolution
):
    trucks = {t.id: t for t in instance.trucks}
    last_order_end = {ep.exchange_point: 0 for ep in instance.warehouse}

    for o in instance.ongoing_orders:
        last_order_end[o.exchange_point] = o.remaining_duration

    last_truck_entrance = 0
    for t in solution.truck_entrance_order:
        assert last_truck_entrance <= last_order_end[t.exchange_point]
        last_truck_entrance = last_order_end[t.exchange_point]
        last_order_end[t.exchange_point] += trucks[t.truck_id].order.duration


@pytest.mark.parametrize("instance", range(8))
def test_instance(instance: int):
    logistics_instance, solution = solve_instance(instance, time_limit=60)

    assert {t.id for t in logistics_instance.trucks} == {
        t.truck_id for t in solution.truck_entrance_order
    }

    check_stock_level_constraints(logistics_instance, solution)
    check_truck_entrance_order(logistics_instance, solution)
