import logging

from build.gen.bakdata.corporate.v1.grant_pb2 import GrantDonation
from .producer import GrantDonationProducer

log = logging.getLogger(__name__)


class GrantDonationExtractor:
    def __init__(self) -> None:
        self.producer = GrantDonationProducer()

    def extract_from_lobby_register(self, lobby_grant_dict: dict, lobbyist: str, index: int) -> GrantDonation:
        grant = GrantDonation()

        grant.id = f'{lobbyist} - {index}'
        grant.name = lobby_grant_dict['name']
        grant.location = lobby_grant_dict['location'] if 'location' in lobby_grant_dict else ''

        donation = lobby_grant_dict['donationEuro']
        grant.money.start = donation['from']
        grant.money.end = donation['to']

        grant.project = lobby_grant_dict['description']

        self.producer.produce_to_topic(grant)
        return grant
