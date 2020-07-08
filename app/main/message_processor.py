from main.cli.cli_parser import ANALYSE
from main.config.constants import RULES, FUNCTION, OPTIONS, RULE, TIME, SEARCH_PARAMETERS, START_DATETIME, END_DATETIME, \
    DataType, NAME, UID, MSG_UID, MESSAGE_ID, LIMIT, ALGORITHMS, MESSAGE_STATUS, ALGORITHM_STATS, CACHE_REF, \
    YARA_MOVEMENT_POST_JSON_ALGO, HAS_EMPTY_FIELDS_FOR_PAYLOAD, ARGUMENTS, HAS_MANDATORY_FIELDS_FOR_PAYLOAD, \
    TRANSFORM_BACKTRACE_FIELDS

from main.formatter.formatter import Formatter, AnalysisFormatter
from main.http.cirrus_proxy import CirrusProxy, FailedToCommunicateWithCirrus
from main.model.enricher import MessageEnricher
from main.model.message_model import Message
from main.model.model_utils import get_transform_search_parameters, InvalidConfigException
from main.utils.utils import error_and_exit, calculate_start_and_end_times_from_duration, get_datetime_now_as_zulu, \
    validate_start_and_end_times

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig
import importlib


LIST_RULES = "list_rules"
CLEAR_CACHE = "clear-cache"
LIST_MESSAGES = "list_messages"
LIST_MESSAGE_TRANSFORMS = 'list_message_transforms'
LIST_MESSAGE_PAYLOADS = 'list_message_payloads'
LIST_MESSAGE_EVENTS = 'list_message_events'
LIST_MESSAGE_METADATA = "list_message_metadata"

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class MessageProcessor:
    """Main class that takes cli arguments and actions them by communicating with Cirrus"""
    # If user provides uid then map to message-id

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.cirrus_proxy = CirrusProxy()
        self.formatter = Formatter()
        self.statistics_map = {} # Message id indexed
        self.run_algorithm_names = set() # set of all algorithms run
        self.algorithm_name_with_data = set() # set if all algorithms that have their own data run
        self.custom_algorithm_data = {} # Used to hold custom headings and other algorithm items

    def action_cli_request(self, cli_dict):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on precedence of flags, analyse could be for a single or multiple msgs
        function_to_call = cli_dict.get(FUNCTION)
        options = cli_dict.get(OPTIONS)
        search_parameters = {}

        logger.info("Received CLI request for function: {}".format(function_to_call))
        logger.debug("CLI command is: {}".format(str(cli_dict)))
        if function_to_call == LIST_RULES:
            self.list_rules(options)

        elif function_to_call == CLEAR_CACHE:
            self.clear_cache()

        elif function_to_call == LIST_MESSAGES:
            rule_mandatory = True
            # TODO fix how we do a single msg id call
            if UID in cli_dict:
                rule_mandatory = False
                search_parameters[MESSAGE_ID] = cli_dict.get(UID)
            cfg_rule = self.__retrieve_valid_rule(cli_dict, rule_mandatory)
            if cfg_rule:
                search_parameters.update(cfg_rule.get(SEARCH_PARAMETERS))
            # IF we have been provided with a message id then we don't need the time
            if rule_mandatory:
                self.__validate_time_window(cli_dict, search_parameters)
            self.list_messages(search_parameters, options)
            return

        elif function_to_call in [LIST_MESSAGE_METADATA, LIST_MESSAGE_PAYLOADS, LIST_MESSAGE_EVENTS]:
            if UID in cli_dict:
                search_parameters[MSG_UID] = cli_dict.get(UID)
                self.__invoke_func_dynamic(function_to_call, search_parameters, options)
                return
            error_and_exit("You must supply the message unique id when making this request!")

        elif function_to_call == LIST_MESSAGE_TRANSFORMS:
            if UID in cli_dict:
                error_and_exit("Message unique id is not valid for this request!")
            cfg_rule = self.__retrieve_valid_rule(cli_dict)
            search_parameters = get_transform_search_parameters(cfg_rule)
            self.list_message_transforms(search_parameters, options)
            return

        elif function_to_call == ANALYSE:
            if UID in cli_dict:
                search_parameters[MESSAGE_ID] = cli_dict.get(UID)
            limit = -1
            if LIMIT in cli_dict:
                limit = cli_dict.get(LIMIT)
            cfg_rule = self.__retrieve_valid_rule(cli_dict)
            search_parameters.update(cfg_rule.get(SEARCH_PARAMETERS))

            # IF we have been provided with a message id then we don't need the time
            if not MESSAGE_ID in search_parameters:
                self.__validate_time_window(cli_dict, search_parameters)
            self.analyse(search_parameters, cfg_rule, limit, options)
            return

        else:
            logger.error("The given function is not implemented: {}".format(function_to_call))

    def __invoke_func_dynamic(self, function_name, search_parameters, options):
        logger.debug("Dynamically invoking function: {}".format(function_name))
        func = getattr(self, function_name)
        func(search_parameters, options)

    def __fetch_rule_config(self, rule_name):
        """Returns the configured rule matching the supplied name"""
        rules_list = self.configuration.get(RULES)
        for rule in rules_list:
            if rule.get(NAME) == rule_name:
                return rule
        return None

    def list_messages(self, search_criteria, format_options):
        logger.debug("Preparing to list_messages")
        try:
            result = self.cirrus_proxy.search_for_messages(search_criteria)
            record_count = len(result) if result else 0
            logger.info("Obtained {} records from server".format(record_count))
            self.formatter.format(DataType.cirrus_messages, result, format_options)
        except FailedToCommunicateWithCirrus as err:
            error_and_exit(str(err))

    def list_message_transforms(self, search_criteria, format_options):
        logger.debug("Preparing to list_transforms")
        try:
            result = self.cirrus_proxy.get_transforms_for_message(search_criteria)
            record_count = len(result) if result else 0
            logger.info("Obtained {} records from server".format(record_count))
            self.formatter.format(DataType.cirrus_transforms, result, format_options)
        except FailedToCommunicateWithCirrus as err:
            error_and_exit(str(err))

    def list_message_payloads(self, search_criteria, format_options):
        logger.debug("Preparing to list_payloads")
        try:
            result = self.cirrus_proxy.get_payloads_for_message(search_criteria.get(MSG_UID))
            self.formatter.format(DataType.cirrus_payloads, result, format_options)
        except FailedToCommunicateWithCirrus as err:
            error_and_exit(str(err))

    def list_message_events(self, search_criteria, format_options):
        logger.debug("Preparing to list_events")
        try:
            result = self.cirrus_proxy.get_events_for_message(search_criteria.get(MSG_UID))
            self.formatter.format(DataType.cirrus_events, result, format_options)
        except FailedToCommunicateWithCirrus as err:
            error_and_exit(str(err))

    def list_message_metadata(self, search_criteria, format_options):
        logger.debug("Preparing to list_metadata")
        try:
            result = self.cirrus_proxy.get_metadata_for_message(search_criteria.get(MSG_UID))
            self.formatter.format(DataType.cirrus_metadata, result, format_options)
        except FailedToCommunicateWithCirrus as err:
            error_and_exit(str(err))

    def list_rules(self, format_options):
        rules_list = self.configuration.get(RULES)
        self.formatter.format(DataType.config_rule, rules_list, format_options)

    def analyse(self, search_parameters, cfg_rule, limit, format_options):
        """Retrieve msgs from Cirrus and apply algorithms from rule against each, collate results and display"""
        try:
            result = self.cirrus_proxy.search_for_messages(search_parameters)
            if result:
                count = 0
                for current_status in result:
                    if 0 < limit <= count:
                        logger.debug("Limiting msg processing to requested limit of: {}".format(limit))
                        break
                    msg_model = Message()
                    msg_model.add_rule(cfg_rule)
                    msg_model.add_status(current_status)
                    count = count + 1
                    self.__add_message_stats(msg_model)
                    self.__process_algorithms_for_message(msg_model, format_options)
                self.__format_analysis(cfg_rule, format_options)
            else:
                logger.error("Failed to retrieve any messages from search request to analyse")
        except FailedToCommunicateWithCirrus as err:
            error_and_exit("Failed to retrieve messages for analysis command")

    def clear_cache(self):
        self.configuration.get(CACHE_REF).clear()

    # -----------------------------------------------------
    # Utility functions
    # -----------------------------------------------------
    def __retrieve_valid_rule(self, cli_dict, mandatory_rule=True):
        # Ensure we have a rule
        if not RULE in cli_dict and mandatory_rule:
            error_and_exit("You must specify a rule for this request")
        configured_rule = self.__fetch_rule_config(cli_dict.get(RULE))
        # Ensure configured rule is valid
        if not configured_rule and mandatory_rule:
            error_and_exit("The specified rule: {} is not found in the rules.json config file, please specify a valid rule name".format(cli_dict.get(RULE)))
        if configured_rule:
            logger.info("Attempting search with provided rule: {}".format(cli_dict.get(RULE)))
        else:
            logger.debug("No rule provided to search with")
        return configured_rule

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
            logger.info("Adding time window to search of start-date: {}, end-date: {}".format(time_params.get("start-date"), time_params.get("end-date")))
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
            logger.info("Adding time window to search of start-date: {}, end-date: {}".format(start_string, end_string))

    def __add_message_stats(self, msg_model):
        self.statistics_map[msg_model.message_uid] = {MESSAGE_STATUS: msg_model.status_dict}

    def __add_custom_algo_stats(self, msg_model, algorithm_name, algorithm_intance):
        self.algorithm_name_with_data.add(algorithm_name)
        records = algorithm_intance.get_analysis_data()
        # Only add data if we have it
        if records:
            self.statistics_map[msg_model.message_uid][algorithm_name] = records
            if algorithm_name in [YARA_MOVEMENT_POST_JSON_ALGO, TRANSFORM_BACKTRACE_FIELDS]:
                self.custom_algorithm_data[algorithm_name] = algorithm_intance.transform_analyser.processed_transform_stage_names

    def __add_message_algo_stats(self, msg_model, algorithm_results_map):
        self.statistics_map[msg_model.message_uid][ALGORITHM_STATS] = algorithm_results_map

    def __process_algorithms_for_message(self, msg_model, format_options):
        if msg_model and msg_model.has_rule:
            if ALGORITHMS in msg_model.rule and msg_model.rule.get(ALGORITHMS) and isinstance(msg_model.rule.get(ALGORITHMS), list):
                algorithm_results_map = {}
                for current_algorithm_config in msg_model.rule.get(ALGORITHMS):
                    if isinstance(current_algorithm_config, str):
                        # find and instantiate class
                        algorithm_name = current_algorithm_config
                        algorithm_instance = self.instantiate_algorithm_class(algorithm_name, format_options)
                    elif isinstance(current_algorithm_config, dict):
                        algorithm_name = current_algorithm_config[NAME]
                        algorithm_instance = self.instantiate_algorithm_class(current_algorithm_config, format_options)
                    else:
                        raise InvalidConfigException("Algorithms for rules should be defined as a list of string names, or a list of objects")
                    logger.debug("Attempting to process algorithm: {} on current msg: {}".format(algorithm_name, msg_model.message_uid))
                    if algorithm_instance:
                        self.run_algorithm_names.add(algorithm_name)
                        # process prerequisite data
                        data_enricher = self.__get_algorithm_prerequisite_data(msg_model, algorithm_instance)
                        algorithm_instance.set_data_enricher(data_enricher)
                        # Run algorithm
                        algo_success = algorithm_instance.analyse()
                        algorithm_results_map[algorithm_name] = algo_success
                        if algorithm_instance.has_analysis_data():
                            self.__add_custom_algo_stats(msg_model, algorithm_name, algorithm_instance)
                    else:
                        logger.info("The specified algorithm could not be found: {}".format(algorithm_name))
                self.__add_message_algo_stats(msg_model, algorithm_results_map)
            else:
                logger.info("Not algorithms defined to process against message id: {} and rule: {}".format(msg_model.message_uid, msg_model.rule[NAME]))

    def __format_analysis(self, rule, format_options):
        results_formatter = AnalysisFormatter(self.run_algorithm_names, self.algorithm_name_with_data, self.statistics_map, self.custom_algorithm_data, format_options)
        results_formatter.format()

    @staticmethod
    def __get_algorithm_name(algorithm):
        if isinstance(algorithm, str):
            return algorithm
        elif isinstance(algorithm, dict):
            return algorithm[NAME]

    @staticmethod
    def is_non_http_request(cli_dict):
        function_to_call = cli_dict.get(FUNCTION)
        if function_to_call in [LIST_RULES, CLEAR_CACHE]:
            return True
        return False

    def __get_algorithm_prerequisite_data(self, msg_model, algorithm_instance):
        data_set = algorithm_instance.get_data_prerequistites()
        data_enricher = MessageEnricher(msg_model, self.cirrus_proxy)
        if data_set:
            data_enricher.retrieve_data(data_set)
        return data_enricher

    @staticmethod
    def __create_algo_instance(algorithm_name):
        algorithm_module = importlib.import_module("main.algorithms.algorithms")
        AlgoClass = getattr(algorithm_module, algorithm_name)
        algorithm_instance = AlgoClass()
        return algorithm_instance

    @staticmethod
    def instantiate_algorithm_class(algorithm_details, format_options):
        if isinstance(algorithm_details, str):
            return MessageProcessor.__create_algo_instance(algorithm_details)
        elif isinstance(algorithm_details, dict):
            defined_name = algorithm_details[NAME]
            algorithm_instance = MessageProcessor.__create_algo_instance(defined_name)
            if ARGUMENTS in algorithm_details:
                algorithm_instance.set_parameters(algorithm_details[ARGUMENTS], format_options)
            return algorithm_instance

