import argparse
import sys

###
# Constants
###
from config.constants import FUNCTION, UID, TIME, CSV, JSON, TABLE, RULE, OPTIONS

LIST = 'list'
ANALYSE = 'analyse'
CLEAR_CACHE = 'clear-cache'

output_types_list = [CSV, JSON, TABLE]

MESSAGES = 'messages'
MESSAGE_PAYLOADS = 'message-payloads'
MESSAGE_EVENTS = 'message-events'
MESSAGE_METADATA = 'message-metadata'
MESSAGE_TRANSFORMS = 'message-transforms'
RULES = 'rules'
list_commands = [MESSAGES, MESSAGE_PAYLOADS, MESSAGE_EVENTS, MESSAGE_METADATA, MESSAGE_TRANSFORMS, RULES]


###
# Create CLI command parsers
###
def create_parent_parser():
    parser = argparse.ArgumentParser(description="Obtain Cirrus message details", add_help=False)
    parent_args_group = parser.add_mutually_exclusive_group()
    parent_args_group.add_argument("-v", "--verbose", action="store_true", default=False)
    parent_args_group.add_argument("-q", "--quiet", action="store_true", default=False)
    parser.add_argument("-o", "--output", choices=output_types_list, default="csv")
    return parser


def create_command_parser(parent_parser):
    command_parser = argparse.ArgumentParser(description="list commands", parents=[parent_parser])
    command_parser.add_argument("command", choices=[LIST, ANALYSE, CLEAR_CACHE])
    command_parser.add_argument("command_parameters", metavar='N', nargs='?', help="parameters for the chosen command")
    command_parser.add_argument("--uid", help="Specify the message unique id")
    command_parser.add_argument("--rule", help="Specify the processing rule to use")
    command_parser.add_argument("--time", help="Specify the time window to filter on eg today, yesterday, 1d, 3h")
    command_parser.add_argument("--start-datetime", help="Specify the start date time: 2020-05-17T10:30:08.877Z")
    command_parser.add_argument("--end-datetime", help="Specify the end date time: 2020-05-17T10:30:08.877Z")
    return command_parser


def create_processing_options(args):
    """Generates an options dict which contain input and output command processing options"""
    options = {'output': args.output, 'quiet': args.quiet, 'verbose': args.verbose}
    return options


def parse_command_line_statement(arguments_list):
    """Takes the cli statement, parses and validates it and returns a dict detailing the command"""
    parent_parser = create_parent_parser()
    command_parser = create_command_parser(parent_parser)
    # Skip the first element as that should be the python script name
    command_args = command_parser.parse_args(arguments_list[1:])
    options = create_processing_options(command_args)
    result_map = {OPTIONS: options}
    if command_args.command == LIST:
        if isinstance(command_args.command_parameters, str) and command_args.command_parameters in list_commands:
            func_str = "{}_{}".format(command_args.command, command_args.command_parameters).replace('-', '_')
            result_map[FUNCTION] = func_str
        else:
            # TODO do the same print to std error and exit
            print("Invalid list argument given", file=sys.stderr)
    else:
        result_map[FUNCTION] = command_args.command
    if command_args.rule:
        result_map[RULE] = command_args.rule
    if command_args.time:
        result_map[TIME] = command_args.time
    if command_args.uid:
        result_map[UID] = command_args.uid
    return result_map
