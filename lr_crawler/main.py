import logging
import os
from time import sleep

import click

import json

from lr_crawler.constant import State
from lr_crawler.lr_extractor import LrExtractor

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)


@click.command()
def run():
    file = open("../assets/json/Lobbyregistersuche-2022-05-24_13-37-55.json")
    data = json.load(file)
    for entry in data["results"]:
        sleep(0.5)
        LrExtractor(entry["registerNumber"], entry["id"]).extract()


if __name__ == "__main__":
    run()
