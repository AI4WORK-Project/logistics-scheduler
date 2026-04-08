import json
import logging
import requests
import pathlib
import os

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)

url = "http://0.0.0.0:5000/schedule"

examples_path = pathlib.Path(__file__).parent.resolve()
instance_path = os.path.join(examples_path, "instances/instance1.json")
with open(instance_path, "r") as f:
    instance = json.load(f)

logging.info("sending request")
response = requests.post(url, params={"time_limit": 120}, json=instance)

logging.info(f"got response with status: {response.status_code}")
if response.ok:
    logging.info(f"response json: {response.json()}")
