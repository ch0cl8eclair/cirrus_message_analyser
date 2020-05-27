from config.constants import OUTPUT, JSON, CSV, TABLE, DataType, NAME
from tabulate import tabulate
import json


class Formatter:
    def format(self, data_type, data, options):
        if options.get(OUTPUT) == JSON:
            print(json.dump(data))
        elif options.get(OUTPUT) == TABLE:
            self.__get_headings(data_type)
            print(
            tabulate([self.__flatten_data_record(data_type, record) for record in data],
                     self.__get_headings(data_type),
                     tablefmt="github")
            )
        elif options.get(OUTPUT) == CSV:
            print(",".join(self.__get_headings(data_type)))
            for record in data:
                print(",".join(self.__flatten_data_record(data_type, record)))
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
            return [self.__get_field(data, NAME), self.__get_field(data, "search_parameters", "source"), self.__get_field(data, "search_parameters", "destination"),\
            self.__get_field(data, "search_parameters", "type"), self.__get_field(data, "search_parameters", "status")]
        elif data_type == DataType.cirrus_messages:
            [self.__get_field("insertDate"), self.__get_field("id"), self.__get_field("unique-id"), self.__get_field("source"), self.__get_field("destination"), self.__get_field("sub-destination"), self.__get_field("type"), self.__get_field("sub-type"), self.__get_field("parent-id"), self.__get_field("process-id"), self.__get_field("business-id"), self.__get_field("message-status"), self.__get_field("message-date")]
        else:
            pass

    def __get_field(self, data, *fields):
        """Given a data object and a list of fields, will perform the necessary gets to return the final field value"""
        iteration = 0
        for current_field in fields:
            if iteration == 0:
                data_obj = data.get(current_field)
            else:
                data_obj = data_obj.get(current_field)
            iteration = iteration + 1
        return data_obj