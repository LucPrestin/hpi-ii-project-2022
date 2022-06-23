import logging
import re
from tokenize import String
from typing import List, Tuple

from parsel import Selector

from build.gen.bakdata.corporate.v1.announcement_pb2 import Announcement
from build.gen.bakdata.corporate.v1.utils_pb2 import Status
from .producer import AnnouncementProducer

log = logging.getLogger(__name__)


class AnnouncementExtractor:
    def __init__(self) -> None:
        self.announcement_producer: AnnouncementProducer = AnnouncementProducer()

    def extract(self, text, announcement_id: int, state: str) -> None:
        selector = Selector(text=text)
        announcement = Announcement()

        announcement.announcement_id = announcement_id
        announcement.state = state
        announcement.reference_id = self.extract_company_reference_number(selector)
        announcement.id = f"{state}_{announcement_id}"
        announcement.event_date = selector.xpath("/html/body/font/table/tr[4]/td/text()").get()

        event_type = selector.xpath("/html/body/font/table/tr[3]/td/text()").get()
        self.set_event_status(announcement, event_type)

        raw_text: str = selector.xpath("/html/body/font/table/tr[6]/td/text()").get()

        announcement.raw_information = raw_text
        announcement.company_name = self.extract_company_name(raw_text)

        self.set_announcement_people(announcement, raw_text)

        self.announcement_producer.produce_to_topic(announcement=announcement)

        log.debug(announcement)

    @staticmethod
    def extract_company_reference_number(selector: Selector) -> str:
        return ((selector.xpath("/html/body/font/table/tr[1]/td/nobr/u/text()").get()).split(": ")[1]).strip()

    @staticmethod
    def set_event_status(announcement, event_type) -> None:
        if event_type == "Neueintragungen":
            log.debug(f"New company found: {announcement.id}")
            announcement.event_type = "create"
            announcement.status = Status.STATUS_ACTIVE
        elif event_type == "Veränderungen":
            log.debug(f"Changes are made to company: {announcement.id}")
            announcement.event_type = "update"
            announcement.status = Status.STATUS_ACTIVE
        elif event_type == "Löschungen":
            log.debug(f"Company {announcement.id} is inactive")
            announcement.event_type = "delete"
            announcement.status = Status.STATUS_INACTIVE

    @staticmethod
    def extract_company_name(raw_text: String) -> str:
        return raw_text.split(',', 1)[0]

    def set_announcement_people(self, announcement, raw_text) -> None:
        people, person_type = self.extract_person(raw_text)
        if person_type == 'Geschäftsführer:' or person_type == 'Geschäftsführerin:':
            announcement.ceos.extend(people)
        elif person_type == 'Gesellschafter:' or person_type == 'Gesellschafterin:':
            announcement.shareholders.extend(people)

    def extract_person(self, information: String) -> Tuple[List[str], str]:
        regexes = {
            'Inhaber:': self.extract_ceos,
            'Inhaberin:': self.extract_ceos,
            'Geschäftsführer:': self.extract_ceos,
            'Geschäftsführerin:': self.extract_ceos,
            'Gesellschafter:': self.extract_shareholders,
            'Gesellschafterin:': self.extract_shareholders
        }

        people = []
        p_type = ''

        for person_type, method in regexes.items():
            if re.search(person_type, information):
                raw_people = information.split(person_type, 1)[1]
                people = method(raw_people)
                p_type = person_type
                break

        return people, p_type

    @staticmethod
    def extract_ceos(raw_ceos: str) -> List[str]:
        result = []
        for raw_ceo in raw_ceos.split(';'):
            intel = raw_ceo.split(',')
            result.append(intel[0] + ', ' + intel[1])
        return result

    @staticmethod
    def extract_shareholders(raw_shareholders: str) -> List[str]:
        return [raw_shareholders.split(';')[1]]
