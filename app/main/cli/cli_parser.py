import argparse

from main.config.constants import FUNCTION, UID, TIME, CSV, JSON, TABLE, RULE, OPTIONS, OUTPUT, START_DATETIME, \
    END_DATETIME, LIMIT, FILE, ICE, CIRRUS, SYSTEM, REGION, PROJECT, GROUP

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')
message_logger = logging.getLogger('message')

###
# Constants
###
LIST = 'list'
ANALYSE = 'analyse'
CLEAR_CACHE = 'clear-cache'
DETAIL = 'detail'
GET_LOGS = "get-logs"
WEBPACK = "webpack"

output_types_list = [CSV, JSON, TABLE, FILE]

MESSAGES = 'messages'
MESSAGE_PAYLOADS = 'message-payloads'
MESSAGE_EVENTS = 'message-events'
MESSAGE_METADATA = 'message-metadata'
MESSAGE_TRANSFORMS = 'message-transforms'
RULES = 'rules'
list_commands = [MESSAGES, MESSAGE_PAYLOADS, MESSAGE_EVENTS, MESSAGE_METADATA, MESSAGE_TRANSFORMS, RULES]

ADM = "ADM"
COMMAND = "COMMAND"
LOCATIONS = "locations"
CONFIGS = "configs"
VERSIONS = "versions"
SCRIPTS = "scripts"
ARTIFACTS = "artifacts"
CLI_TYPE = "cli-type"

###
# Create CLI command parsers
###
def create_parent_parser():
    parser = argparse.ArgumentParser(description="Obtain Cirrus message details", add_help=False)
    parent_args_group = parser.add_mutually_exclusive_group()
    parent_args_group.add_argument("-v", "--verbose", action="store_true", default=False)
    parent_args_group.add_argument("-q", "--quiet", action="store_true", default=False)
    parser.add_argument("-o", "--output", choices=output_types_list, default="table", help="Select the output data format")
    return parser


def create_command_parser(parent_parser):
    command_parser = argparse.ArgumentParser(description="Cirrus Message Analyser commands", parents=[parent_parser])
    command_parser.add_argument("command", choices=[LIST, ANALYSE, CLEAR_CACHE, DETAIL, GET_LOGS, WEBPACK])
    help_str = "List command directives: {}".format(",".join(list_commands))
    command_parser.add_argument("command_parameters", metavar='N', nargs='?', help=help_str)
    command_parser.add_argument("--uid", help="Specify the message unique id")
    command_parser.add_argument("--rule", help="Specify the processing rule to use")
    command_parser.add_argument("--time", help="Specify the time window to filter on eg today, yesterday, 1d, 3h")
    command_parser.add_argument("--start-datetime", dest="start_datetime", help="Specify the start date time: 2020-05-17T10:30:08.877Z")
    command_parser.add_argument("--end-datetime", dest="end_datetime", help="Specify the end date time: 2020-05-17T10:30:08.877Z")
    command_parser.add_argument("--limit", type=int, choices=range(1, 100), help="upper limit on the number of msgs processed")
    command_parser.add_argument("--system", choices=["CIRRUS", "ICE"], help="The target system form which to retrieve data")
    command_parser.add_argument("--region", choices=["EU", "US", "ZA", "AU"], help="The region with which the message is associated")
    return command_parser


def create_adm_parser(parent_parser):
    adm_parser = argparse.ArgumentParser(description="ADM Interface commands", parents=[parent_parser])
    adm_parser.add_argument("command", choices=[LOCATIONS, CONFIGS, VERSIONS, SCRIPTS, ARTIFACTS, LOCATIONS])
    adm_parser.add_argument("--group", help="The parent project group name")
    adm_parser.add_argument("--project", help="The project name")
    return adm_parser


def create_processing_options(args):
    """Generates an options dict which contain input and output command processing options"""
    options = {'output': args.output, 'quiet': args.quiet, 'verbose': args.verbose}
    return options


def parse_command_line_statement(arguments_list):
    """Takes the cli statement, parses and validates it and returns a dict detailing the command"""
    parent_parser = create_parent_parser()
    if len(arguments_list) > 2 and arguments_list[1].upper() == ADM:
        adm_parser = create_adm_parser(parent_parser)
        adm_args = adm_parser.parse_args(arguments_list[2:])
        options = create_processing_options(adm_args)
        result_map = {OPTIONS: options}
        return _handle_adm_parameters(result_map, adm_args)
    else:
        command_parser = create_command_parser(parent_parser)
        # Skip the first element as that should be the python script name
        command_args = command_parser.parse_args(arguments_list[1:])
        options = create_processing_options(command_args)
        result_map = {OPTIONS: options}
        return _handle_command_parameters(result_map, command_args)


def _handle_command_parameters(result_map, command_args):
    result_map[CLI_TYPE] = COMMAND
    if command_args.command == LIST:
        if isinstance(command_args.command_parameters, str) and command_args.command_parameters in list_commands:
            func_str = "{}_{}".format(command_args.command, command_args.command_parameters).replace('-', '_')
            result_map[FUNCTION] = func_str
        else:
            # TODO do the same print to std error and exit
            logger.error("Invalid list argument given: %s", command_args.command_parameters)
    else:
        result_map[FUNCTION] = command_args.command
    if command_args.rule:
        result_map[RULE] = command_args.rule
    if command_args.time:
        result_map[TIME] = command_args.time
    if command_args.start_datetime:
        result_map[START_DATETIME] = command_args.start_datetime
    if command_args.end_datetime:
        result_map[END_DATETIME] = command_args.end_datetime
    if command_args.uid:
        result_map[UID] = command_args.uid
    if command_args.limit:
        result_map[LIMIT] = command_args.limit
    if command_args.system:
        result_map[SYSTEM] = command_args.system
    if command_args.region:
        result_map[REGION] = command_args.region
    log_requested_command(result_map)
    return result_map


def _handle_adm_parameters(result_map, args):
    result_map[CLI_TYPE] = ADM
    if args.command:
        result_map[FUNCTION] = args.command
    if args.project:
        result_map[PROJECT] = args.project
    if args.group:
        result_map[GROUP] = args.group
    log_requested_command(result_map)
    return result_map


def log_requested_command(cli_map):
    if cli_map[CLI_TYPE] == COMMAND:
        if cli_map[FUNCTION].startswith("list"):
            output_str = "Getting {}".format(cli_map[FUNCTION])
        else:
            output_str = "Performing {}".format(cli_map[FUNCTION])
        if RULE in cli_map:
            output_str = output_str + ", with rule: {}".format(cli_map[RULE])
        if TIME in cli_map:
            output_str = output_str + ", with time: {}".format(cli_map[TIME])
        elif START_DATETIME in cli_map:
            output_str = output_str + ", with start datetime: {}".format(cli_map[START_DATETIME])
            if END_DATETIME in cli_map:
                output_str = output_str + "& end datetime: {}".format(cli_map[END_DATETIME])
        if UID in cli_map:
            output_str = output_str + ", with msg uid: {}".format(cli_map[UID])
        message_logger.info(output_str + " & output={}".format(cli_map[OPTIONS][OUTPUT]))
    elif cli_map[CLI_TYPE] == ADM:
        adm_object = ""
        if GROUP in cli_map:
            adm_object = cli_map[GROUP]
            output_str = f"for group: {adm_object}"
        elif PROJECT in cli_map:
            adm_object = cli_map[PROJECT]
            output_str = f"for project: {adm_object}"
        else:
            output_str = "all"
        message_logger.info("Fetching ADM {} {} & output={}".format(cli_map[FUNCTION], adm_object, cli_map[OPTIONS][OUTPUT]))
