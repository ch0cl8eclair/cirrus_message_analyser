import sys
from main.cli.cli_parser import parse_command_line_statement
from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.http.cirrus_session_proxy import obtain_cookies_from_cirrus_manually, cookies_file_exists
from main.message_processor import MessageProcessor


def main():
    # Read in config
    config = ConfigSingleton(get_configuration_dict())
    if not cookies_file_exists():
        obtain_cookies_from_cirrus_manually()
    # Parse the cli command, if the cmd is not well formed then it prints an error and exits
    parsed_cli_parameters_dict = parse_command_line_statement(sys.argv)
    # Hand over the message processor to action
    processor = MessageProcessor()
    processor.action_cli_request(parsed_cli_parameters_dict)


if __name__ == '__main__':
    main()
