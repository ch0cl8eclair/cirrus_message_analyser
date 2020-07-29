from main.config.constants import MESSAGE_ID, SEARCH_PARAMETERS, TYPE, DESTINATION, SOURCE, DataRequisites

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

from main.model.model_utils import get_transform_search_parameters, InvalidStateException, \
    extract_search_parameters_from_message_detail

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
        if not message_model.has_rule and not message_model.message_uid:
            raise InvalidStateException("Message Enricher requires rule or message uid")
        self.message = message_model
        self.cirrus_proxy = cirrus_proxy

    def retrieve_data(self, prerequisites_data_set):
        """Retrieves the required prereq data for the current msg"""
        for prereq in prerequisites_data_set:
            if prereq == DataRequisites.status and not self.message.has_status:
                # retrieve status data for msg
                self.__retrieve_message_status()
            elif prereq == DataRequisites.events and not self.message.has_events:
                # retrieve events data for msg
                self.__retrieve_message_events()
            elif prereq == DataRequisites.payloads and not self.message.has_payloads:
                # retrieve payloads data for msg
                self.__retrieve_message_payloads()
            elif prereq == DataRequisites.transforms and not self.message.has_transforms:
                # retrieve transforms for msg
                self.__retrieve_message_transforms()
            elif prereq == DataRequisites.metadata and not self.message.has_metadata:
                # retrieve metadata for msg
                self.__retrieve_message_metadata()
            else:
                logger.error("Unsupported data prerequisite item: {}".format(prereq))

    def __retrieve_message_status(self):
        search_criteria = {MESSAGE_ID: self.get_message_id()}
        result = self.cirrus_proxy.search_for_messages(search_criteria)
        if result and isinstance(result, list) and len(result) >= 1:
            self.message.add_status(result[0])
            return
        logger.warning("Failed to set message status with message model for: {}".format(self.get_message_id()))

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
        if self.message.has_rule:
            search_parameters = get_transform_search_parameters(self.message.rule)
        elif self.message.message_uid:
            self.__retrieve_message_by_id()
            # we probably have the search parameters now if the request was successful
            search_parameters = self.message.search_criteria
        if search_parameters:
            result = self.cirrus_proxy.get_transforms_for_message(search_parameters)
            self.message.add_transforms(result)
        else:
            logger.error("Failed to retrieve message transforms as we do not have rule search criteria or message details")

    def __retrieve_message_by_id(self):
        result = None
        # only retrieve if we don't have the data already
        if not self.message.has_message_details:
            result = self.cirrus_proxy.get_message_by_uid(self.get_message_id())
            self.message.add_message_details(result[0] if result and len(result) >= 1 else None)
        # Add in the search criteria if not present
        if not self.message.has_search_criteria:
            msg_details = result if result else [self.message.message_details]
            search_parameters = extract_search_parameters_from_message_detail(msg_details)
            self.message.add_search_criteria(search_parameters)

    def get_message_id(self):
        if self.message.message_uid:
            return self.message.message_uid
        # TODO look into other source of msg id should the status not be available
