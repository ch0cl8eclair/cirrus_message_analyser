import os
import sys

from diskcache import Cache

from main.adm_command_processor import ADMCommandProcessor
from main.cli.cli_parser import parse_command_line_statement, COMMAND, CLI_TYPE, ADM, GIT
from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.config.constants import CACHE_REF
from main.gitlab_command_processor import GitLabCommandProcessor
from main.http.cirrus_session_proxy import obtain_cookies_from_cirrus_manually, cookies_file_exists
from main.message_processor import MessageProcessor

CACHE_HOME = os.path.join(os.path.dirname(__file__), '../cache')


def main():
    # Read in config
    config = ConfigSingleton(get_configuration_dict())

    with Cache(CACHE_HOME) as cache_ref:
        # Parse the cli command, if the cmd is not well formed then it prints an error and exits
        parsed_cli_parameters_dict = parse_command_line_statement(sys.argv)

        config.set(CACHE_REF, cache_ref)
        # Handle all cirrus, log and ice commands
        if parsed_cli_parameters_dict[CLI_TYPE] == COMMAND:
            # Hand over the message processor to action
            processor = MessageProcessor()
            # Obtain the cirrus cookies if not present, but only for commands that require Cirrus
            # TODO list messages for ice currently still fetches cirrus cookies
            if processor.is_cirrus_based_request(parsed_cli_parameters_dict):
                if not cookies_file_exists(config):
                    obtain_cookies_from_cirrus_manually()
            processor.action_cli_request(parsed_cli_parameters_dict)

        # Handle ADM commands
        elif parsed_cli_parameters_dict[CLI_TYPE] == ADM:
            processor = ADMCommandProcessor()
            processor.action_cli_request(parsed_cli_parameters_dict)

        # Handle GIT commands
        elif parsed_cli_parameters_dict[CLI_TYPE] == GIT:
            processor = GitLabCommandProcessor()
            processor.action_cli_request(parsed_cli_parameters_dict)


if __name__ == '__main__':
    main()
