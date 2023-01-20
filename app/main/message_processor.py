import importlib
import logging
import sys
from logging.config import fileConfig

from main.cli.cli_parser import ANALYSE, DETAIL, GET_LOGS, WEBPACK
from main.config.configuration import ConfigSingleton
from main.config.constants import RULES, FUNCTION, OPTIONS, RULE, TIME, SEARCH_PARAMETERS, START_DATETIME, END_DATETIME, \
    DataType, NAME, UID, MSG_UID, MESSAGE_ID, LIMIT, ALGORITHMS, MESSAGE_STATUS, ALGORITHM_STATS, CACHE_REF, \
    YARA_MOVEMENT_POST_JSON_ALGO, ARGUMENTS, TRANSFORM_BACKTRACE_FIELDS, DataRequisites, FILE, OUTPUT, START_DATE, \
    END_DATE, CIRRUS, \
    SYSTEM, ICE, ENABLE_ELASTICSEARCH_QUERY, REGION, ENABLE_ICE_PROXY, LOG_STATEMENT_FOUND, VERBOSE, MISC_CFG, CONFIG, \
    ELASTIC_CFG
from main.formatter.dual_formatter import LogAndFileFormatter
from main.formatter.file_output import FileOutputFormatter
from main.formatter.formatter import Formatter, AnalysisFormatter
from main.http.cirrus_proxy import CirrusProxy
from main.http.elk_proxy import ElasticsearchProxy
from main.http.ice_proxy import ICEProxy
from main.http.proxy_cache import FailedToCommunicateWithSystem
from main.model.enricher import MessageEnricher
from main.model.message_model import Message
from main.model.model_utils import get_transform_search_parameters, InvalidConfigException, InvalidStateException
from main.utils.utils import error_and_exit, calculate_start_and_end_times_from_duration, get_datetime_now_as_zulu, \
    validate_start_and_end_times, parse_datetime_str, parse_timezone_datetime_str, \
    format_datetime_to_zulu, generate_webpack, get_configuration_for_app, unpack_config, get_merged_app_cfg, \
    parser_datetime_by_system

LIST_RULES = "list_rules"
CLEAR_CACHE = "clear-cache"
LIST_MESSAGES = "list_messages"
LIST_MESSAGE_TRANSFORMS = 'list_message_transforms'
LIST_MESSAGE_PAYLOADS = 'list_message_payloads'
LIST_MESSAGE_EVENTS = 'list_message_events'
LIST_MESSAGE_METADATA = "list_message_metadata"

import os
LOGGING_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../resources/logging_config.ini')
fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class MessageProcessor:
    """Main class that takes cli arguments and actions them by communicating with Cirrus"""
    # If user provides uid then map to message-id

    def __init__(self, options):
        self.configuration = ConfigSingleton()
        self.cirrus_proxy = CirrusProxy()
        self.ice_proxy = ICEProxy()
        self.formatter = Formatter()
        self.statistics_map = {} # Message id indexed
        self.run_algorithm_names = set() # set of all algorithms run
        self.algorithm_name_with_data = set() # set if all algorithms that have their own data run
        self.custom_algorithm_data = {} # Used to hold custom headings and other algorithm items
        file_generator = FileOutputFormatter()
        self.details_formatter = LogAndFileFormatter(self.formatter, file_generator, self.cirrus_proxy)

        app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
        enable_elastic_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ENABLE_ELASTICSEARCH_QUERY)
        if bool(enable_elastic_str):
            merged_app_cfg = get_merged_app_cfg(self.configuration, ELASTIC_CFG, options)
            self.elasticsearch_proxy = ElasticsearchProxy(merged_app_cfg)

    def action_cli_request(self, cli_dict, merged_app_cfg):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on precedence of flags, analyse could be for a single or multiple msgs
        function_to_call = cli_dict.get(FUNCTION)
        options = cli_dict.get(OPTIONS)
        search_parameters = {}

        if options.get(OUTPUT) == FILE and function_to_call != DETAIL:
            error_and_exit("The file output option is current only valid with the details command!")

        logger.info("Received CLI request for function: {}".format(function_to_call))
        logger.debug("CLI command is: {}".format(str(cli_dict)))
        if function_to_call == LIST_RULES:
            self._get_data_for_message(DataType.config_rule, search_parameters, merged_app_cfg)

        elif function_to_call == CLEAR_CACHE:
            self.clear_cache()

        elif function_to_call == LIST_MESSAGES:
            rule_mandatory = True

            if UID in cli_dict:
                rule_mandatory = False
                search_parameters[MESSAGE_ID] = cli_dict.get(UID)
                msg_model = Message()
                msg_model.add_message_uid(cli_dict.get(UID))
                data_enricher = MessageEnricher(msg_model, self.cirrus_proxy, merged_app_cfg)
                data_enricher.retrieve_data(None)
                self.formatter.format(DataType.cirrus_messages, msg_model.message_details, options)
                return

            system_to_contact = CIRRUS.upper()
            cfg_rule = self.__retrieve_valid_rule(cli_dict, rule_mandatory)
            if cfg_rule:
                search_parameters.update(cfg_rule.get(SEARCH_PARAMETERS))
                system_to_contact = cfg_rule.get(SYSTEM, CIRRUS.upper())
                # Override configured region with that of the cli
                search_parameters[REGION] = options.get(REGION)
            if system_to_contact.upper() == ICE.upper():
                # Override configured region with that of the cli
                search_parameters[REGION] = options.get(REGION)
                self._list_messages(DataType.ice_failed_messages, search_parameters, options, merged_app_cfg)
            else:
                # IF we have been provided with a message id then we don't need the time
                if rule_mandatory:
                    self.__validate_time_window(cli_dict, search_parameters)
                self._list_messages(DataType.cirrus_messages, search_parameters, options, merged_app_cfg)
            return

        elif function_to_call in [LIST_MESSAGE_METADATA, LIST_MESSAGE_PAYLOADS, LIST_MESSAGE_EVENTS]:
            function_to_datatype_map = {LIST_MESSAGE_METADATA: DataType.cirrus_metadata, LIST_MESSAGE_PAYLOADS: DataType.cirrus_payloads, LIST_MESSAGE_EVENTS: DataType.cirrus_events}
            if UID in cli_dict:
                search_parameters[MSG_UID] = cli_dict.get(UID)
                self._get_data_for_message(function_to_datatype_map[function_to_call], search_parameters, options)
                return
            error_and_exit("You must supply the message unique id when making this request!")

        elif function_to_call == LIST_MESSAGE_TRANSFORMS:
            if UID in cli_dict:
                error_and_exit("Message unique id is not valid for this request!")
            cfg_rule = self.__retrieve_valid_rule(cli_dict)

            search_parameters = get_transform_search_parameters(cfg_rule)
            self._get_data_for_message(DataType.cirrus_transforms, search_parameters, options)
            return

        elif function_to_call == DETAIL:
            if UID not in cli_dict:
                error_and_exit("Message unique id must be provided for this request")
            target_system = cli_dict.get(SYSTEM) if SYSTEM in cli_dict else None
            ice_region = options.get(REGION)
            # ice_region = cli_dict.get(REGION) if REGION in cli_dict else None

            msg_model = Message()
            msg_model.add_message_uid(cli_dict.get(UID))

            if not target_system or target_system == "CIRRUS":
                self.detail_cirrus_message(msg_model, options, merged_app_cfg)
            elif target_system == "ICE":
                app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
                enable_elastic_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ENABLE_ICE_PROXY)

                if not bool(enable_elastic_str):
                    error_and_exit("Please enable and configure ICE within the configuration")
                if not ice_region:
                    error_and_exit("Unable to process detail command, you must specify the region associated with the ice message")
                # msg_model.add_message_region(cli_dict.get(REGION))
                msg_model.add_message_region(options.get(REGION))
                self.detail_ice_message(msg_model, options, merged_app_cfg)
            else:
                error_and_exit("Unable to process detail command, target system unknown: {}".format(target_system))
            return

        elif function_to_call == GET_LOGS:
            if UID not in cli_dict:
                error_and_exit("Message unique id must be provided for this request")
            app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
            enable_elastic_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ENABLE_ELASTICSEARCH_QUERY)
            if not bool(enable_elastic_str):
                error_and_exit("Please enable enable_elasticsearch_query flag and set parameters in config")
            message_uid = cli_dict.get(UID)
            self.__validate_time_window(cli_dict, search_parameters)
            log_details = self.elasticsearch_proxy.lookup_message_within_supplied_time_window(message_uid, search_parameters.get(START_DATE, None), search_parameters.get(END_DATE, None))
            self.details_formatter.format_server_log_details(message_uid, log_details, options)
            return

        elif function_to_call == WEBPACK:
            if UID not in cli_dict:
                error_and_exit("Message unique id must be provided for this request")
            app_cfg = get_configuration_for_app(self.configuration, MISC_CFG, "*", "*")
            enable_elastic_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ENABLE_ELASTICSEARCH_QUERY)
            if not bool(enable_elastic_str):
                error_and_exit("Please enable enable_elasticsearch_query flag and set parameters in config")
            message_uid = cli_dict.get(UID)
            if not START_DATETIME in cli_dict:
                error_and_exit("Please provide a start date time for this request")
            self.__validate_time_window(cli_dict, search_parameters)
            # Do we have two dates?
            if search_parameters.get(END_DATE, None):
                log_details = self.elasticsearch_proxy.lookup_message_within_supplied_time_window(message_uid, search_parameters.get(START_DATE, None), search_parameters.get(END_DATE, None))
            # Do we have a single date?
            else:
                dt = parse_datetime_str(search_parameters.get(START_DATE, None))
                log_details = self.elasticsearch_proxy.lookup_message_around_supplied_time(message_uid, dt)

            if not log_details or not LOG_STATEMENT_FOUND in log_details or not bool(log_details.get(LOG_STATEMENT_FOUND, False)):
                print(f"No log details found for given message uid: {message_uid}", file=sys.stderr)
            else:
                self.details_formatter.format_server_log_details(message_uid, log_details, options)
                generated_file = generate_webpack(self.configuration, message_uid)
                logger.info("Generated the following webpack file: {}".format(generated_file))
                print(f"log details found for message uid: {message_uid}, webpage file generated to: {generated_file}", file=sys.stdout)
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
            self.analyse(search_parameters, cfg_rule, limit, options, merged_app_cfg)
            return

        else:
            logger.error("The given function is not implemented: {}".format(function_to_call))

    def detail_cirrus_message(self, msg_model, options, merged_app_cfg):
        data_enricher = MessageEnricher(msg_model, self.cirrus_proxy, merged_app_cfg)
        data_fetch_set = frozenset([DataRequisites.payloads, DataRequisites.transforms])
        data_enricher.retrieve_data(data_fetch_set)
        data_enricher.add_transform_mappings()
        data_enricher.lookup_message_location_on_log_server()
        self.details_formatter.format_message_model(msg_model, options)

    def detail_ice_message(self, msg_model, options, merged_app_cfg):
        data_enricher = MessageEnricher(msg_model, self.cirrus_proxy, merged_app_cfg, self.ice_proxy)
        data_enricher.lookup_ice_message(options)
        self.details_formatter.format_message_model(msg_model, options)

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

    def _get_data_for_message(self, data_type, search_criteria, format_options, merged_app_cfg):
        logger.debug("Preparing to get data for {}".format(data_type))
        try:
            if data_type == DataType.cirrus_messages:
                result = self.cirrus_proxy.search_for_messages(search_criteria, merged_app_cfg)
            elif data_type == DataType.cirrus_transforms:
                result = self.cirrus_proxy.get_transforms_for_message(search_criteria, merged_app_cfg)
            elif data_type == DataType.cirrus_payloads:
                result = self.cirrus_proxy.get_payloads_for_message(search_criteria.get(MSG_UID), merged_app_cfg)
            elif data_type == DataType.cirrus_events:
                result = self.cirrus_proxy.get_events_for_message(search_criteria.get(MSG_UID), merged_app_cfg)
            elif data_type == DataType.cirrus_metadata:
                result = self.cirrus_proxy.get_metadata_for_message(search_criteria.get(MSG_UID), merged_app_cfg)
            elif data_type == DataType.config_rule:
                result = self.configuration.get(RULES)
            elif data_type == DataType.ice_failed_messages:
                self.ice_proxy.initialise(merged_app_cfg)
                result = self.ice_proxy.list_messages(search_criteria, merged_app_cfg)
            else:
                raise InvalidStateException("Unknown data type passed to retrieve message data for")
        except FailedToCommunicateWithSystem as err:
            error_and_exit(str(err))
        record_count = len(result) if result else 0
        logger.debug("Obtained {} records from server".format(record_count))
        self.formatter.format(data_type, result, format_options)
        if format_options[VERBOSE]:
            data = self.formatter.format_transform_sub_lists(result, format_options)
            self.formatter.format(DataType.cirrus_transforms_steps, data, format_options)

    def _list_messages(self, data_type, search_criteria, format_options, merged_app_cfg):
        logger.debug("Preparing to get data for {}".format(data_type))
        try:
            if data_type == DataType.cirrus_messages:
                result = self.cirrus_proxy.search_for_messages(search_criteria, merged_app_cfg)
            elif data_type == DataType.ice_failed_messages:
                self.ice_proxy.initialise(format_options)
                result = self.ice_proxy.list_messages(search_criteria, merged_app_cfg)
            else:
                raise InvalidStateException("Unknown data type passed to list messages for")
        except FailedToCommunicateWithSystem as err:
            error_and_exit(str(err))
        record_count = len(result) if result else 0
        logger.debug("Obtained {} records from server".format(record_count))
        self.formatter.format(data_type, result, format_options)

    def find_message_by_id(self, search_criteria, merged_app_cfg):
        logger.debug("Attempting to find message by id")
        try:
            result = self.cirrus_proxy.get_message_by_uid(search_criteria.get(MSG_UID), merged_app_cfg)
        except FailedToCommunicateWithSystem as err:
            error_and_exit(str(err))
        return result

    def analyse(self, search_parameters, cfg_rule, limit, format_options, merged_app_cfg):
        """Retrieve msgs from Cirrus and apply algorithms from rule against each, collate results and display"""
        try:
            result = self.cirrus_proxy.search_for_messages(search_parameters, merged_app_cfg)
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
                    self.__process_algorithms_for_message(msg_model, format_options, merged_app_cfg)
                self.__format_analysis(cfg_rule, format_options)
            else:
                logger.error("Failed to retrieve any messages from search request to analyse")
        except FailedToCommunicateWithSystem as err:
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
            logger.info("Adding time window to search of start-date: {}, end-date: {}".format(time_params.get(START_DATE), time_params.get(END_DATE)))
        else:

            # handle start and end times
            system_to_contact = cli_dict.get(SYSTEM, ICE.upper())

            # if we just have start then set now as end time
            if not START_DATETIME in cli_dict:
                error_and_exit("Please provide a time window to search ie 1d or given start and end datetime values")
            start_string = parser_datetime_by_system(system_to_contact, cli_dict.get(START_DATETIME))
            end_string = None
            if system_to_contact == CIRRUS.upper():
                if not END_DATETIME in cli_dict:
                    end_string = get_datetime_now_as_zulu()
                else:
                    end_string = parser_datetime_by_system(system_to_contact, cli_dict.get(END_DATETIME))
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

    def __process_algorithms_for_message(self, msg_model, format_options, merged_app_cfg):
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
                        data_enricher = self.__get_algorithm_prerequisite_data(msg_model, algorithm_instance, merged_app_cfg)
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

    @staticmethod
    def is_cirrus_based_request(cli_dict):
        function_to_call = cli_dict.get(FUNCTION)
        if MessageProcessor.is_non_http_request(cli_dict) or function_to_call in [GET_LOGS, WEBPACK]:
            return False
        return True

    def __get_algorithm_prerequisite_data(self, msg_model, algorithm_instance, merged_app_cfg):
        data_set = algorithm_instance.get_data_prerequistites()
        data_enricher = MessageEnricher(msg_model, self.cirrus_proxy, merged_app_cfg)
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

