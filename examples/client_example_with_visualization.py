import json
import requests
from logistics import LogisticsSolution
from logistics.visualize import plot_solution


def main():
    url = "http://0.0.0.0:5000/schedule"
    instance_path = "instances/instance2.json"

    with open(instance_path, "r") as f:
        instance = json.load(f)
    response = requests.post(url, params={"time_limit": 60}, json=instance)

    print("Status Code:", response.status_code)
    if response.ok:
        print("Response JSON:", response.json())

        solution = LogisticsSolution.from_dict(response.json())
        plot_solution(solution)


if __name__ == "__main__":
    main()
