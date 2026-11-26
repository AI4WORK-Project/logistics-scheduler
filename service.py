"""Scheduling shared by the HTTP API and the Kafka consumer, so that both
validate the requests and report the errors in the same way."""

import logging
from dataclasses import dataclass
from typing import Any

import marshmallow
from apiflask import Schema
from marshmallow_dataclass import class_schema

from logistics.factory import LogisticsSchedulingFactory
from logistics.instance import LogisticsInstance
from logistics.solution import LogisticsSolution, TruckScheduleSolution

logger = logging.getLogger("logistics-scheduler-service")

# generate the schema classes
LogisticsInstanceSchema: marshmallow.schema.SchemaMeta = class_schema(
    LogisticsInstance, base_schema=Schema
)
LogisticsSolutionSchema: marshmallow.schema.SchemaMeta = class_schema(
    LogisticsSolution, base_schema=Schema
)

NO_SOLUTION_MESSAGE = "No solution has been found for the given problem"


class InvalidInput(Exception):
    """The request is not valid: detail is reported in the 422 response."""

    def __init__(self, detail: Any):
        super().__init__(str(detail))
        self.detail = detail


@dataclass
class ScheduleResult:
    """Outcome of a request: the status code and the JSON body of the response,
    and the truck schedule to visualize if a solution has been found."""

    status: int
    body: dict[str, Any]
    truck_schedule_solution: TruckScheduleSolution | None = None


def validation_error(detail: Any) -> ScheduleResult:
    logger.error(f"Validation: {detail}")
    return ScheduleResult(422, {"message": "Validation error", "detail": detail})


def internal_error(error: Exception) -> ScheduleResult:
    return ScheduleResult(500, {"message": str(error), "detail": {}})


def load_instance(data: Any) -> LogisticsInstance:
    """Validate the JSON data of an instance as the body of /schedule.

    Raise InvalidInput with the same detail as the HTTP API."""
    try:
        return LogisticsInstanceSchema().load(data)
    except marshmallow.ValidationError as e:
        raise InvalidInput({"json": e.messages}) from e
    except AssertionError as e:
        raise InvalidInput(str(e)) from e


def solve(instance: LogisticsInstance, time_limit: int | None) -> ScheduleResult:
    """Compute the schedule of a valid instance."""
    try:
        factory = LogisticsSchedulingFactory(instance)
        logger.info("LogisticsSchedulingFactory created")

        solution: LogisticsSolution | None = factory.get_solution(time_limit=time_limit)

    except Exception as e:  # noqa: BLE001
        logger.exception("Error while computing the schedule")
        return internal_error(e)

    if solution is None:
        logger.error(NO_SOLUTION_MESSAGE)
        return ScheduleResult(400, {"message": NO_SOLUTION_MESSAGE, "detail": {}})

    logger.info("Solution found")
    return ScheduleResult(200, solution.to_dict(), factory.truck_schedule_solution)
