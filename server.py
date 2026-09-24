import logging

from apiflask import APIFlask, HTTPError, Schema
from marshmallow_dataclass import class_schema
from pydantic import BaseModel, Field

from logistics.factory import LogisticsSchedulingFactory
from logistics.instance import LogisticsInstance
from logistics.solution import LogisticsSolution

logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
)
logger = logging.getLogger("logistics-scheduler-server")

app = APIFlask(
    "Logistics-Scheduler-API", title="Logistics Scheduler API", version="1.0"
)
app.openapi_version = "3.0.2"


class QueryParamsSchema(BaseModel):
    time_limit: int = Field(gt=0)


# generate the schema classes
LogisticsInstanceSchema = class_schema(LogisticsInstance, base_schema=Schema)
LogisticsSolutionSchema = class_schema(LogisticsSolution, base_schema=Schema)


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


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5000)
