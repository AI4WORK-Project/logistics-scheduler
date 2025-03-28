import matplotlib.pyplot as plt
import matplotlib.cm as cm
import collections
from logistics import LogisticsSolution


def plot_solution(solution: LogisticsSolution):
    fig, ax = plt.subplots()
    ax.set_xlabel("Time")
    ax.set_ylabel("Truck")
    ax.grid(True)
    ax.set_axisbelow(True)

    truck_orders = collections.defaultdict(lambda: {"delivery": [], "pickup": []})
    for delivery_order in solution.delivery_orders:
        truck_orders[delivery_order.truck_id]["delivery"].append(delivery_order)
    for delivery_order in solution.pickup_orders:
        truck_orders[delivery_order.truck_id]["pickup"].append(delivery_order)

    truck_ids = sorted(list(truck_orders.keys()))
    ax.set_yticks([2 + 6 * i for i in range(len(truck_ids))], truck_ids)

    cmap = cm.get_cmap("tab10")
    exchange_point_color = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        ex = order.exchange_point
        if ex not in exchange_point_color:
            exchange_point_color[ex] = cmap(len(exchange_point_color))

    cmap = cm.get_cmap("Pastel1")
    material_color = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        m = order.material
        if m not in material_color:
            material_color[m] = cmap(len(material_color))

    y = 0
    dy = 2
    for truck_id in truck_ids:
        orders = truck_orders[truck_id]
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
                    facecolors=(exchange_point_color[order.exchange_point]),
                )
                ax.text(
                    x=order.start_time + order.duration / 2,
                    y=y + 1.5,
                    s=f"exchange_point={order.exchange_point}",
                    ha="center",
                    va="center",
                    color="black",
                )
            y += dy
        y += dy

    plt.show()
