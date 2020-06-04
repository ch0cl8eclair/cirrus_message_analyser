from main.config.constants import OUTPUT, JSON, CSV, TABLE, DataType, NAME
from tabulate import tabulate
import json
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

from main.model.transform_stages import TransformStage

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')
message_logger = logging.getLogger('message')


class Formatter:
    def format(self, data_type, data, options):
        self._format(data_type, data, options, True)

    def _format(self, data_type, data, options, flatten_records=False):
        logger.debug("Attempting to format data for type: {} and output: {}".format(data_type, options.get(OUTPUT)))
        if options.get(OUTPUT) == JSON:
            message_logger.info(json.dumps(data))
        elif options.get(OUTPUT) == TABLE:
            if flatten_records:
                data_records = [self._flatten_data_record(data_type, record) for record in data] if data else []
            else:
                data_records = data if data else []
            self._format_data_as_table(data_records, self._get_headings(data_type))
        elif options.get(OUTPUT) == CSV:
            if data:
                self._format_data_as_csv([self._flatten_data_record(data_type, record) for record in data] if flatten_records else data, self._get_headings(data_type))
            else:
                logger.info("No csv data to output")
        else:
            logger.error("Unknown format option given: {}".format(options.get(OUTPUT)))

    def _format_data_as_table(self, data_records, headings):
        message_logger.info(tabulate(data_records, headings, tablefmt="github"))

    def _format_data_as_csv(self, data_records, headings):
        message_logger.info(", ".join(headings))
        for record in data_records:
            message_logger.info(", ".join([str(elem) for elem in record]))

    def _get_headings(self, data_type):
        if data_type == DataType.config_rule:
            return ["Name", "source", "destination", "type", "status"]
        elif data_type == DataType.cirrus_messages:
            return ["insertDate", "id", "unique-id", "source", "destination", "sub-destination", "type", "sub-type", "parent-id", "process-id", "business-id", "message-status", "message-date"]
        elif data_type == DataType.cirrus_payloads:
            return ["tracking-point", "source", "sub-source", "destination", "sub-destination", "type", "subType", "sequence-number", "insertDate"]
        elif data_type == DataType.cirrus_events:
            return ["insertDate", "id", "unique-id", "source-adapter", "event-id", "event-name", "event-date", "event-sucess", "end-point", "sequence-number", "workflow-id"]
        elif data_type == DataType.analysis_yara_movements:
            headings = [stage.name for stage in TransformStage]
            headings.insert(0, "unique-id")
            return headings
        elif data_type == DataType.analysis_messages:
            return self._get_dynamic_headings(data_type)
        return None

    def _flatten_data_record(self, data_type, data):
        if data_type == DataType.config_rule:
            defined_fields = [[NAME], ["search_parameters", "source"], ["search_parameters", "destination"], ["search_parameters", "type"], ["search_parameters", "message-status"]]
        elif data_type == DataType.cirrus_messages:
            defined_fields = [["insertDate"], ["id"], ["unique-id"], ["source"], ["destination"], ["sub-destination"], ["type"], ["sub-type"], ["parent-id"], ["process-id"], ["business-id"], ["message-status"], ["message-date"]]
        elif data_type == DataType.cirrus_metadata:
            defined_fields = []
        elif data_type == DataType.cirrus_payloads:
            # ,["payload"],["displayPayload"]
            # return [,,["id"],["unique-id"],,,,["compressed"],["content-type"],["content-encoding"],["exception"]]
            defined_fields = [["tracking-point"], ["source"], ["sub-source"], ["destination"], ["sub-destination"], ["type"], ["subType"], ["sequence-number"], ["insertDate"]]
        elif data_type == DataType.cirrus_events:
            defined_fields = [["insertDate"], ["id"], ["unique-id"], ["source-adapter"], ["event-id"], ["event-name"], ["event-date"], ["event-sucess"], ["end-point"], ["sequence-number"], ["workflow-id"]]
        elif data_type == DataType.cirrus_transforms:
            defined_fields = []
        elif data_type == DataType.analysis_messages:
            defined_fields = [[h] for h in self._get_dynamic_headings(data_type)]
        else:
            defined_fields = []
        return self._get_defined_fields_for_datatype(data, defined_fields) if defined_fields else []

    def _get_field(self, data, fields):
        """Given a data object and a list of fields, will perform the necessary gets to return the final field value"""
        iteration = 0
        for current_field in fields:
            if iteration == 0:
                data_obj = data.get(current_field)
            else:
                data_obj = data_obj.get(current_field)
            iteration = iteration + 1
        return data_obj

    def _get_defined_fields_for_datatype(self, data, fields_list):
        return [self._get_field(data, fields_names_tuple) for fields_names_tuple in fields_list]

    def _get_dynamic_headings(self, data_type):
        """To be implemented by subclasses"""
        return []


class DynamicFormatter(Formatter):
    def __init__(self):
        self.algorithm_names = []

    def set_algorithm_names(self, algo_names_list):
        self.algorithm_names = algo_names_list

    def format(self, data_type, data, options):
        # TODO check for JSON output and disable
        if data_type in [DataType.analysis_yara_movements]:
            logger.debug("List of yara message ")
            self._format(data_type, data, options)
        else:
            if data_type == DataType.analysis_messages:
                logger.debug("List of message statuses with algorithmic status results")
            super().format(data_type, data, options)
    #
    # def __flatten_data_with_dynamic_headings(self, data_type, data):
    #     defined_fields = [[h] for h in self.__get_dynamic_headings(data_type)]
    #     return self._get_defined_fields_for_datatype(data, defined_fields)

    def _get_dynamic_headings(self, data_type):
        if data_type == DataType.analysis_messages:
            headings = ["unique-id", "source", "destination", "type", "parent-id", "process-id", "business-id", "message-status"]
            headings.extend(self.algorithm_names)
            return headings

    # def __get_algorithm_names(self, algorithm_result_map):
    #     return list(algorithm_result_map.keys())
    #
    # def __print_algorithm_statuses(self, algorithm_result_map):
    #     return [algorithm_result_map[column_name] for column_name in self.__get_algorithm_names(algorithm_result_map)]