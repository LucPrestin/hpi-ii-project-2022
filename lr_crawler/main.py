import logging
import os
import string
from time import sleep

import click

import json
from os import path

from lr_crawler.lr_extractor import LrExtractor

logging.basicConfig(
    level=os.environ.get("LOGLEVEL", "INFO"), format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
)
log = logging.getLogger(__name__)

@click.command()
@click.option("-i", "--id", "lr_id", type=click.STRING, help="The lr id to extract")
def run(lr_id: string):
    file = open(path.realpath("./assets/json/Lobbyregistersuche-2022-05-24_13-37-55.json"))
    data = json.load(file)
    print(f"results: {len(data['results'])}")
    if lr_id == None:
        for entry in data["results"]:
            sleep(0.5)
            LrExtractor(entry["registerNumber"], entry["id"]).extract()
    else:
        for entry in data["results"]:
            if entry["registerNumber"] == lr_id:
                LrExtractor(entry["registerNumber"], entry["id"]).extract()

if __name__ == "__main__":
    run()
