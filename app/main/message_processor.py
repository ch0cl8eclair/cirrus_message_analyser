import DURATION as DURATION

from config.constants import RULES, FUNCTION, OPTIONS, RULE, TIME, SEARCH_PARAMETERS, START_DATETIME, END_DATETIME, \
    DataType
from config.configuration import ConfigSingleton
from cache_to_disk import delete_old_disk_caches

from formatter.formatter import Formatter
from http.CirrusProxy import CirrusProxy
from utils.utils import error_and_exit, calculate_start_and_end_times_from_duration, get_datetime_now_as_zulu, \
    validate_start_and_end_times


class MessageProcessor:
    """Main class that takes cli arguments and actions them by communicating with Cirrus"""

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.cirrus_proxy = CirrusProxy()
        self.formatter = Formatter()

    def __action_cli_request(self, cli_dict):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on precedence of flags, analyse could be for a single or multiple msgs
        function_to_call = cli_dict.get(FUNCTION)
        options = cli_dict.get(OPTIONS)
        search_parameters = {}

        if function_to_call == "list_rules":
            self.list_rules(options)
        elif function_to_call == "clear_cache":
            self.clear_cache()
        elif function_to_call == "list_messages":
            # validate command line options
            # Ensure we have a rule
            if not RULE in cli_dict:
                error_and_exit("You must specify a rule to inorder to list msgs from Cirrus")
            configured_rule = self.__fetch_rule_config(cli_dict.get(RULE))
            # Ensure configured rule is valid
            if not configured_rule:
                error_and_exit("The specified rule: [] is not found in the rules.json config file, please specify a valid rule name" % cli_dict.get(RULE))
            search_parameters.update(configured_rule.get(SEARCH_PARAMETERS))
            # Choose time over start_datetime and end_datetime, where time is a single duration like day
            # that can be broken down into a start and end time pointer
            if cli_dict.get(TIME):
                try:
                    time_params = calculate_start_and_end_times_from_duration(cli_dict.get(TIME))
                    search_parameters.update(time_params)
                except ValueError as err:
                    error_and_exit(str(err))
            else:
                # handle start and end times
                # if we just have start then set now as end time
                if not START_DATETIME in cli_dict:
                    error_and_exit("Please provide a time window to search ie 1d or given start and end datetime values")
                start_string = cli_dict.get(START_DATETIME)
                if not END_DATETIME:
                    end_string = get_datetime_now_as_zulu()
                else:
                    end_string = cli_dict.get(END_DATETIME)
                time_params = validate_start_and_end_times(start_string, end_string)
                search_parameters.update(time_params)
            self.list_messages(search_parameters, options)
        else:
            pass

    def __fetch_rule_config(self, rule_name):
        """Returns the configured rule matching the supplied name"""
        rules_list = self.configuration.get(RULES)
        for rule in rules_list:
            if rule.name == rule_name:
                return rule
        return None

    def list_messages(self, search_criteria, format_options):
        result = self.cirrus_proxy.search_for_messages(search_criteria)
        self.formatter.format(result, DataType.cirrus_messages, format_options)

    def list_message_payloads(self, options):
        pass

    def list_message_events(self, options):
        pass

    def list_message_metadata(self, options):
        pass

    def list_message_transforms(self, options):
        pass

    def list_rules(self, options):
        rules_list = self.configuration.get(RULES)
        self.formatter.format_config_data(rules_list, options)

    def analyse(self):
        pass

    def clear_cache(self):
        # TODO might have to improve this
        delete_old_disk_caches()