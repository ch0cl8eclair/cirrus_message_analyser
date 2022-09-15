import os
import sys
import logging
from logging.config import fileConfig

from diskcache import Cache

from main.adm_command_processor import ADMCommandProcessor
from main.cli.cli_parser import parse_command_line_statement, COMMAND, CLI_TYPE, ADM, GIT, ICE
from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.config.constants import CACHE_REF, OPTIONS, ICE_CFG, ADM_CFG, CIRRUS_CFG, TABLE, OUTPUT, ENV, REGION
from main.gitlab_command_processor import GitLabCommandProcessor
from main.http.cirrus_session_proxy import obtain_cookies_from_cirrus_driver
from main.ice_command_processor import ICECommandProcessor
from main.message_processor import MessageProcessor
from main.utils.utils import get_merged_app_cfg, unpack_config, cookies_file_exists

CACHE_HOME = os.path.join(os.path.dirname(__file__), '../cache')

LOGGING_CONFIG_FILE = os.path.join(os.path.dirname(__file__), './resources/logging_config.ini')
fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


def main():
    # Read in config
    config = ConfigSingleton(get_configuration_dict())

    with Cache(CACHE_HOME) as cache_ref:
        # Parse the cli command, if the cmd is not well formed then it prints an error and exits
        parsed_cli_parameters_dict = parse_command_line_statement(sys.argv)

        options = parsed_cli_parameters_dict.get(OPTIONS)
        env = options.get(ENV)
        region = options.get(REGION)

        config.set(CACHE_REF, cache_ref)
        # Handle all cirrus, log and ice commands
        if parsed_cli_parameters_dict[CLI_TYPE] == COMMAND:
            merged_app_cfg = get_merged_app_cfg(config, CIRRUS_CFG, options)
            # Hand over the message processor to action
            processor = MessageProcessor()
            # Obtain the cirrus cookies if not present, but only for commands that require Cirrus
            # TODO list messages for ice currently still fetches cirrus cookies
            if processor.is_cirrus_based_request(parsed_cli_parameters_dict):
                if not cookies_file_exists(config, CIRRUS_CFG, env, region):
                    logger.debug("No Cirrus cookie found, logging in")
                    obtain_cookies_from_cirrus_driver(merged_app_cfg)
                    logger.debug("Selenium process completed")
                else:
                    logger.debug("Already logged into Cirrus, we have cookie, not logging in")
            processor.action_cli_request(parsed_cli_parameters_dict, merged_app_cfg)

        # Handle ADM commands
        elif parsed_cli_parameters_dict[CLI_TYPE] == ADM:
            merged_app_cfg = get_merged_app_cfg(config, ADM_CFG, options)
            processor = ADMCommandProcessor()
            processor.action_cli_request(parsed_cli_parameters_dict, merged_app_cfg)

        # Handle GIT commands
        elif parsed_cli_parameters_dict[CLI_TYPE] == GIT:
            processor = GitLabCommandProcessor()
            processor.action_cli_request(parsed_cli_parameters_dict)

        # Handle ICE commands
        elif parsed_cli_parameters_dict[CLI_TYPE] == ICE:
            merged_app_cfg = get_merged_app_cfg(config, ICE_CFG, options)
            options = merged_app_cfg[ICE_CFG][OPTIONS]
            # Override output to Table
            options[OUTPUT] = TABLE
            processor = ICECommandProcessor()
            processor.action_cli_request(parsed_cli_parameters_dict, merged_app_cfg)


if __name__ == '__main__':
    main()
