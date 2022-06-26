import logging
import os
from time import sleep

import requests

from information_integration.announcement import AnnouncementExtractor
from information_integration.announcement import State

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


def crawl_trade_register_announcements(announcement_id: int, state: State) -> None:
    if state == State.SCHLESWIG_HOLSTEIN and announcement_id < 7830:
        error = ValueError("The start announcement_id for the state SCHLESWIG_HOLSTEIN (sh) is 7831")
        log.error(error)
        exit(1)

    extractor = AnnouncementExtractor()

    while True:
        # For graceful crawling! Remove this at your own risk!
        sleep(0.5)

        log.info(f"Sending Request for: {announcement_id} and state: {state}")

        url = f"https://www.handelsregisterbekanntmachungen.de/skripte/hrb.php?rb_id={announcement_id}&land_abk={state}"
        text = requests.get(url=url).text

        if "Falsche Parameter" in text:
            log.info("The end has reached")
            break

        try:
            extractor.extract(text, announcement_id, state)
        except Exception as ex:
            log.error(f"Skipping {announcement_id} in state {state}")
            log.error(f"Cause: {ex}")
        finally:
            announcement_id = announcement_id + 1
