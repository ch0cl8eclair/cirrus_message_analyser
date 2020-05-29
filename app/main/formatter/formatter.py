from main.config.constants import OUTPUT, JSON, CSV, TABLE, DataType, NAME
from tabulate import tabulate
import json
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')
message_logger = logging.getLogger('message')


class Formatter:
    def format(self, data_type, data, options):
        logger.debug("Attempting to format data for type: {} and output: {}".format(data_type, options.get(OUTPUT)))
        if options.get(OUTPUT) == JSON:
            message_logger.info(json.dump(data))
        elif options.get(OUTPUT) == TABLE:
            # self.__get_headings(data_type)
            data_records = [self.__flatten_data_record(data_type, record) for record in data] if data else []
            message_logger.info(tabulate(data_records,
                     self.__get_headings(data_type),
                     tablefmt="github")
            )
        elif options.get(OUTPUT) == CSV:
            message_logger.info(", ".join(self.__get_headings(data_type)))
            if data:
                for record in data:
                    message_logger.info(", ".join(str(elem) for elem in self.__flatten_data_record(data_type, record)))
            else:
                logger.info("No data to output")
        else:
            pass

    def __get_headings(self, data_type):
        if data_type == DataType.config_rule:
            return ["Name", "source", "destination", "type", "status"]
        elif data_type == DataType.cirrus_messages:
            return ["insertDate", "id", "unique-id", "source", "destination", "sub-destination", "type", "sub-type", "parent-id", "process-id", "business-id", "message-status", "message-date"]
        return None

    def __flatten_data_record(self, data_type, data):
        if data_type == DataType.config_rule:
            defined_fields = [[NAME], ["search_parameters", "source"], ["search_parameters", "destination"], ["search_parameters", "type"], ["search_parameters", "status"]]
            return self.__get_defined_fields_for_datatype(data, defined_fields)
        elif data_type == DataType.cirrus_messages:
            defined_fields = [["insertDate"], ["id"], ["unique-id"], ["source"], ["destination"], ["sub-destination"], ["type"], ["sub-type"], ["parent-id"], ["process-id"], ["business-id"], ["message-status"], ["message-date"]]
            return self.__get_defined_fields_for_datatype(data, defined_fields)
        elif data_type == DataType.cirrus_metadata:
            return []
        else:
            return []

    def __get_field(self, data, fields):
        """Given a data object and a list of fields, will perform the necessary gets to return the final field value"""
        iteration = 0
        for current_field in fields:
            if iteration == 0:
                data_obj = data.get(current_field)
            else:
                data_obj = data_obj.get(current_field)
            iteration = iteration + 1
        return data_obj

    def __get_defined_fields_for_datatype(self, data, fields_list):
        return [self.__get_field(data, fields_names_tuple) for fields_names_tuple in fields_list]
