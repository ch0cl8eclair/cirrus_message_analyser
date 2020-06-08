import os
import sys
from main.cli.cli_parser import parse_command_line_statement
from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.config.constants import CACHE_REF
from main.http.cirrus_session_proxy import obtain_cookies_from_cirrus_manually, cookies_file_exists
from main.message_processor import MessageProcessor
from diskcache import Cache

CACHE_HOME = os.path.join(os.path.dirname(__file__), '../cache')


def main():
    # Read in config
    config = ConfigSingleton(get_configuration_dict())

    with Cache(CACHE_HOME) as cache_ref:
        # Parse the cli command, if the cmd is not well formed then it prints an error and exits
        parsed_cli_parameters_dict = parse_command_line_statement(sys.argv)

        config.set(CACHE_REF, cache_ref)

        # Hand over the message processor to action
        processor = MessageProcessor()
        # Obtain the cirrus cookies if not present
        # TODO need to timeout cached cookie automatically after an hour,
        #  current implemention can only be set to a min of one day
        if not processor.is_non_http_request(parsed_cli_parameters_dict):
            if not cookies_file_exists(config):
                obtain_cookies_from_cirrus_manually()
        processor.action_cli_request(parsed_cli_parameters_dict)


if __name__ == '__main__':
    main()
