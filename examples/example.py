from logistics import LogisticsInstance, LogisticsSchedulingFactory
from logistics.visualize import plot_solution
import pathlib
import os


def main():
    examples_path = pathlib.Path(__file__).parent.resolve()
    instance_path = os.path.join(examples_path, "instances/instance2.json")
    solution_path = os.path.join(examples_path, "instances/instance2_solution.json")
    with open(instance_path, "r") as f:
        instance = f.read()
    instance: LogisticsInstance = LogisticsInstance.from_json(instance)

    factory = LogisticsSchedulingFactory(instance)
    solution = factory.get_solution()
    if solution is not None:
        print(solution)
        with open(solution_path, "w") as f:
            f.write(solution.to_json())

        plot_solution(solution)


if __name__ == "__main__":
    main()
