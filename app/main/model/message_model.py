import logging
from logging.config import fileConfig

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import UNIQUE_ID, TYPE, SEARCH_PARAMETERS
from main.model.model_utils import filter_transforms, MissingConfigException

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class Message:
    """Class which holds all message related data together for a distinct message id"""
    def __init__(self):
        self.has_status = False
        self.has_events = False
        self.has_payloads = False
        self.has_metadata = False
        self.has_transforms = False
        self.has_rule = False
        self.has_search_criteria = False
        self.has_message_details = False
        self.has_payload_transform_mappings = False
        self.message_uid = None
        self.has_server_location = False
        self.has_ice_dashboard_stats = True
        self.has_ice_failed_messages = False

    def add_rule(self, rule):
        self.rule = rule
        self.has_rule = True

    def add_status(self, status_record):
        self.status_dict = status_record
        self.has_status = True
        self.message_uid = status_record.get(UNIQUE_ID)

    def add_message_uid(self, msg_uid):
        self.message_uid = msg_uid

    def add_message_region(self, region):
        self.message_region = region

    def add_message_details(self, message_details_data):
        self.message_details = message_details_data
        self.has_message_details = True

    def add_events(self, events_data):
        self.events_list = events_data
        self.has_events = True

    def add_metadata(self, metadata_data):
        self.metadata_list = metadata_data
        self.has_metadata = True

    def add_payloads(self, payload_data):
        self.payloads_list = payload_data
        self.has_payloads = True

    def add_transforms(self, transform_data):
        # filter transforms to only include the relevant ones
        if self.has_transform_search_parameters():
            self.transforms_list = filter_transforms(self.get_transform_search_criteria(), transform_data)
        # Add all transforms if there is no filter defined
        else:
            self.transforms_list = transform_data
        self.has_transforms = True

    def add_search_criteria(self, search_criteria):
        self.search_criteria = search_criteria
        self.has_search_criteria = True

    def add_payload_transform_mappings(self, mappings):
        self.payload_transform_mappings = mappings
        self.has_payload_transform_mappings = True

    def add_server_location(self, location_dict):
        self.server_location_dict = location_dict
        self.has_server_location = True

    def add_ice_dashboard_stats(self, dashboard_stats):
        self.ice_dashboard_stats = dashboard_stats
        self.has_ice_dashboard_stats = True

    def add_ice_failed_messages(self, messages):
        self.ice_failed_messages = messages
        self.has_ice_failed_messages = True

    def has_transform_search_parameters(self):
        if self.has_search_criteria:
            return True
        if self.has_rule and self.rule and self.rule.get(SEARCH_PARAMETERS):
            return True
        return False

    def get_transform_search_criteria(self):
        if self.has_search_criteria:
            return self.search_criteria
        if self.has_rule and self.rule and self.rule.get(SEARCH_PARAMETERS):
            return self.rule.get(SEARCH_PARAMETERS)
        raise MissingConfigException("Search criteria or rule not set")
