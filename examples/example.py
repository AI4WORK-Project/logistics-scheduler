from logistics import LogisticsInstance, LogisticsSchedulingFactory
from logistics.visualize import plot_solution


def main():
    instance = "instances/instance2.json"
    with open(instance, "r") as f:
        instance = f.read()
    instance: LogisticsInstance = LogisticsInstance.from_json(instance)

    factory = LogisticsSchedulingFactory(instance)
    solution = factory.get_solution()
    if solution is not None:
        print(solution)
        with open("instances/instance2_solution.json", "w") as f:
            f.write(solution.to_json())

        plot_solution(solution)


if __name__ == "__main__":
    main()
