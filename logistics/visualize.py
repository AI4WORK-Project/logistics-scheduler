import collections
import io

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.figure import Figure

from logistics.solution import TruckScheduleSolution


def draw_solution(ax: Axes, solution: TruckScheduleSolution):
    """Draws the orders at each exchange point over time: for each order, the
    lower bar shows the material and the upper bar the truck."""
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

    cmap = plt.get_cmap("tab10")
    truck_color = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        if order.truck_id not in truck_color:
            truck_color[order.truck_id] = cmap(len(truck_color) % cmap.N)

    cmap = plt.get_cmap("Pastel1")
    material_color = {}
    for order in solution.delivery_orders + solution.pickup_orders:
        m = order.material
        if m not in material_color:
            material_color[m] = cmap(len(material_color) % cmap.N)

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


def solution_html(solution: TruckScheduleSolution) -> str:
    """The chart of draw_solution as a standalone HTML page with an SVG image.
    It does not use pyplot, so it can be called from several threads."""
    exchange_points = {
        o.exchange_point for o in solution.delivery_orders + solution.pickup_orders
    }
    fig = Figure(figsize=(12, 1.5 + 1.2 * max(len(exchange_points), 1)))
    draw_solution(fig.subplots(), solution)
    fig.tight_layout()
    svg = io.StringIO()
    fig.savefig(svg, format="svg")
    # drop the XML declaration and DOCTYPE of the SVG document
    svg_element = svg.getvalue()[svg.getvalue().index("<svg") :]
    return (
        "<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
        "<title>Logistics Yard Management schedule</title>\n</head>\n<body>\n"
        f"{svg_element}\n</body>\n</html>\n"
    )


def plot_solution(solution: TruckScheduleSolution):
    _fig, ax = plt.subplots()
    draw_solution(ax, solution)
    plt.show()
