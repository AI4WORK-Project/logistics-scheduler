import logging
from flask import Flask, request, Response
from logistics import LogisticsInstance, LogisticsSchedulingFactory

logging.basicConfig(level=logging.INFO)

app = Flask("Logistics-Scheduler-API")


@app.route("/schedule", methods=["POST"])
def schedule():
    try:
        logging.info("Request received!")

        instance: LogisticsInstance = LogisticsInstance.from_dict(request.json)

        factory = LogisticsSchedulingFactory(instance)

        time_limit = request.args.get("time_limit", None, type=int)
        logging.info(f"Time limit: {time_limit}")

        solution = factory.get_solution(time_limit=time_limit)
        if solution is not None:
            logging.info(f"Solution found")
        else:
            logging.info("No solution has been found for the given problem")
            return Response(
                '{"message":"No solution has been found for the given problem"}',
                mimetype="application/json",
                status=400,
            )

    except Exception as e:
        return Response(
            '{"message":"%s"}' % str(e), mimetype="application/json", status=500
        )

    return Response(solution.to_json(), mimetype="application/json", status=200)


if __name__ == "__main__":
    from waitress import serve

    serve(app, host="0.0.0.0", port=5000)
