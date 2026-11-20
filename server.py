import logging
from importlib.metadata import PackageNotFoundError, version

import marshmallow
from apiflask import APIFlask, HTTPError, Schema
from apiflask.fields import String
from marshmallow_dataclass import class_schema
from pydantic import BaseModel, Field

from logistics.factory import LogisticsSchedulingFactory
from logistics.instance import LogisticsInstance
from logistics.solution import LogisticsSolution

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


class QueryParamsSchema(BaseModel):
    time_limit: int = Field(gt=0)


# generate the schema classes
LogisticsInstanceSchema: marshmallow.schema.SchemaMeta = class_schema(
    LogisticsInstance, base_schema=Schema
)
LogisticsSolutionSchema: marshmallow.schema.SchemaMeta = class_schema(
    LogisticsSolution, base_schema=Schema
)


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
    return solution.to_dict(), 200


def start():
    logger.info("Starting...")
    from waitress import serve

    serve(app, host="0.0.0.0", port=5000)


if __name__ == "__main__":
    start()
