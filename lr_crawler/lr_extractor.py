import imp
import json
import logging
from time import sleep
from typing import List

import requests

from build.gen.bakdata.corporate.v1.institution_pb2 import Institution
from build.gen.bakdata.corporate.v1.person_pb2 import Person
from build.gen.bakdata.corporate.v1.utils_pb2 import *
from lr_producer import LrProducer

log = logging.getLogger(__name__)


class LrExtractor:
    def __init__(self, register_number, id):
        self.register_number = register_number
        self.id = id
        self.producer = LrProducer()

    def extract(self):
        #try:
        log.info(
            f"Sending Request for lobby register entry: {self.register_number}")
        json_all = self.send_request().text
        json_result = json.loads(json_all)["registerEntryDetail"]
        print(json_result)
        institution = Institution()
        int: institution.id = self.id
        institution.name = json_result["lobbyistIdentity"]["name"]
        institution.business_category = json_result["activity"]["de"]
        if "membershipEntries" in json_result:
            institution.memberships = json_result["membershipEntries"]
        if "firstPublicationData" in json_result:
            institution.initial_registration = json_result["account"]["firstPublicationData"]
        institution.register_id = self.register_number
        address_json = json_result["lobbyistIdentity"]["address"]
        if address_json["type"] == "FOREIGN":
            institution.contact.CopyFrom(Contact(
                address=f"{address_json['internationalAdditional1']}, {address_json['internationalAdditional2']} {address_json['city']} {address_json['country']['code']}",
                phone=json_result["lobbyistIdentity"]["phoneNumber"],
                email=json_result["lobbyistIdentity"]["organizationEmails"],
                website=json_result["lobbyistIdentity"]["websites"]
            ))
        elif address_json["type"] == "NATIONAL":
            institution.contact.CopyFrom(Contact(
                address=f"{address_json['street']} {address_json['streetNumber']}, {address_json['zipCode']} {address_json['city']} {address_json['country']['code']}",
                phone=json_result["lobbyistIdentity"]["phoneNumber"],
                email=json_result["lobbyistIdentity"]["organizationEmails"],
                website=json_result["lobbyistIdentity"]["websites"]
            ))
        institution.annual_interest_expenditure.CopyFrom(Range(
            start=json_result["financialExpensesEuro"]["from"],
            end=json_result["financialExpensesEuro"]["to"]
        ))
        institution.representatives.extend(map(lambda entry: Person(
            name=f"{entry['commonFirstName']} {entry['lastName']}",
            role=entry["function"],
            phone=entry["phoneNumber"],
            email=entry["organizationMemberEmails"]
        ), json_result["lobbyistIdentity"]["legalRepresentatives"]))
        institution.interest_staff.extend(map(
            lambda entry: f"{entry['commonFirstName']} {entry['lastName']}", json_result["lobbyistIdentity"]["namedEmployees"]))
        institution.interests.extend(map(
            lambda interest: interest["de"] if "de" in interest else interest["fieldOfInterestText"], json_result["fieldsOfInterest"]))
        institution.activities_description = json_result["activityDescription"]
        institution.clients = []
        institution.clients.extend(
            lambda entry: f"{entry['name']} {entry['legalForm']}", json_result["clientOrganizations"])
        institution.clients.extend(
            lambda entry: f"{entry['commonFirstName']} {entry['lastName']}", json_result["clientPersons"])

        institution.grants = []
        institution.donations = []
        for entry in json_result["donators"]:
            if entry["categoryType"] == "PUBLIC_ALLOWANCES":
                institution.grants.append(
                    GrantDonation(
                        entry["name"],
                        entry["location"],
                        Range(
                            entry["donationEuro"]["from"],
                            entry["donationEuro"]["to"],
                        ),
                        entry["description"]
                    )
                )
            elif entry["categoryType"] == "DONATIONS":
                institution.donations.append(
                    GrantDonation(
                        entry["name"],
                        entry["location"],
                        Range(
                            entry["donationEuro"]["from"],
                            entry["donationEuro"]["to"],
                        ),
                        entry["description"]
                    ))

        institution.financial_report_url = ""
        for entry in json_result["registerEntryMedia"]:
            if entry["type"] == "ANNUAL_REPORT":
                institution.financial_report_url = entry["media"]["url"]
            if entry["type"] == "CODE_OF_CONDUCT":
                institution.code_of_conduct_url = entry["media"]["url"]

        institution.disclosure_required = json_result["disclosureRequirementsExist"]

        self.producer.produce_to_topic(corporate=corporate)
        log.debug(institution)
        # except Exception as ex:
        #     log.error(f"Skipping {self.register_number} with id {self.id}")
        #     log.error(f"Cause: {ex}")
        exit(0)

    def send_request(self):
        url = f"https://www.lobbyregister.bundestag.de/sucheJson/{self.register_number}/{self.id}"
        return requests.get(url=url)
