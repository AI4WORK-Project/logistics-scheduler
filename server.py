import json
import logging
import threading
from importlib.metadata import PackageNotFoundError, version

import marshmallow
from apiflask import APIFlask, HTTPError, Schema
from apiflask.fields import String
from flask import Response
from flask_cors import CORS
from marshmallow_dataclass import class_schema
from pydantic import BaseModel, Field
from werkzeug.exceptions import BadRequest

from logistics.factory import LogisticsSchedulingFactory
from logistics.instance import LogisticsInstance
from logistics.solution import LogisticsSolution, TruckScheduleSolution
from logistics.visualize import solution_html

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
)
logger = logging.getLogger("logistics-scheduler-server")

try:
    __version__ = version("logistics")
except PackageNotFoundError:
    __version__ = "unknown"

app = APIFlask(
    "Logistics-Scheduler-API",
    title="Human-Aware Task Planner – Logistics Yard Management",
    version=__version__,
)
app.openapi_version = "3.0.2"
CORS(app)


class QueryParamsSchema(BaseModel):
    time_limit: int = Field(gt=0)


# generate the schema classes
LogisticsInstanceSchema: marshmallow.schema.SchemaMeta = class_schema(
    LogisticsInstance, base_schema=Schema
)
LogisticsSolutionSchema: marshmallow.schema.SchemaMeta = class_schema(
    LogisticsSolution, base_schema=Schema
)


class LastScheduleGantt:
    """HTML visualization of the last computed schedule, kept in memory."""

    def __init__(self):
        self._lock = threading.Lock()
        self._html = None

    def update(self, truck_schedule_solution: TruckScheduleSolution):
        try:
            html = solution_html(truck_schedule_solution)
        except Exception:
            logger.warning("Could not visualize the schedule", exc_info=True)
            html = None
        with self._lock:
            self._html = html

    def get(self):
        with self._lock:
            return self._html


last_schedule_gantt_html = LastScheduleGantt()


class HealthSchema(Schema):
    status = String(metadata={"example": "healthy"})
    version = String(metadata={"example": __version__})


@app.get("/health")
@app.output(HealthSchema)
@app.doc(summary="Check if the service is alive and reachable")
def health_check():
    logger.debug("Health check pinged.")
    return {"status": "healthy", "version": __version__}


@app.errorhandler(AssertionError)
def validation_error(error):
    message = str(error)
    logger.error(f"Validation: {message}")
    return {
        "message": "Validation error",
        "detail": message,
    }, 422


@app.errorhandler(BadRequest)
def bad_request(error: BadRequest):
    # the request parser attaches the decoding error to the 400 it raises for a
    # body that is not valid JSON: report it as invalid input, as documented
    decoding_error = getattr(error, "exc", None)
    if isinstance(decoding_error, (json.JSONDecodeError, UnicodeDecodeError)):
        message = f"Invalid JSON: {decoding_error}"
        logger.error(f"Validation: {message}")
        return {"message": "Validation error", "detail": {"json": [message]}}, 422
    return app.error_callback(HTTPError(400, message=error.name))


@app.post("/schedule")
@app.input(QueryParamsSchema, location="query")
@app.input(LogisticsInstanceSchema, location="json")
@app.output(LogisticsSolutionSchema, status_code=200)
@app.doc(
    summary="Schedule logistics tasks",
    responses={
        400: "No solution found",
        422: "Invalid input",
        500: "Internal server error",
    },
)
def schedule(query_data, json_data):
    try:
        time_limit = query_data.time_limit
        logger.info(f"Time limit: {time_limit}")

        instance: LogisticsInstance = LogisticsInstance.from_dict(json_data)
        logger.info("LogisticsInstance created")

        factory = LogisticsSchedulingFactory(instance)
        logger.info("LogisticsSchedulingFactory created")

        solution: LogisticsSolution | None = factory.get_solution(time_limit=time_limit)

    except Exception as e:  # noqa: BLE001
        message = str(e)
        logger.error(message)
        raise HTTPError(status_code=500, message=message)

    if solution is None:
        message = "No solution has been found for the given problem"
        logger.error(message)
        raise HTTPError(status_code=400, message=message)

    logger.info("Solution found")
    last_schedule_gantt_html.update(factory.truck_schedule_solution)
    return solution.to_dict(), 200


@app.get("/last_schedule_gantt")
@app.doc(
    summary="Visualize the last computed schedule",
    description="HTML chart of the orders scheduled at each exchange point over "
    "time, with their material and truck, in the last schedule computed by "
    "/schedule.",
    responses={
        200: {"description": "HTML visualization", "content": {"text/html": {}}},
        404: "No schedule has been computed yet",
    },
)
def last_schedule_gantt():
    logger.info("Received request for the last generated schedule plot html.")
    html = last_schedule_gantt_html.get()
    if html is None:
        return {"message": "Gantt html not found"}, 404
    return Response(html, mimetype="text/html")


def start():
    logger.info("Starting...")
    from waitress import serve

    serve(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    start()
