import logging
from logging.config import fileConfig

from main.cli.cli_parser import LOCATIONS, CONFIGS, ARTIFACTS, SCRIPTS, VERSIONS, DASHBOARD, MESSAGES
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import FUNCTION, OPTIONS, DataType, OUTPUT, TABLE, ICE_CFG
from main.formatter.formatter import Formatter
from main.http.ice_proxy import ICEProxy
from main.utils.utils import error_and_exit

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class ICECommandProcessor:
    """Main class that takes cli arguments and actions them by communicating with ICE"""

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.ice_proxy = ICEProxy()
        self.formatter = Formatter()

    def action_cli_request(self, cli_dict, merged_app_cfg):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on supplied arguments
        function_to_call = cli_dict.get(FUNCTION, None)

        if not function_to_call:
            error_and_exit("Please specific a command to run for ADM!")

        # Log into the adm site
        logger.info("Logging into ice site")
        self.ice_proxy.initialise(merged_app_cfg)

        logger.info("Received CLI request for function: {}".format(function_to_call))
        logger.debug("CLI command is: {}".format(str(cli_dict)))

        if function_to_call == DASHBOARD:
            result = self.ice_proxy.get_calm_dashboard_data(merged_app_cfg)
            data_type = DataType.ice_dashboard
        elif function_to_call == MESSAGES:
            result = self.ice_proxy.get_failed_messages_data(merged_app_cfg)
            data_type = DataType.ice_failed_messages
        else:
            error_and_exit(f"Unknown command passed for ADM: {function_to_call}")
        self.formatter.format(data_type, result, cli_dict.get(OPTIONS))