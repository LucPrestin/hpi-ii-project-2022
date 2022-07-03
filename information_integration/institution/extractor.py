import logging
from hashlib import md5

from build.gen.bakdata.corporate.v1.institution_pb2 import Institution
from build.gen.bakdata.corporate.v1.utils_pb2 import *
from information_integration.grant import GrantDonationExtractor
from information_integration.person import PersonExtractor
from .producer import InstitutionProducer

log = logging.getLogger(__name__)


class InstitutionExtractor:
    def __init__(self) -> None:
        self.institution_producer = InstitutionProducer()
        self.person_extractor = PersonExtractor()
        self.grant_extractor = GrantDonationExtractor()

    def extract(self, request_result) -> None:
        institution = Institution()

        register_number = request_result['registerNumber']

        detailed_information = request_result['registerEntryDetail']
        internal_register_id = detailed_information['id']

        institution.id = md5(f'{register_number}{internal_register_id}'.encode('utf_8')).hexdigest()

        if "name" not in detailed_information["lobbyistIdentity"]:
            if detailed_information["lobbyistIdentity"]["identity"] != "NATURAL" and \
                    detailed_information["lobbyistIdentity"]["identity"] != "SELF_OPERATED":
                institution.name = detailed_information["lobbyistIdentity"]["name"]
            else:
                self.person_extractor.extract_from_lobby_register(detailed_information['lobbyistIdentity'])
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

        institution.representatives.extend(map(
            lambda person_dict: self.person_extractor.extract_from_lobby_register(person_dict),
            detailed_information["lobbyistIdentity"]["legalRepresentatives"]))

        institution.interest_staff.extend(map(
            lambda person_dict: self.person_extractor.extract_from_lobby_register(person_dict),
            detailed_information["lobbyistIdentity"]["namedEmployees"]))

        institution.interests.extend(map(
            lambda interest: interest["de"] if "de" in interest else interest["fieldOfInterestText"],
            detailed_information["fieldsOfInterest"]))

        institution.activities_description = detailed_information["activityDescription"]

        institution.clients.extend(map(
            lambda client_dict: f"{client_dict['name']} {client_dict['legalForm']}",
            detailed_information["clientOrganizations"]))

        institution.clients.extend(map(
            lambda person_dict: self.person_extractor.extract_from_lobby_register(person_dict),
            detailed_information["clientPersons"]))

        for index, entry in enumerate(detailed_information["donators"]):
            if entry["categoryType"] == "PUBLIC_ALLOWANCES":
                institution.grants.append(
                    self.grant_extractor.extract_from_lobby_register(
                        entry,
                        institution.name,
                        index))
            elif entry["categoryType"] == "DONATIONS":
                institution.donations.append(
                    self.grant_extractor.extract_from_lobby_register(
                        entry,
                        institution.name,
                        index))

        institution.financial_report_url = ""
        for entry in detailed_information["registerEntryMedia"]:
            if entry["type"] == "ANNUAL_REPORT":
                institution.financial_report_url = entry["media"]["url"]
            if entry["type"] == "CODE_OF_CONDUCT":
                institution.code_of_conduct_url = entry["media"]["url"]

        if "disclosureRequirementsExist" in detailed_information:
            institution.disclosure_required = detailed_information["disclosureRequirementsExist"]

        self.institution_producer.produce_to_topic(institution=institution)
        log.debug(institution)
