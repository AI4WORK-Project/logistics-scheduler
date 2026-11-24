import json
import logging
import os
import pathlib

import requests

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger("client_example")

url = "http://0.0.0.0:5000/schedule"

examples_path = pathlib.Path(__file__).parent.resolve()
instance_path = os.path.join(examples_path, "instances/instance1.json")
with open(instance_path, "r") as f:
    instance = json.load(f)

logger.info("sending request")
response = requests.post(url, params={"time_limit": 120}, json=instance)

logger.info(f"got response with status: {response.status_code}")
if response.ok:
    logger.info(f"response json: {response.json()}")
