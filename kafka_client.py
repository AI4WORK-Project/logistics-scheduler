"""Start the scheduler with its Kafka consumer, which requires
KAFKA_BOOTSTRAP_SERVER.

Kept for the deployments that run `python kafka_client.py`, such as
Pilot-Logistics: it is the same as `python server.py` with
KAFKA_BOOTSTRAP_SERVER set, so the HTTP API and /health are served too.
"""

import server

if __name__ == "__main__":
    server.start(kafka_required=True)
