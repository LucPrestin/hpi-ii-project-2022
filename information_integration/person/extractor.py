import logging
from hashlib import md5
from typing import List

from build.gen.bakdata.corporate.v1.person_pb2 import Person
from .producer import PersonProducer

log = logging.getLogger(__name__)


class PersonExtractor:
    def __init__(self) -> None:
        self.producer = PersonProducer()

    def extract_from_lobby_register(self, lobbyist_identity: dict) -> Person:
        person = Person()

        if 'academicDegreeBefore' in lobbyist_identity:
            title_before = lobbyist_identity['academicDegreeBefore'] + ' ' 
        else:
            title_before = ''
        
        if 'academicDegreeAfter' in lobbyist_identity:
            title_after = ' ' + lobbyist_identity['academicDegreeAfter']
        else:
            title_after = ''

        person.name = f'{title_before}{lobbyist_identity["lastName"].strip().lower()}, {lobbyist_identity["commonFirstName"].strip().lower()}{title_after}'
        person.role = lobbyist_identity['function'] if 'function' in lobbyist_identity else ''
        person.phone = lobbyist_identity['phoneNumber'] if 'phoneNumber' in lobbyist_identity else ''

        if 'organizationMemberEmails' in lobbyist_identity:
            person.email.extend(lobbyist_identity['organizationMemberEmails'])

        person.id = md5(f'{person.name}'.encode('utf_8')).hexdigest()

        self.producer.produce_to_topic(person)
        return person

    def extract_ceos_from_trade_register_announcement(self, raw_ceos: str) -> List[Person]:
        result: List[Person] = []

        for raw_ceo in raw_ceos.split(';'):
            intel = raw_ceo.split(',')

            person = Person()

            if len(intel) >= 2:
                person.name = f'{intel[0].strip().lower()}, {intel[1].strip().lower()}'
            else:
                continue

            person.id = md5(f'{person.name}'.encode('utf_8')).hexdigest()

            self.producer.produce_to_topic(person)
            result.append(person)

        return result

    def extract_shareholder_from_trade_register_announcement(self, raw_shareholders: str) -> Person:
        person = Person()

        person.name = raw_shareholders.split(';')[1].strip().lower()
        person.id = md5(f'{person.name}'.encode('utf_8')).hexdigest()

        self.producer.produce_to_topic(person)
        return [person]
