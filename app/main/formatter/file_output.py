import datetime
import os.path
from os import path
import logging
from logging.config import fileConfig

from main.config.configuration import get_configuration_dict, ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import OUTPUT_FOLDER, DataType, LOGFILE, TOTAL_COUNT, ERROR_COUNT, HOST, LOG_CORRELATION_ID, \
    ELASTICSEARCH_EXCLUDE_LOG_FILES
from main.utils.utils import write_json_to_file, write_text_to_file

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class FileOutputFormatter:
    def __init__(self):
        self.configuration = ConfigSingleton(get_configuration_dict())
        output_folder_str = self.configuration.get(OUTPUT_FOLDER)
        self.base_output_director = output_folder_str
        if not path.exists(output_folder_str):
            os.mkdir(output_folder_str)

    def setup_message_uid_output_folder(self, message_uid):
        msg_path = os.path.join(self.base_output_director, message_uid)
        if not path.exists(msg_path):
            os.mkdir(msg_path)

    def get_filename_for_datatype(self, datatype):
        if datatype == DataType.config_rule:
            return "config_rule.json"
        elif datatype == DataType.cirrus_messages:
            return "cirrus_message_details.json"
        elif datatype == DataType.cirrus_payloads:
            return "cirrus_message_payloads.json"
        elif datatype == DataType.cirrus_metadata:
            return "cirrus_message_metadata.json"
        elif datatype == DataType.cirrus_events:
            return "cirrus_message_event.json"
        elif datatype == DataType.cirrus_transforms:
            return "cirrus_message_transforms.json"
        elif datatype == DataType.payload_transform_mappings:
            return "payload_transform_mappings.json"
        elif datatype == DataType.host_log_mappings:
            return "host_log_mappings.json"
        elif datatype == DataType.elastic_search_results:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            return f'es-output-uid-{timestamp}.json'
        elif datatype == DataType.elastic_search_results_correlated:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
            return f'es-output-correlated-{timestamp}.json'
        else:
            return None

    def _get_log_output_filename(self, source_log_filename):
        base_log_file_name = os.path.basename(source_log_filename)
        return "{}".format(base_log_file_name)

    def generate_host_log_filename(self, message_uid, hostname, current_log_file, isLog=True):
        base_log_filename = self._get_log_output_filename(current_log_file)
        extention = "log" if isLog else "json"
        prefix = "" if isLog else "es-log-search-"
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

    def output_json_data_to_given_file(self, message_uid, filename, data, data_type=None):
        filepath = os.path.join(*[item for item in [self.base_output_director, message_uid, filename] if item])
        self._output_json_data_to_file(filepath, data_type, data)

    def _output_json_data_to_file(self, filepath, data_type, data):
        if filepath.endswith(".json"):
            pretty_print = False
            if data_type and data_type in [DataType.config_rule, DataType.payload_transform_mappings, DataType.host_log_mappings]:
                pretty_print = True
            write_json_to_file(filepath, data, pretty_print)
        else:
            write_text_to_file(filepath, data)

    def generate_log_statements(self, message_uid, log_lines, statement_type_counts, no_filtering=False):
        for host_name in log_lines:
            if not host_name in statement_type_counts:
                statement_type_counts[host_name] = {}
            for current_log_file in log_lines[host_name]:
                filename = self.generate_host_log_filename(message_uid, host_name, current_log_file, True)
                filepath = os.path.join(self.base_output_director, message_uid, filename)
                abs_path = os.path.abspath(filepath)
                logger.debug("Outputting logging to file: {}".format(abs_path))
                statement_type_counts[host_name][current_log_file] = {}
                with open(filepath, 'w') as outfile:
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
            combined_output = {HOST: host,
                                     LOGFILE: current_logfile,
                                     TOTAL_COUNT: log_level_counts.get(host, {}).get(current_logfile, {}).get(TOTAL_COUNT, 0),
                                     ERROR_COUNT: log_level_counts.get(host, {}).get(current_logfile, {}).get(ERROR_COUNT, 0),
                                     LOG_CORRELATION_ID: ', '.join(host_log_correlation_ids.get(host, {}).get(current_logfile, []))}
            results.append(combined_output)
        return results


def main():
    config = ConfigSingleton(get_configuration_dict())


if __name__ == '__main__':
    main()
