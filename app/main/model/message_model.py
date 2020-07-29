import logging
from logging.config import fileConfig

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import UNIQUE_ID, TYPE, SEARCH_PARAMETERS

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
        self.message_uid = None

    def add_rule(self, rule):
        self.rule = rule
        self.has_rule = True

    def add_status(self, status_record):
        self.status_dict = status_record
        self.has_status = True
        self.message_uid = status_record.get(UNIQUE_ID)

    def add_message_uid(self, msg_uid):
        self.message_uid = msg_uid

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
        # filter transforms by message type, and movement search will return movement and movementCancellation
        filter_type = self.__get_msg_type_search_parameter()
        if filter_type:
            original_length = len(transform_data)
            self.transforms_list = [transform for transform in transform_data if transform[TYPE] == filter_type]
            filtered_length = len(self.transforms_list)
            logger.info(f"Filtered transforms list from {original_length} to {filtered_length} for filter type: {filter_type}")
        # Add all transforms if there is no filter defined
        else:
            self.transforms_list = transform_data
        self.has_transforms = True

    def add_search_criteria(self, search_criteria):
        self.search_criteria = search_criteria
        self.has_search_criteria = True

    # def add_message_unique_id(self, message_uid):
    #     """This is only called when the user sets a uid from the cli"""
    #     self.message_uid = message_uid

    def __get_msg_type_search_parameter(self):
        if self.has_rule and self.rule and self.rule.get(SEARCH_PARAMETERS) and TYPE in self.rule.get(SEARCH_PARAMETERS):
            return self.rule.get(SEARCH_PARAMETERS)[TYPE]
        elif self.has_search_criteria:
            return self.search_criteria[TYPE]
        return None

    # def __generate_transform_summary_lists(self):
    #     """Generates the transform stage names as per payloads from the transforms list"""
    #     if not self.has_transforms:
    #         logger.error("No transforms found for message to generate transform steps")
    #         return
    #     summary_list = []
    #     for current_transform in self.transforms_list:
    #         parsing_in = False
    #         summary_list.append(current_transform.get("transform-channel"))
    #         prefix = current_transform.get("transform-name")
    #         if prefix == "IN":
    #             parsing_in = True
    #         for current_step in current_transform.get("transform-steps"):
    #             step_name = current_step.get("transform-step-name")
    #             step_type = current_step.get("transform-step-type")
    #             translated_type = translate_step_type_to_payload_type(step_type)
    #             summary_list.append("{} - {}({})".format(translated_type, prefix, step_name))
    #         if parsing_in:
    #             summary_list.append(ROUTE)
    #     summary_list.append(SEND)
    #     self.transform_summary_stage_names = summary_list
    #
    # def get_transform_stage_names(self):
    #     # TODO need to use getattr
    #     return self.transform_summary_stage_names if self.transform_summary_stage_names else None
