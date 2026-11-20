# Human-Aware Task Planner – Logistics Yard Management

Repository: `logistics-scheduler`

The Logistics Yard Management variant of the AI4Work Human-Aware Task Planner computes the sequence in which the trucks waiting in the parking lot enter the logistics yard, and the exchange point where each truck delivers or picks up its material.
It is exposed as a REST service (`server.py`) on top of the `logistics` Python package, and it is distributed as a Docker image.

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

Or install the package and run the server directly (Python 3.12):

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
- **422**: the input or the query parameters are not valid: `{"message": "Validation error", "detail": ...}`.
- **500**: internal server error: `{"message": "<reason>", "detail": {}}`.

### GET `/last_schedule_gantt`

Returns an HTML chart of the last schedule computed by `/schedule`: the orders scheduled at each exchange point over time, with their material and truck.

- **200**: the HTML page, to be viewed in a browser.
- **404**: no schedule has been computed yet: `{"message": "Gantt html not found"}`.

### GET `/health`

Returns `{"status": "healthy", "version": "<version>"}` if the service is up and reachable.
The Docker image uses it as its `HEALTHCHECK`.

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
- [example.py](examples/example.py): solves an instance using the `logistics` package directly, without the server, and plots the schedule.

## Development

```sh
pip install .[test]
python -m pytest tests/test_solver.py

# the API tests need a running server
python server.py &
python -m pytest tests/test_api.py
```

The CI runs the tests on every pull request. Every push to `main` publishes the Docker image `ghcr.io/ai4work-project/logistics-scheduler:latest`, and every tag `vX.Y.Z` publishes `ghcr.io/ai4work-project/logistics-scheduler:X.Y.Z`.

## License

Copyright (c) 2025-2026 Fondazione Bruno Kessler and other contributors.

This software is distributed under the [Eclipse Public License 2.0](LICENSE) (`EPL-2.0`). See [NOTICE](NOTICE).

## Acknowledgements

This software has been developed within the AI4Work project, which has received funding from the European Union's Horizon Europe research and innovation programme under grant agreement No 101135990.
