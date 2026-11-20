import json
import logging
import os
import pathlib
import socket
import threading
import time

import pytest
import requests

import server

URL = "http://0.0.0.0:5000/schedule"
HEALTH_URL = "http://0.0.0.0:5000/health"
GANTT_URL = "http://0.0.0.0:5000/last_schedule_gantt"
INSTANCES_PATH = os.path.join(pathlib.Path(__file__).parent.resolve(), "instances")

logger = logging.getLogger("test_api")


@pytest.fixture(scope="module", autouse=True)
def start_server(request):
    logger.info("[Setup] starting server...")
    # do not run the tests against another server already listening on the port
    with socket.socket() as s:
        assert s.connect_ex(("127.0.0.1", 5000)) != 0, "Port 5000 is already in use"
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()

    # wait until the server answers, failing if it could not start
    deadline = time.monotonic() + 30
    while True:
        assert server_thread.is_alive(), "The server could not start"
        try:
            requests.get(HEALTH_URL, timeout=1).raise_for_status()
            break
        except requests.RequestException:
            assert time.monotonic() < deadline, "The server did not start in time"
            time.sleep(0.2)

    # yield control to the test suite
    yield

    logger.info("[Teardown] stopping server...")


def load_instance_json(instance_name: str) -> dict:
    instance_path = os.path.join(INSTANCES_PATH, instance_name)
    with open(instance_path, "r") as f:
        instance = json.load(f)
    return instance


def test_health():
    response = requests.get(HEALTH_URL)
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert len(response.json()["version"]) > 0


def test_invalid_instance():
    response = requests.post(URL, params={"time_limit": 10 * 60}, json="")
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    logger.info(f"{response.json()}")


def test_missing_query_param():
    instance = load_instance_json("instance0.json")
    response = requests.post(URL, json=instance)
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    logger.info(f"{response.json()}")


def test_invalid_query_param():
    instance = load_instance_json("instance0.json")
    response = requests.post(URL, params={"time_limit": 0}, json=instance)
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    logger.info(f"{response.json()}")


@pytest.mark.parametrize("instance", range(2))
def test_incomplete_instance(instance: int):
    instance_json = load_instance_json(f"instance_incomplete{instance}.json")
    response = requests.post(URL, params={"time_limit": 10 * 60}, json=instance_json)
    assert response.status_code == 422
    assert len(response.json()["message"]) > 0
    logger.info(f"{response.json()}")


def test_instance_not_solvable():
    instance = load_instance_json("instance_not_solvable.json")
    response = requests.post(URL, params={"time_limit": 10 * 60}, json=instance)
    assert response.status_code == 400
    assert len(response.json()["message"]) > 0
    logger.info(f"{response.json()}")


def test_valid_instance():
    instance = load_instance_json("instance0.json")
    response = requests.post(URL, params={"time_limit": 10 * 60}, json=instance)
    assert response.status_code == 200
    logger.info(f"{response.json()}")

    response = requests.get(GANTT_URL)
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    assert "<svg" in response.text
