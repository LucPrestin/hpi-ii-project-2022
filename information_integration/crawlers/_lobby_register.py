import json
import logging
import os
from time import sleep

import requests

from information_integration.institution.extractor import InstitutionExtractor

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


def crawl_all_institutions():
    extractor = InstitutionExtractor()

    data = _fetch_general_data_list()

    for entry in data["results"]:
        sleep(0.5)
        detailed_data = _fetch_detailed_data(entry['detailsPageUrl'])

        try:
            extractor.extract(detailed_data)
        except Exception as ex:
            log.error(f"Skipping register entry {detailed_data['register_number']}")
            log.error(f"Cause: {ex}")
            continue


def crawl_institution_with_id(register_number: str) -> None:
    extractor = InstitutionExtractor()

    general_data = _fetch_general_data(register_number)

    if general_data is None:
        log.error(f'An entry with the register number {register_number} does not exist')
        return

    detailed_data = _fetch_detailed_data(general_data['detailsPageUrl'])

    try:
        extractor.extract(detailed_data)
    except Exception as ex:
        log.error(f"Skipping register entry {detailed_data['register_number']}")
        log.error(f"Cause: {ex}")


def _fetch_general_data_list() -> dict:
    log.info('Sending Request for list of lobby register entries')

    url = 'https://www.lobbyregister.bundestag.de/sucheJson?q='
    return _send_request(url)


def _fetch_general_data(register_number: str) -> dict:
    log.info(f'Sending Request for rough data on lobby register entry: {register_number}')

    url = f'https://www.lobbyregister.bundestag.de/sucheJson?q={register_number}'
    general_data = _send_request(url)

    if general_data is not None and 'resultCount' in general_data and general_data['resultCount'] == 1:
        return general_data['result'][0]


def _fetch_detailed_data(register_number: str, id: str) -> dict:
    log.info(f'Sending Request for lobby register entry: {register_number}')

    url = f'https://www.lobbyregister.bundestag.de/sucheJson/{register_number}/{id}'
    return _send_request(url)


def _send_request(url) -> dict:
    response = requests.get(url=url)
    raw_text = response.text
    return json.loads(raw_text)
