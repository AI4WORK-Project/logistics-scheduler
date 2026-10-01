import json
import logging
import os
import signal

from confluent_kafka import Consumer, KafkaError, Producer

from logistics.factory import LogisticsSchedulingFactory
from logistics.instance import LogisticsInstance
from logistics.solution import LogisticsSolution

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
)


class KafkaClient:
    def __init__(self) -> None:
        signal.signal(signal.SIGTERM, self.__handle_signal)
        signal.signal(signal.SIGINT, self.__handle_signal)

        self.logger = logging.getLogger("kafka-client")

        bootstrap_server = os.environ["KAFKA_BOOTSTRAP_SERVER"]
        self.logger.info(f"Kafka bootstrap servers: {bootstrap_server}")

        username = os.environ["KAFKA_USERNAME"]
        password = os.environ["KAFKA_PASSWORD"]
        sasl_config = {
            "security.protocol": "SASL_PLAINTEXT",
            "sasl.mechanism": "PLAIN",
            "sasl.username": username,
            "sasl.password": password,
        }

        producer_config = {
            "bootstrap.servers": bootstrap_server,
            "acks": "all",
        }
        producer_config.update(sasl_config)
        self.producer_topic = "logistics-solution"
        self.producer = Producer(producer_config)

        consumer_config = {
            "bootstrap.servers": bootstrap_server,
            "group.id": "logistics-scheduler",
            "auto.offset.reset": "earliest",
        }
        consumer_config.update(sasl_config)
        self.consumer_topic = "logistics-instance"
        self.consumer = Consumer(consumer_config)
        self.consuming = False

    def __handle_signal(self, signum: int, frame):
        self.logger.info(f"Received shutdown signal {signum}")
        self.stop()

    def __produce(self, logistics_solution: LogisticsSolution):
        def delivery_callback(err, msg):
            if err:
                self.logger.error("Failed to return LogisticsSolution: {err}")
            else:
                self.logger.info(
                    f"Returned LogisticsSolution to topic {msg.topic()}: {msg.value()}"
                )

        logistics_solution_json: str = json.dumps(logistics_solution.to_dict())
        self.producer.produce(
            self.producer_topic, logistics_solution_json, callback=delivery_callback
        )
        self.producer.flush(10)

    def __consume(self):
        self.consumer.subscribe([self.consumer_topic])
        while self.consuming:
            msg = self.consumer.poll(1.0)
            if msg is None:
                self.logger.info("Waiting...")
            elif msg.error():
                error = msg.error()
                errorMsg = f"Failed to poll topic {self.consumer_topic}: {msg.error()}"
                if error and error.code() in (
                    KafkaError.UNKNOWN_TOPIC_OR_PART,
                    KafkaError._UNKNOWN_TOPIC,
                    KafkaError._UNKNOWN_PARTITION,
                ):
                    self.logger.warning(f"{errorMsg}")
                else:
                    self.logger.error(f"{errorMsg}")
            else:
                value = msg.value()
                if value is None:
                    self.logger.warning(
                        f"Received empty message from topic {msg.topic()}"
                    )
                else:
                    self.__handle_msg(value)

    def __handle_msg(self, msg_bytes: bytes):
        try:
            msg_dict = json.loads(msg_bytes)
            logistics_instance: LogisticsInstance = LogisticsInstance.from_dict(
                msg_dict
            )
            logistics_instance.validate()
            self.logger.info(f"Received LogisticsInstance {logistics_instance}")

            factory = LogisticsSchedulingFactory(logistics_instance)
            self.logger.info("LogisticsSchedulingFactory created")

            logistics_solution: LogisticsSolution | None = factory.get_solution()
            if logistics_solution is None:
                self.logger.error("Failed to find solution for given LogisticsInstance")
            else:
                self.__produce(logistics_solution)

        except Exception as e:  # noqa: BLE001
            self.logger.error(f"Failed to process msg: {e}")

    def start(self):
        self.logger.info("Starting kafka client...")
        self.consuming = True
        self.__consume()

    def stop(self):
        self.logger.info("Stopping kafka client...")
        self.consuming = False
        # Leave group and commit final offsets
        if self.consumer is not None:
            self.logger.info("Stopping consumer...")
            self.consumer.close()
        if self.producer is not None:
            self.logger.info("Stopping producer...")
            self.producer.flush(timeout=1.0)
            del self.producer


if __name__ == "__main__":
    logger = logging.getLogger("logistics-scheduler-kafka")
    try:
        kafka_client = KafkaClient()
        kafka_client.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # noqa: BLE001
        logger.error(f"{e}")
