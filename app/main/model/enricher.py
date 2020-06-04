from main.config.constants import MESSAGE_ID, SEARCH_PARAMETERS, TYPE, DESTINATION, SOURCE

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

from main.model.model_utils import get_transform_search_parameters

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')

METADATA = "metadata"
PAYLOADS = "payloads"
TRANSFORMS = "transforms"
STATUS = "status"
EVENTS = "events"


class MessageEnricher:
    """Given a message model, this class determines which data to retrieve for the message and update the message model with the data"""

    def __init__(self, message_model, cirrus_proxy):
        if not message_model.has_rule:
            raise InvalidStateException("Message Enricher requires rule")
        self.message = message_model
        self.cirrus_proxy = cirrus_proxy

    def __obtain_retrieve_flags_from_rule(self, rule):
        # Hard coded for now but should be based on algorithm requirements
        return {STATUS: True, EVENTS: False, TRANSFORMS: True, PAYLOADS: True, METADATA: False}

    def retrieve_data(self):
        flags_dict = self.__obtain_retrieve_flags_from_rule(self.message.rule)
        if flags_dict[STATUS] and not self.message.has_status:
            # retrieve status data for msg
            self.__retrieve_message_status()
        if flags_dict[EVENTS] and not self.message.has_events:
            # retrieve events data for msg
            self.__retrieve_message_events()
        if flags_dict[PAYLOADS] and not self.message.has_payloads:
            # retrieve payloads data for msg
            self.__retrieve_message_payloads()
        if flags_dict[TRANSFORMS] and not self.message.has_transforms:
            # retrieve transforms for msg
            self.__retrieve_message_transforms()
        if flags_dict[METADATA] and not self.message.has_metadata:
            # retrieve metadata for msg
            self.__retrieve_message_metadata()

    def __retrieve_message_status(self):
        search_criteria = {MESSAGE_ID: self.get_message_id()}
        result = self.cirrus_proxy.search_for_messages(search_criteria)
        if result and isinstance(result, list) and len(result) >= 1:
            self.message.add_status(result[0])
            return
        logger.warn("Failed to set message status with message model for: {}".format(self.get_message_id()))

    def __retrieve_message_events(self):
        result = self.cirrus_proxy.get_events_for_message(self.get_message_id())
        self.message.add_events(result)

    def __retrieve_message_payloads(self):
        result = self.cirrus_proxy.get_payloads_for_message(self.get_message_id())
        self.message.add_payloads(result)

    def __retrieve_message_metadata(self):
        result = self.cirrus_proxy.get_metadata_for_message(self.get_message_id())
        self.message.add_metadata(result)

    def __retrieve_message_transforms(self):
        search_parameters = get_transform_search_parameters(self.message.rule)
        result = self.cirrus_proxy.get_transforms_for_message(search_parameters)
        self.message.add_transforms(result)

    def get_message_id(self):
        if self.message.message_uid:
            return self.message.message_uid
        # TODO look into other source of msg id should the status not be available
