import json
import logging
import os
import threading
import time

import pytest
from confluent_kafka import Consumer, KafkaError, Producer
from testcontainers.community.kafka import KafkaContainer

import kafka_client
from logistics.instance import LogisticsInstance
from logistics.solution import LogisticsSolution
from tests import test_api

logger = logging.getLogger("test_kafka_client")


@pytest.fixture(scope="session", autouse=True)
def kafka_container(request):
    with KafkaContainer() as kafka:
        bootstrap_server = kafka.get_bootstrap_server()
        logger.info(f"bootstrap_server: {bootstrap_server}")
        os.environ["BOOTSTRAP_SERVER"] = bootstrap_server
        yield bootstrap_server


@pytest.fixture(autouse=True)
def kafka_test_helpers(kafka_container):
    test_consumer_config = {
        "bootstrap.servers": kafka_container,
        "group.id": "test-verifier-group",
        "auto.offset.reset": "earliest",
    }
    test_consumer = Consumer(test_consumer_config)

    test_producer_config = {
        "bootstrap.servers": kafka_container,
        "acks": "all",
    }
    test_producer = Producer(test_producer_config)

    yield test_consumer, test_producer

    try:
        logger.info("closing test consumer and test producer...")
        test_consumer.close()
        test_producer.flush(1.0)
        del test_producer
    except Exception:  # noqa: BLE001
        logger.warning("failed to cleanly close test consumer and test producer")


def delivery_callback(err, msg):
    if err:
        logger.info("Failed to send message: {err}")
    else:
        logger.info(f"Sent message to topic {msg.topic()}")


def test_kafka_client(kafka_test_helpers):
    test_consumer, test_producer = kafka_test_helpers
    test_consumer.subscribe(["logistics-solution"])

    client = kafka_client.KafkaClient()
    client_thread = threading.Thread(target=client.start, daemon=True)
    client_thread.start()

    time.sleep(1.0)

    logger.info("sending message")
    logistics_instance: LogisticsInstance = LogisticsInstance.from_dict(
        test_api.load_instance_json("instance0.json")
    )
    test_producer.produce(
        "logistics-instance",
        json.dumps(logistics_instance.to_dict()),
        callback=delivery_callback,
    )
    test_producer.flush()

    logistics_solution: LogisticsSolution | None = None
    # Try polling for up to 10 seconds
    retries = 15
    while retries > 0:
        msg = test_consumer.poll(1.0)
        if msg is None:
            retries -= 1
            logger.info("waiting...")
            continue
        if msg.error():
            if msg.error().code() in (
                KafkaError.UNKNOWN_TOPIC_OR_PART,
                KafkaError._UNKNOWN_TOPIC,
                KafkaError._UNKNOWN_PARTITION,
            ):
                retries -= 1
                logger.warning(f"{msg.error()}")
                continue
            # Fail only on actual unrecoverable errors
            pytest.fail(f"test consumer error: {msg.error()}")
        else:
            logger.info(f"received logistics solution: {msg.value()}")
            logistics_solution = LogisticsSolution.from_dict(json.loads(msg.value()))
            break

    client.stop()
    client_thread.join(5.0)

    assert logistics_solution is not None, (
        "Did not receive a LogisticsSolution from KafkaClient."
    )
