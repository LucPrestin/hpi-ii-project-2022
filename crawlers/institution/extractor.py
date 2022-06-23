import logging

from build.gen.bakdata.corporate.v1.institution_pb2 import Institution
from build.gen.bakdata.corporate.v1.person_pb2 import Person
from build.gen.bakdata.corporate.v1.utils_pb2 import *
from .producer import InstitutionProducer

log = logging.getLogger(__name__)


class InstitutionExtractor:
    def __init__(self) -> None:
        self.producer = InstitutionProducer()

    def extract(self, detailed_information) -> None:
        institution = Institution()

        register_number = detailed_information['registerNumber']
        internal_register_id = detailed_information['id']

        institution.id = f"{register_number}_{internal_register_id}"

        if "name" not in detailed_information["lobbyistIdentity"]:
            if detailed_information["lobbyistIdentity"]["identity"] != "NATURAL" and \
                    detailed_information["lobbyistIdentity"][
                        "identity"] != "SELF_OPERATED":
                institution.name = detailed_information["lobbyistIdentity"]["name"]  # throws error
            else:
                log.info(f"Skipping {register_number} with id {internal_register_id} since it's a person")
                return
        else:
            institution.name = detailed_information["lobbyistIdentity"]["name"]
        if "de" in detailed_information["activity"]:
            institution.business_category = detailed_information["activity"]["de"]
        else:
            institution.business_category = detailed_information["activity"]["text"]
        if "membershipEntries" in detailed_information:
            institution.memberships = detailed_information["membershipEntries"]
        if "firstPublicationData" in detailed_information:
            institution.initial_registration = detailed_information["account"]["firstPublicationData"]
        institution.register_id = register_number
        address_json = detailed_information["lobbyistIdentity"]["address"]
        if address_json["type"] == "FOREIGN":
            if "internationalAdditional1" in address_json and "internationalAdditional2" in address_json:
                institution.contact.CopyFrom(Contact(
                    address=f"{address_json['internationalAdditional1']}, {address_json['internationalAdditional2']} {address_json['city']} {address_json['country']['code']}",
                    phone=detailed_information["lobbyistIdentity"]["phoneNumber"],
                    email=detailed_information["lobbyistIdentity"]["organizationEmails"],
                    website=detailed_information["lobbyistIdentity"]["websites"]
                ))
            else:
                institution.contact.CopyFrom(Contact(
                    address=f"{address_json['internationalAdditional1']}, {address_json['city']} {address_json['country']['code']}",
                    phone=detailed_information["lobbyistIdentity"]["phoneNumber"],
                    email=detailed_information["lobbyistIdentity"]["organizationEmails"],
                    website=detailed_information["lobbyistIdentity"]["websites"]
                ))
        elif address_json["type"] == "NATIONAL":
            institution.contact.CopyFrom(Contact(
                address=f"{address_json['street']} {address_json['streetNumber']}, {address_json['zipCode']} {address_json['city']} {address_json['country']['code']}",
                phone=detailed_information["lobbyistIdentity"]["phoneNumber"],
                email=detailed_information["lobbyistIdentity"]["organizationEmails"],
                website=detailed_information["lobbyistIdentity"]["websites"]
            ))
        if "financialExpensesEuro" in detailed_information:
            institution.annual_interest_expenditure.CopyFrom(Range(
                start=detailed_information["financialExpensesEuro"]["from"],
                end=detailed_information["financialExpensesEuro"]["to"]
            ))
        institution.representatives.extend(map(lambda entry: Person(
            name=f"{entry['commonFirstName']} {entry['lastName']}",
            role=entry["function"],
            phone=entry["phoneNumber"],
            email=entry["organizationMemberEmails"]
        ), detailed_information["lobbyistIdentity"]["legalRepresentatives"]))

        institution.interest_staff.extend(map(
            self.get_interest_person, detailed_information["lobbyistIdentity"]["namedEmployees"]))
        institution.interests.extend(map(
            lambda interest: interest["de"] if "de" in interest else interest["fieldOfInterestText"],
            detailed_information["fieldsOfInterest"]))
        institution.activities_description = detailed_information["activityDescription"]
        institution.clients.extend(
            map(lambda entry: f"{entry['name']} {entry['legalForm']}", detailed_information["clientOrganizations"]))
        institution.clients.extend(
            map(lambda entry: f"{entry['commonFirstName']} {entry['lastName']}", detailed_information["clientPersons"]))

        for entry in detailed_information["donators"]:
            if entry["categoryType"] == "PUBLIC_ALLOWANCES":
                institution.grants.append(
                    self.get_grant_donation(entry)
                )
            elif entry["categoryType"] == "DONATIONS":
                institution.donations.append(
                    self.get_grant_donation(entry)
                )

        institution.financial_report_url = ""
        for entry in detailed_information["registerEntryMedia"]:
            if entry["type"] == "ANNUAL_REPORT":
                institution.financial_report_url = entry["media"]["url"]
            if entry["type"] == "CODE_OF_CONDUCT":
                institution.code_of_conduct_url = entry["media"]["url"]

        if "disclosureRequirementsExist" in detailed_information:
            institution.disclosure_required = detailed_information["disclosureRequirementsExist"]

        self.producer.produce_to_topic(institution=institution)
        log.debug(institution)

    @staticmethod
    def get_interest_person(entry):
        if "commonFirstName" in entry and "lastName" in entry:
            return f"{entry['commonFirstName']} {entry['lastName']}"
        return

    @staticmethod
    def get_grant_donation(entry):
        if "location" in entry:
            return GrantDonation(
                name=entry["name"],
                location=entry["location"],
                money=Range(
                    start=entry["donationEuro"]["from"],
                    end=entry["donationEuro"]["to"],
                ),
                project=entry["description"])
        else:
            return GrantDonation(
                name=entry["name"],
                money=Range(
                    start=entry["donationEuro"]["from"],
                    end=entry["donationEuro"]["to"],
                ),
                project=entry["description"])
