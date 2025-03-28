import random
from logistics.instance import *
from logistics import LogisticsInstance, LogisticsSchedulingFactory
from logistics.visualize import plot_solution


def create_instance(
    num_exchange_points, num_materials, num_trucks, num_orders_per_truck
):
    random.seed(0)

    exchange_points = [f"P{i}" for i in range(num_exchange_points)]
    warehouse = []
    for i in range(num_materials):
        warehouse.append(
            Material(
                f"M{i}",
                random.randint(40, 60),
                200,
                random.sample(exchange_points, num_exchange_points // 2),
            )
        )

    trucks = []
    for i in range(num_trucks):
        truck_orders = {}
        for order_kind in ["delivery", "pickup"]:
            sampled_materials = random.sample(warehouse, num_orders_per_truck // 2)
            truck_orders[order_kind] = [
                DeliveryPickupOrder(
                    m.material, random.randint(1, 20), random.randint(10, 100)
                )
                for m in sampled_materials
            ]
        trucks.append(
            Truck(
                f"T{i}",
                random.randint(0, 100),
                truck_orders["delivery"],
                truck_orders["pickup"],
            )
        )

    instance = LogisticsInstance(warehouse, trucks)
    return instance


def main():
    num_exchange_points = 6
    num_materials = 8
    num_trucks = 6
    num_orders_per_truck = 5

    instance = create_instance(
        num_exchange_points, num_materials, num_trucks, num_orders_per_truck
    )

    with open("instance2.json", "w") as f:
        f.write(instance.to_json())

    factory = LogisticsSchedulingFactory(instance)
    solution = factory.get_solution()
    if solution is not None:
        with open("instance2_solution.json", "w") as f:
            f.write(solution.to_json())

        plot_solution(solution)


if __name__ == "__main__":
    main()
