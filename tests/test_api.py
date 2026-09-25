import json
import os
import pathlib

import pytest
import requests

URL = "http://0.0.0.0:5000/schedule"
INSTANCES_PATH = os.path.join(pathlib.Path(__file__).parent.resolve(), "instances")


def load_instance_json(instance_name: str) -> dict:
    instance_path = os.path.join(INSTANCES_PATH, instance_name)
    with open(instance_path, "r") as f:
        instance = json.load(f)
    return instance


def test_invalid_instance():
    response = requests.post(URL, params={"time_limit": 10 * 60}, json="")
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    print(f"{response.json()}")


def test_missing_query_param():
    instance = load_instance_json("instance0.json")
    response = requests.post(URL, json=instance)
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    print(f"{response.json()}")


def test_invalid_query_param():
    instance = load_instance_json("instance0.json")
    response = requests.post(URL, params={"time_limit": 0}, json=instance)
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    print(f"{response.json()}")


@pytest.mark.parametrize("instance", range(2))
def test_incomplete_instance(instance: int):
    instance_json = load_instance_json(f"instance_incomplete{instance}.json")
    response = requests.post(URL, params={"time_limit": 10 * 60}, json=instance_json)
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    print(f"{response.json()}")


def test_instance_not_solvable():
    instance = load_instance_json("instance_not_solvable.json")
    response = requests.post(URL, params={"time_limit": 10 * 60}, json=instance)
    assert response.status_code == 400
    assert len(response.json()["message"]) > 0
    print(f"{response.json()}")


def test_valid_instance():
    instance = load_instance_json("instance0.json")
    response = requests.post(URL, params={"time_limit": 10 * 60}, json=instance)
    assert response.status_code == 200
    print(f"{response.json()}")
