import collections

import matplotlib.pyplot as plt
from matplotlib import cm

from logistics.solution import TruckScheduleSolution


def plot_solution(solution: TruckScheduleSolution):
    _fig, ax = plt.subplots()
    ax.set_xlabel("Time")
    ax.set_ylabel("Exchange Point")
    ax.grid(True)
    ax.set_axisbelow(True)

    exchange_point_orders = collections.defaultdict(
        lambda: {"delivery": [], "pickup": []}
    )
    for delivery_order in solution.delivery_orders:
        exchange_point_orders[delivery_order.exchange_point]["delivery"].append(
            delivery_order
        )
    for pickup_order in solution.pickup_orders:
        exchange_point_orders[pickup_order.exchange_point]["pickup"].append(
            pickup_order
        )

    exchange_point_ids = sorted(exchange_point_orders.keys())
    ax.set_yticks(
        [2 + 6 * i for i in range(len(exchange_point_ids))], exchange_point_ids
    )

    cmap = cm.get_cmap("tab10")
    truck_color = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        if order.truck_id not in truck_color:
            truck_color[order.truck_id] = cmap(len(truck_color))

    cmap = cm.get_cmap("Pastel1")
    material_color = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        m = order.material
        if m not in material_color:
            material_color[m] = cmap(len(material_color))

    y = 0
    dy = 2
    for ep in exchange_point_ids:
        orders = exchange_point_orders[ep]
        orders["delivery"].sort(key=lambda o: o.start_time)
        orders["pickup"].sort(key=lambda o: o.start_time)

        for order_kind in ["delivery", "pickup"]:
            for order in orders[order_kind]:
                ax.broken_barh(
                    [(order.start_time, order.duration)],
                    (y, 1),
                    facecolors=(material_color[order.material]),
                )
                ax.text(
                    x=order.start_time + order.duration / 2,
                    y=y + 0.5,
                    s=f"material={order.material}",
                    ha="center",
                    va="center",
                    color="black",
                )
                ax.broken_barh(
                    [(order.start_time, order.duration)],
                    (y + 1, 1),
                    facecolors=(truck_color[order.truck_id]),
                )
                ax.text(
                    x=order.start_time + order.duration / 2,
                    y=y + 1.5,
                    s=f"truck={order.truck_id}",
                    ha="center",
                    va="center",
                    color="black",
                )
            y += dy
        y += dy

    plt.show()
