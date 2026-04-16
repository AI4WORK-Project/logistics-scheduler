from logistics import LogisticsInstance, LogisticsSchedulingFactory
from logistics.visualize import plot_solution
import pathlib
import os
import json


def main():
    examples_path = pathlib.Path(__file__).parent.resolve()
    instance_path = os.path.join(examples_path, "instances/instance1.json")
    solution_path = os.path.join(examples_path, "instances/instance1_solution.json")
    with open(instance_path, "r") as f:
        instance = f.read()
    instance: LogisticsInstance = LogisticsInstance.from_json(instance)

    factory = LogisticsSchedulingFactory(instance)
    solution = factory.get_solution()
    if solution is not None:
        print(solution)
        with open(solution_path, "w") as f:
            f.write(json.dumps(json.loads(solution.to_json()), indent=4))

        plot_solution(factory.truck_schedule_solution)
    else:
        print("No solution.")


if __name__ == "__main__":
    main()
