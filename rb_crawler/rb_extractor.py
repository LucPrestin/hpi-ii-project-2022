import logging
from time import sleep
from tokenize import String

import requests
from parsel import Selector

import re

from build.gen.bakdata.corporate.v1.announcement_pb2 import Announcement
from build.gen.bakdata.corporate.v1.utils_pb2 import Status
from rb_producer import RbProducer

log = logging.getLogger(__name__)


class RbExtractor:
    def __init__(self, start_rb_id: int, state: str):
        self.rb_id = start_rb_id
        self.state = state
        self.producer = RbProducer()

    def extract(self):
        while True:
            try:
                log.info(f"Sending Request for: {self.rb_id} and state: {self.state}")
                text = self.send_request()
                if "Falsche Parameter" in text:
                    log.info("The end has reached")
                    break
                selector = Selector(text=text)
                announcement = Announcement()
                announcement.rb_id = self.rb_id
                announcement.state = self.state
                announcement.reference_id = self.extract_company_reference_number(selector)
                event_type = selector.xpath("/html/body/font/table/tr[3]/td/text()").get()
                announcement.event_date = selector.xpath("/html/body/font/table/tr[4]/td/text()").get()
                announcement.id = f"{self.state}_{self.rb_id}"
                raw_text: str = selector.xpath("/html/body/font/table/tr[6]/td/text()").get()
                self.handle_events(announcement, event_type, raw_text)
                self.rb_id = self.rb_id + 1
                log.debug(announcement)
            except Exception as ex:
                log.error(f"Skipping {self.rb_id} in state {self.state}")
                log.error(f"Cause: {ex}")
                self.rb_id = self.rb_id + 1
                continue
        exit(0)

    def send_request(self) -> str:
        url = f"https://www.handelsregisterbekanntmachungen.de/skripte/hrb.php?rb_id={self.rb_id}&land_abk={self.state}"
        # For graceful crawling! Remove this at your own risk!
        sleep(0.5)
        return requests.get(url=url).text

    @staticmethod
    def extract_company_reference_number(selector: Selector) -> str:
        return ((selector.xpath("/html/body/font/table/tr[1]/td/nobr/u/text()").get()).split(": ")[1]).strip()

    def handle_events(self, announcement, event_type, raw_text):
        if event_type == "Neueintragungen":
            self.handle_new_entries(announcement, raw_text)
        elif event_type == "Veränderungen":
            self.handle_changes(announcement, raw_text)
        elif event_type == "Löschungen":
            self.handle_deletes(announcement)
        
        announcement.raw_information = raw_text
        announcement.company_name = self.extract_company_name(raw_text)
        self.set_announcement_people(announcement, raw_text)            

        self.producer.produce_to_topic(announcment=announcement)

    def handle_new_entries(self, announcement: Announcement, raw_text: str) -> Announcement:
        log.debug(f"New company found: {announcement.id}")
        announcement.event_type = "create"
        announcement.status = Status.STATUS_ACTIVE

    def handle_changes(self, announcement: Announcement, raw_text: str):
        log.debug(f"Changes are made to company: {announcement.id}")
        announcement.event_type = "update"
        announcement.status = Status.STATUS_ACTIVE

    def handle_deletes(self, announcment: Announcement):
        log.debug(f"Company {announcment.id} is inactive")
        announcment.event_type = "delete"
        announcment.status = Status.STATUS_INACTIVE
    
    def extract_company_name(self, information: String):
        return information.split(',', 1)[0]
    
    def set_announcement_people(self, announcement, raw_text):
        people, person_type = self.extract_person(raw_text)
        if person_type == 'Geschäftsführer:' or person_type == 'Geschäftsführerin:':
            announcement.ceos.extend(people)
        elif person_type == 'Gesellschafter:' or person_type == 'Gesellschafterin:':
            announcement.shareholders.extend(people)


    def extract_person(self, information: String):
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
                people = method(information.split(person_type, 1)[1])
                p_type = person_type
                break
        
        return people, p_type
    
    def extract_ceos(self, raw_ceos):
        result = []
        for raw_ceo in raw_ceos.split(';'):
            intel = raw_ceo.split(',')
            result.append(intel[0] + ', ' + intel[1])
        return result

    def extract_shareholders(self, raw_shareholders):
        return [raw_shareholders.split(';')[1]]
