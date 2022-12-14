from main.algorithms.payload_transform_mapper import PayloadTransformMapper
from main.config.constants import MESSAGE_ID, SEARCH_PARAMETERS, TYPE, DESTINATION, SOURCE, DataRequisites, \
    ENABLE_ELASTICSEARCH_QUERY, MESSAGE_ID_HEADING, EVENT_DATE_HEADING, ENABLE_ICE_PROXY, MISC_CFG, CONFIG, ELASTIC_CFG

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

from main.http.elk_proxy import ElasticsearchProxy
from main.model.model_utils import get_transform_search_parameters, InvalidStateException, \
    extract_search_parameters_from_message_detail, SuspectedMissingTransformsException
from main.utils.utils import parse_timezone_datetime_str, get_configuration_for_app, unpack_config, switch_app_cfg

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')

METADATA = "metadata"
PAYLOADS = "payloads"
TRANSFORMS = "transforms"
STATUS = "status"
EVENTS = "events"


class MessageEnricher:
    """Given a message model, this class determines which data to retrieve for the message and update the message model with the data"""

    def __init__(self, message_model, cirrus_proxy, merged_app_cfg, ice_proxy=None):
        self.configuration = ConfigSingleton()
        if not message_model.has_rule and not message_model.message_uid:
            raise InvalidStateException("Message Enricher requires rule or message uid")
        self.message = message_model
        self.cirrus_proxy = cirrus_proxy
        self.ice_proxy = ice_proxy
        self.merged_app_cfg = merged_app_cfg
        app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
        enable_elastic_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ENABLE_ELASTICSEARCH_QUERY)
        if bool(enable_elastic_str):
            # switch to specific config for elastic search
            es_merged_cfg = switch_app_cfg(self.configuration, merged_app_cfg, ELASTIC_CFG)
            self.elasticsearch_proxy = ElasticsearchProxy(es_merged_cfg)

    def retrieve_data(self, prerequisites_data_set):
        """Retrieves the required prereq data for the current msg"""
        # If we have a message but not status/details for it then retrieve them
        if self.get_message_id() and not self.has_status:
            self.__retrieve_message_by_id()
        if prerequisites_data_set:
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
        result = self.cirrus_proxy.search_for_messages(search_criteria, self.merged_app_cfg)
        if result and isinstance(result, list) and len(result) >= 1:
            self.message.add_status(result[0])
            return
        logger.warning("Failed to set message status with message model for: {}".format(self.get_message_id()))

    def __retrieve_message_events(self):
        result = self.cirrus_proxy.get_events_for_message(self.get_message_id(), self.merged_app_cfg)
        self.message.add_events(result)

    def __retrieve_message_payloads(self):
        result = self.cirrus_proxy.get_payloads_for_message(self.get_message_id(), self.merged_app_cfg)
        self.message.add_payloads(result)

    def __retrieve_message_metadata(self):
        result = self.cirrus_proxy.get_metadata_for_message(self.get_message_id(), self.merged_app_cfg)
        self.message.add_metadata(result)

    def __retrieve_message_transforms(self):
        # Obtain transform search parameters
        if self.message.has_rule:
            search_parameters = get_transform_search_parameters(self.message.rule)
        elif self.message.message_uid:
            self.__retrieve_message_by_id()
            # we probably have the search parameters now if the request was successful
            search_parameters = self.message.search_criteria
        # Obtain transforms
        if search_parameters:
            result = self.cirrus_proxy.get_transforms_for_message(search_parameters, self.merged_app_cfg)
            # In case we don't get another with a source & destination search, then do separate searches
            if not result:
                result = self.__retrieve_transforms_per_channel()
            self.message.add_transforms(result)
        else:
            logger.error("Failed to retrieve message transforms as we do not have rule search criteria or message details")

    def __retrieve_transforms_per_channel(self):
        logger.warning("Insufficient transforms found for combined transform search, now attempting to search against separate channels")
        search_parameters = self.message.search_criteria
        combined_result = []
        for key in [DESTINATION, SOURCE]:
            temp_search_parameters = dict(search_parameters)
            del temp_search_parameters[key]
            channel_transform_result = self.cirrus_proxy.get_transforms_for_message(temp_search_parameters, self.merged_app_cfg)
            logger.debug("Obtained {} transforms by removing key: {} from search".format(len(channel_transform_result), key))
            if channel_transform_result:
                combined_result.extend(channel_transform_result)
        return combined_result

    def __retrieve_and_update_wider_transforms(self):
        result = self.__retrieve_transforms_per_channel()
        self.message.add_transforms(result)

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

    def add_transform_mappings(self):
        """Adds payload to transform mappings data structure to the message model"""
        mapper = PayloadTransformMapper(self.message.payloads_list, self.message.transforms_list, self.cirrus_proxy)
        try:
            mapper.map()
        except SuspectedMissingTransformsException:
            self.__retrieve_and_update_wider_transforms()
            mapper.reset(self.message.transforms_list)
            try:
                mapper.map()
            except SuspectedMissingTransformsException:
                logger.warning("Failing to retrieve all transforms, please verify payload tracking endpoints against transforms")
        self.message.add_payload_transform_mappings(mapper.get_records())

    def lookup_message_location_on_log_server(self):
        app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
        enable_elastic_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ENABLE_ELASTICSEARCH_QUERY)
        if bool(enable_elastic_str):
            lookup_dict = self.elasticsearch_proxy.lookup_message(self.message.message_uid, self.message.payloads_list)
            self.message.add_server_location(lookup_dict)
        else:
            logger.debug("Elastic search not enable for message search")

    def lookup_ice_message(self, options):
        if self.message.message_region and self.ice_proxy:
            self.ice_proxy.initialise(options)
            failed_details = self.ice_proxy.get_failed_messages_data(self.message.message_region, options)
            for item in failed_details:
                if item[MESSAGE_ID_HEADING] == self.message.message_uid:
                    ice_give_datetime = parse_timezone_datetime_str(item[EVENT_DATE_HEADING])
                    results = self.elasticsearch_proxy.lookup_message_around_supplied_time(item[MESSAGE_ID_HEADING], ice_give_datetime)
                    self.message.add_server_location(results)
                    break
            else:
                logger.error("Failed to find given message uid within ICE failures Dashboard")
        else:
            logger.error("No region given to search for messages within ICE Dashboard")
