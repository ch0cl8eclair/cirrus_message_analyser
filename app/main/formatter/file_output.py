import datetime
import os.path
from collections import Generator
from os import path
import logging
from logging.config import fileConfig

from main.config.configuration import get_configuration_dict, ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import OUTPUT_FOLDER, DataType, LOGFILE, TOTAL_COUNT, ERROR_COUNT, HOST, LOG_CORRELATION_ID, \
    ELASTICSEARCH_EXCLUDE_LOG_FILES, output_formats_to_extention_map, MISC_CFG, CONFIG
from main.utils.utils import write_json_to_file, write_text_to_file, write_single_text_to_file, \
    get_configuration_for_app, unpack_config

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class FileOutputFormatter:
    def __init__(self):
        self.configuration = ConfigSingleton(get_configuration_dict())
        app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
        # output_folder_str = self.configuration.get(OUTPUT_FOLDER)
        output_folder_str = unpack_config(app_cfg, MISC_CFG, CONFIG, OUTPUT_FOLDER)
        self.base_output_directory = output_folder_str
        if not path.exists(output_folder_str):
            os.mkdir(output_folder_str)

    def setup_message_uid_output_folder(self, message_uid):
        msg_path = os.path.join(self.base_output_directory, message_uid)
        if not path.exists(msg_path):
            os.mkdir(msg_path)

    def get_filename_for_datatype(self, datatype, output_format=None):
        extention = output_formats_to_extention_map[output_format] if output_format else ".json"

        if datatype == DataType.config_rule:
            file_name = "config_rule{}"
        elif datatype == DataType.cirrus_messages:
            file_name = "cirrus_message_details{}"
        elif datatype == DataType.cirrus_payloads:
            file_name = "cirrus_message_payloads{}"
        elif datatype == DataType.cirrus_metadata:
            file_name = "cirrus_message_metadata{}"
        elif datatype == DataType.cirrus_events:
            file_name = "cirrus_message_event{}"
        elif datatype == DataType.cirrus_transforms:
            file_name = "cirrus_message_transforms{}"
        elif datatype == DataType.payload_transform_mappings:
            file_name = "payload_transform_mappings{}"
        elif datatype == DataType.cirrus_transforms_steps:
            file_name = "payload_transform_steps{}"
        elif datatype == DataType.host_log_mappings:
            file_name = "host_log_mappings{}"
        elif datatype == DataType.elastic_search_results:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            file_name = f'es-output-uid-{timestamp}' + "{}"
        elif datatype == DataType.elastic_search_results_correlated:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            file_name = f'es-output-correlated-{timestamp}' + "{}"
        else:
            return None
        return file_name.format(extention)

    def _get_log_output_filename(self, source_log_filename):
        base_log_file_name = os.path.basename(source_log_filename)
        return "{}".format(base_log_file_name)

    def generate_host_log_filename(self, message_uid, hostname, current_log_file, is_log=True):
        base_log_filename = self._get_log_output_filename(current_log_file)
        extention = "log" if is_log else "json"
        prefix = "" if is_log else "es-log-search-"
        filename = "{}{}-{}.{}".format(prefix, hostname.replace('.', '-'), base_log_filename, extention)
        self.setup_message_uid_output_folder(message_uid)
        return filename

    def output_json_data_to_file(self, message_uid, data_type, data):
        self.setup_message_uid_output_folder(message_uid)
        filename = self.get_filename_for_datatype(data_type)
        if filename:
            self.output_json_data_to_given_file(message_uid, filename, data, data_type)
        else:
            logger.error("Failed to map datatype:{} to filename for output".format(str(data_type)))

    def _get_file_path_from_components(self, message_uid, filename):
        filepath = os.path.join(*[item for item in [self.base_output_directory, message_uid, filename] if item])
        return filepath

    def output_json_data_to_given_file(self, message_uid, filename, data, data_type=None):
        filepath = self._get_file_path_from_components(message_uid, filename)
        self._output_json_data_to_file(filepath, data_type, data)

    def _output_json_data_to_file(self, filepath, data_type, data):
        if filepath.endswith(".json"):
            pretty_print = False
            if data_type and data_type in [DataType.config_rule, DataType.payload_transform_mappings, DataType.cirrus_transforms_steps, DataType.host_log_mappings, DataType.cirrus_messages]:
                pretty_print = True
            write_json_to_file(filepath, data, pretty_print)
        else:
            write_text_to_file(filepath, data)

    def output_text_to_file(self, message_uid, base_filename, text, file_type="xls"):
        filepath = self._get_filepath_output(message_uid, base_filename, file_type)
        write_single_text_to_file(filepath, text)

    def _get_filepath_output(self, message_uid, filename, data_type_log_str):
        filepath = self._get_file_path_from_components(message_uid, filename)
        self.setup_message_uid_output_folder(message_uid)
        abs_path = os.path.abspath(filepath)
        logger.debug("Outputting {} data to file: {}".format(data_type_log_str, abs_path))
        return filepath

    def output_logging_to_file(self, message_uid, data_type, data, output_format):
        filename = self.get_filename_for_datatype(data_type, output_format)
        if not filename:
            logger.error("Failed to get filename for type: {}".format(data_type.name))
        filepath = self._get_filepath_output(message_uid, filename, data_type.name)
        # determine type: text or generator
        if data:
            if isinstance(data, Generator):
                write_text_to_file(filepath, data)
            elif isinstance(data, str):
                write_single_text_to_file(filepath, data)
            elif isinstance(data, list) or isinstance(data, dict):
                write_json_to_file(filepath, data)
                self._output_json_data_to_file(filepath, data_type, data)
            else:
                logger.warning("Unknown datatype passed for file-output, ignoring")

    def generate_log_statements(self, message_uid, log_lines, statement_type_counts, no_filtering=False):
        for host_name in log_lines:
            if not host_name in statement_type_counts:
                statement_type_counts[host_name] = {}
            for current_log_file in log_lines[host_name]:
                filename = self.generate_host_log_filename(message_uid, host_name, current_log_file, True)
                filepath = os.path.join(self.base_output_directory, message_uid, filename)
                abs_path = os.path.abspath(filepath)
                logger.debug("Outputting logging to file: {}".format(abs_path))
                statement_type_counts[host_name][current_log_file] = {}
                with open(filepath, 'w', encoding="utf-8") as outfile:
                    for line in sorted(log_lines[host_name][current_log_file], key = lambda i: i.get('_source', {}).get("@timestamp", "")):
                        if line["_source"]["source"] == current_log_file or no_filtering:
                            level = line['_source'].get('level', '')
                            self.upgrade_level_count(statement_type_counts, host_name, current_log_file, level)
                            outfile.write("{} {} {}\n".format(line['_source'].get('@timestamp', ''), level, line['_source'].get('message', '')))
        return statement_type_counts

    def upgrade_level_count(self, statement_type_counts, current_hostname, current_log_file, level):
        statement_type_counts[current_hostname][current_log_file][TOTAL_COUNT] = statement_type_counts[current_hostname][current_log_file].get(TOTAL_COUNT, 0) + 1
        if level == "ERROR":
            statement_type_counts[current_hostname][current_log_file][ERROR_COUNT] = statement_type_counts[current_hostname][current_log_file].get(ERROR_COUNT, 0) + 1

    def enrich_log_summary_data(self, host_log_correlation_ids, server_locations, log_level_counts):
        results = []
        exclude_logs = self.configuration.get(ELASTICSEARCH_EXCLUDE_LOG_FILES)
        for server_array_item in sorted(server_locations, key = lambda i: i[HOST]):
            host = server_array_item[HOST]
            current_logfile = server_array_item[LOGFILE]
            if exclude_logs and current_logfile in exclude_logs:
                continue
            # Given that we search es using a set, we should use a set for results output also
            unique_correlation_ids = set(host_log_correlation_ids.get(host, {}).get(current_logfile, []))
            combined_output = {HOST: host,
                                     LOGFILE: current_logfile,
                                     TOTAL_COUNT: log_level_counts.get(host, {}).get(current_logfile, {}).get(TOTAL_COUNT, 0),
                                     ERROR_COUNT: log_level_counts.get(host, {}).get(current_logfile, {}).get(ERROR_COUNT, 0),
                                     LOG_CORRELATION_ID: ', '.join(unique_correlation_ids)}
            results.append(combined_output)
        return results


def main():
    config = ConfigSingleton(get_configuration_dict())


if __name__ == '__main__':
    main()
