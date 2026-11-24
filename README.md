# Human-Aware Task Planner – Logistics Yard Management

Repository: `logistics-scheduler`

The Logistics Yard Management variant of the AI4Work Human-Aware Task Planner computes the sequence in which the trucks waiting in the parking lot enter the logistics yard, and the exchange point where each truck delivers or picks up its material.
It is exposed as a REST service (`server.py`), and optionally as a [Kafka](#kafka) consumer, on top of the `logistics` Python package, and it is distributed as a Docker image.

The schedule satisfies hard constraints and optimizes the waiting times of the drivers:

- **Hard constraints**: each exchange point serves one truck at a time, after the orders currently in progress; each truck is served at an exchange point that stores its material (or at the one it requires); the stock of each material at each exchange point stays between zero and its capacity.
- **Human-aware objective**: the completion time of each truck is minimized, weighted by the time the truck has already been waiting, so that trucks waiting longer are prioritized. This reduces waiting and idle times, improves the yard throughput and ensures fairness among drivers.

The optimization model is solved with the OR-Tools CP-SAT solver.

## Quick start

Run the published Docker image:

```sh
docker run -p 5000:5000 ghcr.io/ai4work-project/logistics-scheduler:latest
```

Or build the image from source:

```sh
docker build -t logistics-scheduler .
docker run -p 5000:5000 logistics-scheduler
```

Or install the package and run the server directly (Python 3.10 or later; the image and CI use 3.12):

```sh
pip install .
python server.py
```

The service listens on port 5000. The interactive API documentation is available at <http://localhost:5000/docs>.

## API

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/schedule` | Computes the truck entrance sequence for the given yard state |
| `GET` | `/last_schedule_gantt` | HTML visualization of the last computed schedule |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Interactive API documentation (Swagger UI) |
| `GET` | `/openapi.json` | OpenAPI specification |

### POST `/schedule`

Computes the truck entrance sequence for the yard state described by the JSON request body.

#### Query parameters

- `time_limit` (**required**, int > 0): time limit in seconds for the solver.

#### Request body

A JSON object describing the yard state: the exchange points with their materials and stock levels (`warehouse`), the trucks waiting in the parking lot with their delivery or pickup order (`trucks`), and the orders in progress at the exchange points (`ongoing_orders`).
See:

- [instance1_description.md](examples/instances/instance1_description.md): description of the input and output fields;
- [instance1.json](examples/instances/instance1.json) and [instance1_annotated.json](examples/instances/instance1_annotated.json): example request;
- [schema.json](examples/instances/schema.json): JSON schema of the request.

The request is validated against the OpenAPI schema: unknown fields are rejected.

#### Responses

- **200**: the sequence in which the trucks enter the yard, each with its assigned exchange point (`truck_entrance_order`). See [instance1_solution.json](examples/instances/instance1_solution.json) and [instance1_solution_annotated.json](examples/instances/instance1_solution_annotated.json).
- **400**: no solution has been found: `{"message": "No solution has been found for the given problem", "detail": {}}`.
- **422**: the input or the query parameters are not valid, including a body that is not valid JSON: `{"message": "Validation error", "detail": ...}`.
- **500**: internal server error: `{"message": "<reason>", "detail": {}}`.

### GET `/last_schedule_gantt`

Returns an HTML chart of the last schedule computed by `/schedule` or for a Kafka request: the orders scheduled at each exchange point over time, with their material and truck.

- **200**: the HTML page, to be viewed in a browser.
- **404**: no schedule has been computed yet: `{"message": "Gantt html not found"}`.
- **500**: the last schedule could not be visualized: `{"message": "The last schedule could not be visualized"}`.

The page is rendered when it is first requested, so computing a schedule does not wait for its visualization.

### GET `/health`

Returns `{"status": "healthy", "version": "<version>"}` if the service is up and reachable.
When the Kafka consumer is enabled, the response also contains `"kafka": "running"`, and the status is 503 with `{"status": "unhealthy", "kafka": "stopped", ...}` if the consumer has stopped.
The Docker image uses it as its `HEALTHCHECK`.

## Kafka

The scheduler can also receive the instances from a Kafka topic and send each schedule to a reply topic.
The Kafka consumer runs next to the HTTP API, which stays available, when `KAFKA_BOOTSTRAP_SERVER` is set:

| Variable | Description |
|---|---|
| `KAFKA_BOOTSTRAP_SERVER` | Kafka broker, e.g. `kafka:9092`: enables the consumer |
| `KAFKA_TOPIC_LOGISTICS_INSTANCE` | Topic of the requests (required with `KAFKA_BOOTSTRAP_SERVER`) |
| `KAFKA_USERNAME`, `KAFKA_PASSWORD` | Credentials for SASL PLAIN authentication, if both are set |
| `KAFKA_TIME_LIMIT` | Time limit in seconds for the requests without a `TimeLimit` header (default 120, at most 3600) |

```sh
docker run -p 5000:5000 \
  -e KAFKA_BOOTSTRAP_SERVER=kafka:9092 \
  -e KAFKA_TOPIC_LOGISTICS_INSTANCE=logistics-instance \
  ghcr.io/ai4work-project/logistics-scheduler:latest
```

Each request is a message with the same JSON body as `/schedule` and these headers:

- `CorrelationId` (required): copied to the reply, to match it with its request;
- `ReplyTopic` (required): topic where the reply is sent;
- `TimeLimit` (optional): time limit in seconds for the solver, between 1 and 3600; `KAFKA_TIME_LIMIT` if missing.

A message without `CorrelationId` or `ReplyTopic` cannot be answered: it is logged and skipped.
Every other request gets a reply on its `ReplyTopic`, with the `CorrelationId` of the request and a `Status` header with the status code `/schedule` would return:

- **200**: the body is the schedule, as returned by `/schedule`;
- **400**, **422**, **500**: the body is the error, as returned by `/schedule`: `{"message": "...", "detail": ...}`. An invalid `TimeLimit` header gives 422 with the detail `{"headers": {"TimeLimit": [...]}}`.

The requests are processed one at a time, by the consumer group `logistics-scheduler`, and each request is committed once its reply has been sent: a request in progress when the scheduler stops is processed again when it restarts.
The consumer creates the request topic if the broker allows it, and logs `Waiting...` when it is idle, after starting or after a request.

`python kafka_client.py` starts the server with the consumer and fails if `KAFKA_BOOTSTRAP_SERVER` is not set.
It is kept, together with the image name `ghcr.io/ai4work-project/logistics-scheduler-kafka`, for the deployments of [Pilot-Logistics](https://github.com/AI4WORK-Project/Pilot-Logistics), which wait for the broker with `nc` (installed in the image) and then run it.

## Examples

With the server running:

```sh
# compute a schedule
curl -X POST --json @examples/instances/instance1.json "http://localhost:5000/schedule?time_limit=60"

# save the visualization of the last schedule and open it in a browser
curl "http://localhost:5000/last_schedule_gantt" > schedule.html
```

The [examples](examples) folder also contains:

- [client_example.py](examples/client_example.py): sends a request to the server and prints the response;
- [client_example_with_visualization.py](examples/client_example_with_visualization.py): sends a request and opens the visualization of the schedule;
- [example.py](examples/example.py): solves an instance using the `logistics` package directly, without the server, and plots the schedule.

The client examples need `requests`: `pip install .[example]`.

## Development

```sh
pip install .[test]
python -m pytest tests
```

The API tests start the server on port 5000 themselves, so the port must be free.
The Kafka tests start a Kafka broker with [Testcontainers](https://testcontainers.com/), so they need Docker.

The CI runs the tests on every pull request. Every push to `main` publishes the Docker image `ghcr.io/ai4work-project/logistics-scheduler:latest`, and every tag `vX.Y.Z` publishes `ghcr.io/ai4work-project/logistics-scheduler:X.Y.Z`. The same image is also published as `ghcr.io/ai4work-project/logistics-scheduler-kafka`.

## License

Copyright (c) 2025-2026 Fondazione Bruno Kessler and other contributors.

This software is distributed under the [Eclipse Public License 2.0](LICENSE) (`EPL-2.0`). See [NOTICE](NOTICE).

## Acknowledgements

This software has been developed within the AI4Work project, which has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement No 101135990.
