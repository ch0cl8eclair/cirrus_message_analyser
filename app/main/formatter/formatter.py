import json
import logging
import operator
from functools import reduce
from logging.config import fileConfig

from tabulate import tabulate

from main.algorithms.empty_fields import FlattenJsonOutputToCSV
from main.algorithms.payload_transform_mapper import PayloadTransformMapper
from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import OUTPUT, JSON, DataType, NAME, QUIET, \
    YARA_MOVEMENT_POST_JSON_ALGO, HAS_EMPTY_FIELDS_FOR_PAYLOAD, HAS_MANDATORY_FIELDS_FOR_PAYLOAD, \
    TRANSFORM_BACKTRACE_FIELDS, HOST, LOGFILE, LEVEL, LOG_CORRELATION_ID, LINE, \
    TIME, TOTAL_COUNT, ERROR_COUNT, \
    OutputFormat, SYSTEM
from main.model.model_utils import enrich_message_analysis_status_results, get_algorithm_results_per_message, \
    prefix_message_id_to_lines, get_data_type_for_algorithm, get_algorithm_name_from_data_type
from main.utils.utils import convert_output_option_to_enum, convert_timestamp_to_datetime_str

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')
message_logger = logging.getLogger('message')


class Formatter:
    """Formats out collected data to the specified output format: JSON|CSV|TABLE"""

    def format(self, data_type, data, options):
        self._format(data_type, data, options, True)

    def _format(self, data_type, data, options, flatten_records=False):
        output_type = convert_output_option_to_enum(options)
        if data:
            logger.debug("Attempting to format data for type: {} and output: {}".format(data_type, output_type.name))
        else:
            logger.warning("No data to output for type: {}".format(output_type.name))
            return
        data_records = self._get_processed_data_for_output(data, data_type, output_type, flatten_records)
        if output_type == OutputFormat.json:
            self._format_to_json(data_records)
        elif output_type == OutputFormat.table:
            self._format_to_table(data_records, self._get_headings(data_type))
        elif output_type == OutputFormat.csv:
            self._format_to_csv(data_records, self._get_headings(data_type))

    def _format_to_json(self, data_records):
        message_logger.info(json.dumps(data_records))

    def _format_to_table(self, data_records, headings):
        message_logger.info(self._create_table_data_str(data_records, headings))

    def _format_to_csv(self, data_records, headings):
        csv_gen = self._csv_data_generator(data_records, headings)
        for log_line in csv_gen:
            message_logger.info(log_line)

    ### #######################################################################
    ### Utility methods
    ### #######################################################################

    def _get_processed_data_for_output(self, data, data_type, output_type, flatten_records):
        if output_type == OutputFormat.table:
            if flatten_records:
                return (self._flatten_data_record(data_type, record) for record in data)
        elif output_type == OutputFormat.csv:
            if flatten_records:
                return (self._flatten_data_record(data_type, record) for record in data)
        return data

    def get_processed_data_for_file_output(self, data, data_type, options, flatten_records=True):
        output_type = convert_output_option_to_enum(options)
        data_records = self._get_processed_data_for_output(data, data_type, output_type, flatten_records)
        if output_type == OutputFormat.table:
            return self._create_table_data_str(data_records, self._get_headings(data_type))
        elif output_type == OutputFormat.csv:
            return self._csv_data_generator(data_records, self._get_headings(data_type))
        return data_records

    def _create_table_data_str(self, data_records, headings):
        return tabulate(data_records, headings, tablefmt="pretty")

    def _xstr(self, value):
        return str(value) if not None else ""

    def _csv_data_generator(self, data_records, headings):
        yield ", ".join(headings)
        for record in data_records:
            yield ", ".join([self._xstr(elem) for elem in record])

    def _get_headings(self, data_type):
        """Gives the list of headings per data type"""
        if data_type == DataType.config_rule:
            return ["Name", "system", "source", "destination", "type", "status"]
        elif data_type == DataType.cirrus_messages:
            return ["insertDate", "id", "unique-id", "source", "destination", "sub-destination", "type", "sub-type", "parent-id", "process-id", "business-id", "message-status", "message-date"]
        elif data_type == DataType.cirrus_payloads:
            return ["tracking-point", "source", "sub-source", "destination", "sub-destination", "type", "subType", "sequence-number", "insertDate"]
        elif data_type == DataType.cirrus_events:
            return ["insertDate", "id", "unique-id", "source-adapter", "event-id", "event-name", "event-date", "event-sucess", "end-point", "sequence-number", "workflow-id"]
        elif data_type == DataType.cirrus_transforms:
            return ["insertDate", "id", "transform-name", "transform-channel", "source", "destination", "type", "comment", "split-result", "split-result-xpath", "next-destination", "generate-new-message-id"]
        elif data_type == DataType.cirrus_transforms_steps:
            return ["transform-name", "transform-channel", "id", "transform-step-name", "transform-order", "url", "transform-step-type", "comment"]
        elif data_type == DataType.cirrus_metadata:
            return None # TODO need to find a metadata example
        elif data_type in [DataType.analysis_yara_movements, DataType.transform_backtrace_fields]:
            return self._get_dynamic_headings(data_type)
        elif data_type == DataType.empty_fields_for_payload:
            return FlattenJsonOutputToCSV.EMPTY_HEADINGS
        elif data_type == DataType.mandatory_fields_for_payload:
            return FlattenJsonOutputToCSV.MANDATORY_HEADINGS
        elif data_type == DataType.analysis_messages:
            return self._get_dynamic_headings(data_type)
        elif data_type == DataType.payload_transform_mappings:
            return PayloadTransformMapper.HEADINGS
        elif data_type == DataType.host_log_mappings:
            return [HOST, LOGFILE, TOTAL_COUNT, ERROR_COUNT, LOG_CORRELATION_ID]
        elif data_type == DataType.log_statements:
            return [TIME, LEVEL, LINE]
        if data_type == DataType.ice_failed_messages:
            return ['Event Date', 'Message ID', 'Adapter ID', 'Service Details', 'Source', 'Destination', 'Message Type', 'Region', 'Delete']
        if data_type == DataType.ice_dashboard:
            return ['Community', 'In Progress Messages', 'Failed Event Messages', 'Heartbeat Failures', 'CALM Alerts']
        return None

    def _flatten_data_record(self, data_type, data):
        """Used to screen out less useful column data from dataset, also flattens out nested structures"""
        if data_type == DataType.config_rule:
            defined_fields = [[NAME], [SYSTEM], ["search_parameters", "source"], ["search_parameters", "destination"], ["search_parameters", "type"], ["search_parameters", "message-status"]]
        elif data_type == DataType.cirrus_messages:
            defined_fields = [["insertDate"], ["id"], ["unique-id"], ["source"], ["destination"], ["sub-destination"], ["type"], ["sub-type"], ["parent-id"], ["process-id"], ["business-id"], ["message-status"], ["message-date"]]
        elif data_type == DataType.cirrus_metadata:
            defined_fields = [] # TODO need to find a metadata example
        elif data_type == DataType.cirrus_payloads:
            defined_fields = [["tracking-point"], ["source"], ["sub-source"], ["destination"], ["sub-destination"], ["type"], ["subType"], ["sequence-number"], ["insertDate"]]
        elif data_type == DataType.cirrus_events:
            defined_fields = [["insertDate"], ["id"], ["unique-id"], ["source-adapter"], ["event-id"], ["event-name"], ["event-date"], ["event-sucess"], ["end-point"], ["sequence-number"], ["workflow-id"]]
        elif data_type == DataType.cirrus_transforms:
            defined_fields = [["insertDate"], ["id"], ["transform-name"], ["transform-channel"], ["source"], ["destination"], ["type"], ["comment"], ["split-result"], ["split-result-xpath"], ["next-destination"], ["generate-new-message-id"]]
        elif data_type == DataType.cirrus_transforms_steps:
            defined_fields = [[heading] for heading in self._get_headings(data_type)]
        elif data_type == DataType.analysis_messages:
            defined_fields = [[h] for h in self._get_dynamic_headings(data_type)]
        elif data_type == DataType.payload_transform_mappings:
            defined_fields = [[heading] for heading in self._get_headings(data_type)]
        elif data_type == DataType.host_log_mappings:
            defined_fields = [[heading] for heading in self._get_headings(data_type)]
        elif data_type == DataType.log_statements:
            defined_fields = [[heading] for heading in self._get_headings(data_type)]
        elif data_type == DataType.ice_failed_messages:
            defined_fields = [[heading] for heading in self._get_headings(data_type)]
        elif data_type == DataType.ice_dashboard:
            defined_fields = [[heading] for heading in self._get_headings(data_type)]
        else:
            defined_fields = []
        return self._get_defined_fields_for_datatype(data, defined_fields, self._get_translated_date_fields(data_type)) if defined_fields else []

    def _get_translated_date_fields(self, data_type):
        if data_type == DataType.cirrus_payloads:
            return ["insertDate"]
        elif data_type == DataType.cirrus_events:
            return ["insertDate"]
        elif data_type == DataType.cirrus_transforms:
            return ["insertDate"]
        elif data_type == DataType.cirrus_messages:
            return ["insertDate", "message-date"]
        return None

    @staticmethod
    def _get_field(data, fields, translatable_date_fields_list=None):
        """Given a data object and a list of fields, will perform the necessary gets to return the final field value"""
        iteration = 0
        for current_field in fields:
            if iteration == 0:
                data_obj = data.get(current_field, "")
            else:
                data_obj = data_obj.get(current_field, "")
            iteration = iteration + 1
        # Do we have data, check the last field obtained is a date and format it out
        if translatable_date_fields_list and data_obj and current_field and current_field in translatable_date_fields_list:
            return convert_timestamp_to_datetime_str(data_obj)
        return data_obj

    def _get_defined_fields_for_datatype(self, data, fields_list, translatable_date_fields_list):
        return [self._get_field(data, fields_names_tuple, translatable_date_fields_list) for fields_names_tuple in fields_list]

    def _get_dynamic_headings(self, data_type):
        """To be implemented by subclasses"""
        return []

    def print_algo_heading(self, algorithm_name, options):
        if not options.get(QUIET):
            message_logger.info(f"Algorithm: {algorithm_name} results:")

### #######################################################################
### Subclasses
### #######################################################################


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
        elif data_type in [DataType.adm_locations, DataType.adm_configs, DataType.adm_versions, DataType.adm_scripts, DataType.adm_artifacts]:
            logger.debug("formatting list of adm data")
            if data:
                headings = data.pop(0)
                super()._format_to_table(data, headings)
            else:
                logger.warning("no data to output for type: {}".format(data_type))
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