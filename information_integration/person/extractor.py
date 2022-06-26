import logging

from .producer import PersonProducer

log = logging.getLogger(__name__)


class PersonExtractor:
    def __init__(self) -> None:
        self.producer = PersonProducer()

    def extract(self, detailed_information) -> None:
        pass
