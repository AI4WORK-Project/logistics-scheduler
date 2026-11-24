import json
import logging
import signal
import sys
import threading
from importlib.metadata import PackageNotFoundError, version

from apiflask import APIFlask, HTTPError, Schema
from apiflask.fields import String
from flask import Response
from flask_cors import CORS
from pydantic import BaseModel, Field
from werkzeug.exceptions import BadRequest

import kafka_worker
import service
from logistics.instance import LogisticsInstance
from logistics.solution import TruckScheduleSolution
from logistics.visualize import solution_html
from service import LogisticsInstanceSchema, LogisticsSolutionSchema

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


class LastScheduleGantt:
    """Last computed schedule, kept in memory and rendered as an HTML page
    only when it is requested."""

    def __init__(self, render):
        self._render = render
        self._lock = threading.Lock()
        self._schedule = None
        self._html = None

    def update(self, *schedule):
        with self._lock:
            self._schedule = schedule
            self._html = None

    def html(self) -> str | None:
        """Return the HTML page, None if no schedule has been computed yet.

        Raise the rendering error if the page cannot be rendered."""
        with self._lock:
            if self._html is None and self._schedule is not None:
                self._html = self._render(*self._schedule)
            return self._html


def render_schedule(truck_schedule_solution: TruckScheduleSolution) -> str:
    return solution_html(truck_schedule_solution)


last_schedule_gantt_html = LastScheduleGantt(render_schedule)


# thread of the Kafka consumer, if it has been started
kafka_thread: threading.Thread | None = None


class HealthSchema(Schema):
    status = String(metadata={"example": "healthy"})
    version = String(metadata={"example": __version__})
    kafka = String(
        metadata={
            "example": "running",
            "description": "running or stopped, only if the Kafka consumer is enabled",
        }
    )


@app.get("/health")
@app.output(HealthSchema)
@app.doc(
    summary="Check if the service is alive and reachable",
    responses={503: "The Kafka consumer has stopped"},
)
def health_check():
    logger.debug("Health check pinged.")
    body = {"status": "healthy", "version": __version__}
    if kafka_thread is not None:
        if kafka_thread.is_alive():
            body["kafka"] = "running"
        else:
            body.update(status="unhealthy", kafka="stopped")
            return body, 503
    return body


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
def schedule(query_data, json_data: LogisticsInstance):
    time_limit = query_data.time_limit
    logger.info(f"Time limit: {time_limit}")

    # the body has already been validated against LogisticsInstanceSchema
    result = service.solve(json_data, time_limit)
    if result.status != 200:
        raise HTTPError(status_code=result.status, message=result.body["message"])

    last_schedule_gantt_html.update(result.truck_schedule_solution)
    return result.body, 200


@app.get("/last_schedule_gantt")
@app.doc(
    summary="Visualize the last computed schedule",
    description="HTML chart of the orders scheduled at each exchange point over "
    "time, with their material and truck, in the last schedule computed by "
    "/schedule.",
    responses={
        200: {"description": "HTML visualization", "content": {"text/html": {}}},
        404: "No schedule has been computed yet",
        500: "The last schedule could not be visualized",
    },
)
def last_schedule_gantt():
    logger.info("Received request for the last generated schedule plot html.")
    try:
        html = last_schedule_gantt_html.html()
    except Exception:
        logger.exception("Could not visualize the last schedule")
        return {"message": "The last schedule could not be visualized"}, 500
    if html is None:
        return {"message": "Gantt html not found"}, 404
    return Response(html, mimetype="text/html")


def start_kafka_worker(config: kafka_worker.KafkaConfig) -> kafka_worker.KafkaWorker:
    """Start the Kafka consumer in a thread: the schedules it computes are
    shown by /last_schedule_gantt too."""
    global kafka_thread
    worker = kafka_worker.KafkaWorker(config, on_schedule=last_schedule_gantt_html.update)

    def run():
        try:
            worker.run()
        except Exception:
            logger.exception("The Kafka consumer has stopped")

    kafka_thread = threading.Thread(target=run, name="kafka-worker", daemon=True)
    kafka_thread.start()
    return worker


def start(kafka_required: bool = False):
    """Start the server, and the Kafka consumer if KAFKA_BOOTSTRAP_SERVER is set.

    Raise ValueError if the Kafka configuration is not valid, or if it is
    missing and kafka_required is set."""
    logger.info("Starting...")
    from waitress import serve

    config = kafka_worker.KafkaConfig.from_env()
    if config is None and kafka_required:
        raise ValueError("KAFKA_BOOTSTRAP_SERVER is required.")
    worker = start_kafka_worker(config) if config is not None else None

    if threading.current_thread() is threading.main_thread():
        # stop as on Ctrl+C, so that the Kafka consumer leaves its group
        signal.signal(signal.SIGTERM, lambda signum, frame: sys.exit(0))
    try:
        serve(app, host="0.0.0.0", port=5000)
    finally:
        if worker is not None and kafka_thread is not None:
            logger.info("Stopping the Kafka consumer...")
            worker.stop()
            kafka_thread.join(10)


if __name__ == "__main__":
    start()
