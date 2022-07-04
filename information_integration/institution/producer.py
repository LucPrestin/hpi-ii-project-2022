import logging

from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.protobuf import ProtobufSerializer
from confluent_kafka.serialization import StringSerializer

from build.gen.bakdata.corporate.v1 import institution_pb2
from build.gen.bakdata.corporate.v1.institution_pb2 import Institution
from ._constants import SCHEMA_REGISTRY_URL, BOOTSTRAP_SERVER, TOPIC
from ..utils import get_used_ids

log = logging.getLogger(__name__)


class InstitutionProducer:
    def __init__(self):
        self.used_ids = get_used_ids(TOPIC)

        schema_registry_conf = {"url": SCHEMA_REGISTRY_URL}
        schema_registry_client = SchemaRegistryClient(schema_registry_conf)

        protobuf_serializer = ProtobufSerializer(
            institution_pb2.Institution,
            schema_registry_client,
            {"use.deprecated.format": True}
        )

        string_serializer = StringSerializer("utf_8")

        producer_conf = {
            "bootstrap.servers": BOOTSTRAP_SERVER,
            "key.serializer": string_serializer,
            "value.serializer": protobuf_serializer
        }

        self.producer = SerializingProducer(producer_conf)

    def produce_to_topic(self, institution: Institution):
        if institution.id not in self.used_ids:
            self.used_ids.append(institution.id)

            self.producer.produce(
                topic=TOPIC,
                partition=-1,
                key=str(institution.id),
                value=institution,
                on_delivery=self.delivery_report
            )

            # It is a naive approach to flush after each produce this can be optimised
            self.producer.poll()
        else:
            log.info(f'Institution {institution.id} already produced to {TOPIC}, skipping entry')

    @staticmethod
    def delivery_report(err, msg):
        """
        Reports the failure or success of a message delivery.
        Args:
            err (KafkaError): The error that occurred on None on success.
            msg (Message): The message that was produced or failed.
        Note:
            In the delivery report callback the Message.key() and Message.value()
            will be the binary format as encoded by any configured Serializers and
            not the same object that was passed to produce().
            If you wish to pass the original object(s) for key and value to delivery
            report callback we recommend a bound callback or lambda where you pass
            the objects along.
        """
        if err is not None:
            log.error("Delivery failed for User record {}: {}".format(msg.key(), err))
            return
        log.info(
            "User record {} successfully produced to {} [{}] at offset {}".format(
                msg.key(), msg.topic(), msg.partition(), msg.offset()
            )
        )
