import json
import logging
import os
import signal

from confluent_kafka import Consumer, KafkaError, Producer
from confluent_kafka._types import HeadersType
from confluent_kafka.admin._metadata import ClusterMetadata

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

        bootstrap_server = os.getenv("KAFKA_BOOTSTRAP_SERVER")
        if bootstrap_server is None:
            raise Exception("KAFKA_BOOTSTRAP_SERVER is required.")  # noqa: TRY002
        consumer_topic = os.getenv("KAFKA_TOPIC_LOGISTICS_INSTANCE")
        if consumer_topic is None:
            raise Exception("KAFKA_TOPIC_LOGISTICS_INSTANCE is required.")  # noqa: TRY002

        self.logger.info(f"Kafka bootstrap servers: {bootstrap_server}")

        sasl_config = None
        username = os.getenv("KAFKA_USERNAME")
        password = os.getenv("KAFKA_PASSWORD")
        if username is not None and password is not None:
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
        if sasl_config is not None:
            producer_config.update(sasl_config)
        self.producer = Producer(producer_config)

        consumer_config = {
            "bootstrap.servers": bootstrap_server,
            "group.id": "logistics-scheduler",
            "allow.auto.create.topics": "true",
            "auto.offset.reset": "earliest",
        }
        if sasl_config is not None:
            consumer_config.update(sasl_config)
        self.consumer_topic = consumer_topic
        self.consumer = Consumer(consumer_config)
        self.consuming = False

        self.logger.info(f"Checking if topic {self.consumer_topic} exists")
        meta_data: ClusterMetadata = self.consumer.list_topics(self.consumer_topic)
        if (
            meta_data.topics is None
            or meta_data.topics.get(self.consumer_topic) is None
        ):
            self.logger.info(f"Topic {self.consumer_topic} not found")
        else:
            self.logger.info(f"Topic {meta_data.topics.get(self.consumer_topic)} found")

    def __handle_signal(self, signum: int, frame):
        self.logger.info(f"Received shutdown signal {signum}")
        self.stop()

    def __produce(
        self,
        logistics_solution: LogisticsSolution,
        correlation_id: str,
        reply_topic: str,
    ):
        def delivery_callback(err, msg):
            if err:
                self.logger.error("Failed to return LogisticsSolution: {err}")
            else:
                self.logger.info(
                    f"Returned LogisticsSolution to topic {msg.topic()}: {msg.value()}"
                )

        logistics_solution_json: str = json.dumps(logistics_solution.to_dict())
        self.producer.produce(
            reply_topic,
            logistics_solution_json,
            headers=[
                ("CorrelationId", correlation_id.encode("utf-8")),
            ],
            on_delivery=delivery_callback,
        )
        self.producer.flush(10)

    def __consume(self):
        self.logger.info(f"Subscribing to topic {self.consumer_topic}")
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
                headers = msg.headers()
                if value is None or headers is None:
                    self.logger.error(
                        f"Received message without value or headers from topic {msg.topic()}"
                    )
                else:
                    self.__handle_msg(value, headers)

    def __extractHeaders(self, headers: HeadersType) -> tuple[str | None, str | None]:
        correlation_id: str | None = None
        reply_topic: str | None = None

        for key, value in headers:
            if key == "CorrelationId":
                correlation_id = self.__getHeaderValue(value)
            if key == "ReplyTopic":
                reply_topic = self.__getHeaderValue(value)

        return (correlation_id, reply_topic)

    def __getHeaderValue(self, value: str | bytes | None) -> str | None:
        if type(value) == bytes:
            return value.decode("utf-8")
        elif type(value) == str:
            return value
        else:
            return None

    def __handle_msg(self, msg_bytes: bytes, msg_headers: HeadersType):
        try:
            correlation_id, reply_topic = self.__extractHeaders(msg_headers)
            if correlation_id is None or reply_topic is None:
                self.logger.error(
                    "Message header CorrelationId or ReplyTopic is missing"
                )
                return
            self.logger.info(f"Received message headers {msg_headers}")

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
                self.__produce(logistics_solution, correlation_id, reply_topic)

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
