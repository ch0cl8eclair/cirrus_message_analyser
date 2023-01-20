import logging
import json
from logging.config import fileConfig

from main.cli.cli_parser import LOKI
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import OPTIONS, TABLE, OUTPUT, QUERY, END_DATETIME, TIME, START_DATETIME, END_DATE, \
    START_DATE, REGION, ENV, DataType, VERBOSE
from main.formatter.formatter import DynamicFormatter
from main.http.loki_proxy import LokiProxy
from main.message_processor import MessageProcessor
from main.utils.utils import error_and_exit, calculate_start_and_end_times_from_duration, get_datetime_now_as_zulu, \
    validate_start_and_end_times, parser_datetime_by_system

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class LokiCommandProcessor:
    """Main class that takes cli arguments and actions them by communicating with Loki"""

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.loki_proxy = LokiProxy()
        self.formatter = DynamicFormatter()

    def action_cli_request(self, cli_dict, merged_app_cfg):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on supplied arguments
        query = cli_dict.get(QUERY, None)
        start_datetime = cli_dict.get(START_DATETIME, None)
        end_datetime = cli_dict.get(END_DATETIME, None)
        time_period = cli_dict.get(TIME, None)
        options = cli_dict.get(OPTIONS)
        # options[OUTPUT] = TABLE

        if not query:
            error_and_exit("Please specific the Loki QL query string!")

        search_parameters = {}
        # add back double quotes as we couldn't use these on the cli
        search_parameters[QUERY] = query.replace("'", '"')
        search_parameters[ENV] = options.get(ENV)
        self.__validate_time_window(cli_dict, search_parameters)

        result = self.loki_proxy.fetch_logs(search_parameters)
        output = self.process_response_data(result, options)
        self.formatter.format(DataType.loki_logs, output, options)

    @staticmethod
    def process_response_data(json_res, options):
        is_verbose = True if options and options[VERBOSE] else False
        output = []
        # jq '.data.result[].values[][1] | fromjson | .log'
        if "data" in json_res:
            data = json_res.get("data")
            if "result" in data:
                res_array = data.get("result")
                if res_array:
                    print(f"{len(res_array)} items in result array")
                    for result_item in res_array:
                        if "values" in result_item:
                            val_array = result_item.get("values")
                            if val_array and len(val_array) >= 2:
                                line_array = []
                                log_statement_obj = json.loads(val_array[1][1])
                                if is_verbose:
                                    line_array.append(log_statement_obj.get("time"))
                                    line_array.append(log_statement_obj.get("pod"))
                                line_array.append(log_statement_obj.get("log"))
                                output.append(line_array)
        return output


    @staticmethod
    def __validate_time_window(cli_dict, search_parameters):
        # Choose time over start_datetime and end_datetime, where time is a single duration like day
        # that can be broken down into a start and end time pointer
        if cli_dict.get(TIME):
            try:
                time_params = calculate_start_and_end_times_from_duration(cli_dict.get(TIME))
                search_parameters.update(time_params)
            except ValueError as err:
                error_and_exit(str(err))
            logger.info("Adding time window to search of start-date: {}, end-date: {}".format(time_params.get(START_DATE), time_params.get(END_DATE)))
        else:
            # if we just have start then set now as end time
            if not START_DATETIME in cli_dict:
                error_and_exit("Please provide a time window to search ie 1d or given start and end datetime values")
            start_string = parser_datetime_by_system(LOKI, cli_dict.get(START_DATETIME))
            end_string = None
            if not END_DATETIME in cli_dict:
                end_string = get_datetime_now_as_zulu()
            else:
                end_string = parser_datetime_by_system(LOKI, cli_dict.get(END_DATETIME))
            time_params = validate_start_and_end_times(start_string, end_string)
            search_parameters.update(time_params)
            logger.info("Adding time window to search of start-date: {}, end-date: {}".format(start_string, end_string))


if __name__ == '__main__':
    print("Test processing of loki response file")
    output_file = open("c:/temp/loki.json")
    json_data = json.load(output_file)
    LokiCommandProcessor.process_response_data(json_data)
    output_file.close()