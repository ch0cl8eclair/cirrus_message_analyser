import json
import logging
from logging.config import fileConfig

from tabulate import tabulate

from main.algorithms.empty_fields import FlattenJsonOutputToCSV
from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import OUTPUT, JSON, CSV, TABLE, DataType, NAME, TransformStage, QUIET, \
    YARA_MOVEMENT_POST_JSON_ALGO, HAS_EMPTY_FIELDS_FOR_PAYLOAD, HAS_MANDATORY_FIELDS_FOR_PAYLOAD, \
    TRANSFORM_BACKTRACE_FIELDS

from main.model.model_utils import enrich_message_analysis_status_results, get_algorithm_results_per_message, \
    prefix_message_id_to_lines, get_data_type_for_algorithm, get_algorithm_name_from_data_type
import operator
from functools import reduce

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
        if data_records:
            message_logger.info(tabulate(data_records, headings, tablefmt="github"))
        else:
            logger.warning("No data present to output as table")

    def _xstr(self, value):
        return str(value) if not None else ""

    def _format_data_as_csv(self, data_records, headings):
        message_logger.info(", ".join(headings))
        for record in data_records:
            message_logger.info(", ".join([self._xstr(elem) for elem in record]))

    def _get_headings(self, data_type):
        if data_type == DataType.config_rule:
            return ["Name", "source", "destination", "type", "status"]
        elif data_type == DataType.cirrus_messages:
            return ["insertDate", "id", "unique-id", "source", "destination", "sub-destination", "type", "sub-type", "parent-id", "process-id", "business-id", "message-status", "message-date"]
        elif data_type == DataType.cirrus_payloads:
            return ["tracking-point", "source", "sub-source", "destination", "sub-destination", "type", "subType", "sequence-number", "insertDate"]
        elif data_type == DataType.cirrus_events:
            return ["insertDate", "id", "unique-id", "source-adapter", "event-id", "event-name", "event-date", "event-sucess", "end-point", "sequence-number", "workflow-id"]
        elif data_type in [DataType.analysis_yara_movements, DataType.transform_backtrace_fields]:
            return self._get_dynamic_headings(data_type)
        elif data_type == DataType.empty_fields_for_payload:
            return FlattenJsonOutputToCSV.EMPTY_HEADINGS
        elif data_type == DataType.mandatory_fields_for_payload:
            return FlattenJsonOutputToCSV.MANDATORY_HEADINGS
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

    @staticmethod
    def _get_field(data, fields):
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

    def print_algo_heading(self, algorithm_name, options):
        if not options.get(QUIET):
            message_logger.info(f"Algorithm: {algorithm_name} results:")


class DynamicFormatter(Formatter):
    """Used to output data that did not come from Cirrus, ie non JSON and possibly with dynamic headings"""
    def __init__(self):
        self.algorithm_names = []
        self.custom_algorithm_data_dict = {}

    def set_algorithm_names(self, algo_names_list):
        self.algorithm_names = algo_names_list

    def set_custom_algorithm_data(self, custom_algorithm_data):
        self.custom_algorithm_data_dict = custom_algorithm_data

    def format(self, data_type, data, options):
        if data_type in [DataType.analysis_yara_movements, DataType.empty_fields_for_payload, DataType.mandatory_fields_for_payload, DataType.transform_backtrace_fields]:
            logger.debug("Handling custom algo formatting without flattening data")
            self._format_data_via_conversion(data_type, data, options)
        else:
            self._format_data_via_conversion(data_type, data, options)

    def _get_dynamic_headings(self, data_type):
        if data_type == DataType.analysis_messages:
            headings = ["unique-id", "source", "destination", "type", "parent-id", "process-id", "business-id", "message-status"]
            headings.extend(self.algorithm_names)
            return headings
        elif data_type in [DataType.analysis_yara_movements, DataType.transform_backtrace_fields]:
            algo_name = get_algorithm_name_from_data_type(data_type)
            if algo_name and algo_name in self.custom_algorithm_data_dict:
                headings = []
                headings.extend(self.custom_algorithm_data_dict[algo_name])
                headings.insert(0, "unique-id")
                return headings
        return None

    def _format_data_via_conversion(self, data_type, data, options):
        if options.get(OUTPUT) == JSON:
            headings = self._get_headings(data_type)
            json_data = self.convert_array_to_json(headings, data)
            output_data = json_data
        else:
            output_data = data

        if data_type == DataType.analysis_messages:
            logger.debug("formatting list of message statuses with algorithmic status results")
            # go through this path to add flattening of data
            super().format(data_type, output_data, options)
        else:
            # avoid flattening
            self._format(data_type, output_data, options)

    def convert_array_to_json(self, headings, data_table):
        output_rows = []
        for row in data_table:
            if isinstance(row, dict):
                row_obj = {}
                for k, v in row.items():
                    if k in headings:
                        row_obj[k] = v
                output_rows.append(row_obj)
            elif isinstance(row, list):
                row_obj = {}
                for heading, value in zip(headings, row):
                    row_obj[heading] = value
                output_rows.append(row_obj)
        return output_rows


class AnalysisFormatter:
    """Format out the analysis results, start with msg summary and following with algo custom output"""
    def __init__(self, run_algorithm_names, algorithms_with_data, statistics_map, custom_algorithm_data, format_options):
        self.custom_formatter = DynamicFormatter()
        self.custom_formatter.set_algorithm_names(run_algorithm_names)
        self.algorithms_with_data = algorithms_with_data
        self.statistics_map = statistics_map
        self.format_options = format_options
        self.custom_formatter.set_custom_algorithm_data(custom_algorithm_data)

    def format(self):
        self.custom_formatter.format(DataType.analysis_messages, enrich_message_analysis_status_results(self.statistics_map), self.format_options)
        # Now check for algorithm specific results and print out
        for algorithm_name in self.algorithms_with_data:
            self.__format_algorithm_results(algorithm_name, self.custom_formatter, self.format_options)

    def __format_algorithm_results(self, algorithm_name, custom_formatter, format_options):
        format_data_type = get_data_type_for_algorithm(algorithm_name)
        if algorithm_name in [YARA_MOVEMENT_POST_JSON_ALGO, TRANSFORM_BACKTRACE_FIELDS]:
            custom_formatter.print_algo_heading(algorithm_name, format_options)
            # Next print out the yara algo field matching results across the transform stages
            movements_data_enriched = get_algorithm_results_per_message(self.statistics_map, algorithm_name, prefix_message_id_to_lines)
            movements_data = reduce(operator.concat, movements_data_enriched) if movements_data_enriched else movements_data_enriched
            custom_formatter.format(format_data_type, movements_data, format_options)
        elif algorithm_name in [HAS_EMPTY_FIELDS_FOR_PAYLOAD, HAS_MANDATORY_FIELDS_FOR_PAYLOAD]:
            custom_formatter.print_algo_heading(algorithm_name, format_options)
            field_algo_data_enriched = get_algorithm_results_per_message(self.statistics_map, algorithm_name, prefix_message_id_to_lines)
            # reshape the list to a simple 2d array that can be uniformly formatted out
            flattened_list_of_lines = reduce(operator.concat, field_algo_data_enriched)
            custom_formatter.format(format_data_type, flattened_list_of_lines, format_options)
        else:
            logger.error("Unable to format out algorithm results for : {}, please implement".format(algorithm_name))