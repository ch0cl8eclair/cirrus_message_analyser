import json
import logging
from logging.config import fileConfig

from main.cli.cli_parser import LOCATIONS, CONFIGS, ARTIFACTS, SCRIPTS, VERSIONS
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import FUNCTION, PROJECT, GROUP, OPTIONS, DataType, OUTPUT, TABLE
from main.formatter.formatter import Formatter, DynamicFormatter
from main.http.adm_proxy import ADMProxy

from main.utils.utils import error_and_exit

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class ADMCommandProcessor:
    """Main class that takes cli arguments and actions them by communicating with ADM"""

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.adm_proxy = ADMProxy()
        self.formatter = DynamicFormatter()

    def action_cli_request(self, cli_dict, merged_app_cfg):
        """Take the cli arguments, validate them further and action them"""
        # Determine behaviour based on supplied arguments
        function_to_call = cli_dict.get(FUNCTION, None)
        project = cli_dict.get(PROJECT, None)
        group = cli_dict.get(GROUP, None)
        options = cli_dict.get(OPTIONS)
        options[OUTPUT] = TABLE

        if not function_to_call:
            error_and_exit("Please specific a command to run for ADM!")

        # Log into the adm site
        logger.info("Logging into adm site")
        self.adm_proxy.initialise(merged_app_cfg)

        logger.info("Received CLI request for function: {}".format(function_to_call))
        logger.debug("CLI command is: {}".format(str(cli_dict)))

        if function_to_call == LOCATIONS:
            if project:
                result = self.adm_proxy.get_locations_for_project(project, merged_app_cfg)
            elif group:
                result = self.adm_proxy.get_locations_for_group(group, merged_app_cfg)
            else:
                result = self.adm_proxy.get_locations(merged_app_cfg)
            data_type = DataType.adm_locations

        elif function_to_call == CONFIGS:
            if project:
                result = self.adm_proxy.get_configs_for_project(project, merged_app_cfg)
            elif group:
                result = self.adm_proxy.get_configs_for_group(group, merged_app_cfg)
            else:
                result = self.adm_proxy.get_configs(merged_app_cfg, merged_app_cfg)
            data_type = DataType.adm_configs

        elif function_to_call == VERSIONS:
            if project:
                result = self.adm_proxy.get_versions_for_project(project, merged_app_cfg)
            elif group:
                result = self.adm_proxy.get_versions_for_group(group, merged_app_cfg)
            else:
                result = self.adm_proxy.get_versions(merged_app_cfg)
            data_type = DataType.adm_versions

        elif function_to_call == SCRIPTS:
            if project:
                result = self.adm_proxy.get_scripts_for_project(project, merged_app_cfg)
            elif group:
                result = self.adm_proxy.get_scripts_for_group(group, merged_app_cfg)
            else:
                result = self.adm_proxy.get_scripts(merged_app_cfg)
            data_type = DataType.adm_scripts

        elif function_to_call == ARTIFACTS:
            if project:
                result = self.adm_proxy.get_artifacts_for_project(project, merged_app_cfg)
            elif group:
                result = self.adm_proxy.get_artifacts_for_group(group, merged_app_cfg)
            else:
                result = self.adm_proxy.get_artifacts(merged_app_cfg)
            data_type = DataType.adm_artifacts

        else:
            error_and_exit(f"Unknown command passed for ADM: {function_to_call}")
        self.formatter.format(data_type, result, options)