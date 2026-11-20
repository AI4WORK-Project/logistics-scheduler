import json
import logging
import os
import pathlib
import tempfile
import webbrowser

import requests

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger("client_example_with_visualization")

server_url = "http://0.0.0.0:5000"

examples_path = pathlib.Path(__file__).parent.resolve()
instance_path = os.path.join(examples_path, "instances/instance1.json")
with open(instance_path, "r") as f:
    instance = json.load(f)

logger.info("sending request")
response = requests.post(
    f"{server_url}/schedule", params={"time_limit": 120}, json=instance
)
logger.info(f"got response with status: {response.status_code}")

if response.ok:
    logger.info(f"response json: {response.json()}")

    # the response contains only the truck entrance order: the server keeps
    # the chart of the whole schedule, with the orders at each exchange point
    gantt = requests.get(f"{server_url}/last_schedule_gantt")
    gantt.raise_for_status()
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(gantt.text)
    logger.info(f"opening the schedule visualization {f.name}")
    webbrowser.open(pathlib.Path(f.name).as_uri())
