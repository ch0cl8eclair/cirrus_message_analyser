import os

from main.config.constants import CREDENTIALS, RULES, CHROME_DRIVER_FOLDER, PASSWORD, USERNAME, CIRRUS_USERNAME, \
    CIRRUS_PASSWORD
from main.utils.utils import parse_json_from_file

CONFIGURATION_FILE = "resources/configuration.json"
CREDENTIALS_FILE   = "resources/credentials.json"
RULES_FILE         = "resources/rules.json"
LOGGING_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../../resources/logging_config.ini')

# MAP env variable to conf variable key, just a change of case currently
environment_vars_map = {CHROME_DRIVER_FOLDER.upper(): CHROME_DRIVER_FOLDER}
environment_credentials_vars_map = {CIRRUS_USERNAME: USERNAME, CIRRUS_PASSWORD: PASSWORD}


class Borg:
    _shared_state = {}

    def __init__(self, config_dict):
        if config_dict is not None:
            self._shared_state.update(config_dict)
        self.__dict__ = self._shared_state


class ConfigSingleton(Borg):
    def __init__(self, config_dict=None):
        Borg.__init__(self, config_dict)

    def get(self, key):
        return self._shared_state[key]

    def has_key(self, key):
        return key in self._shared_state

    def set(self, key, value):
        self._shared_state[key] = value


def read_configuration_file_into_map():
    main_config = parse_json_from_file(CONFIGURATION_FILE)
    credentials = parse_json_from_file(CREDENTIALS_FILE)
    rules = parse_json_from_file(RULES_FILE)
    main_config[CREDENTIALS] = credentials
    main_config[RULES] = rules
    return main_config


def read_environment_variables(main_config):
    """Overwrite configuration file values with those from environment"""
    # Read generic config
    for env_var, conf_var in environment_vars_map.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            main_config[conf_var] = env_value
    # Read credential specific variables
    for env_var, conf_var in environment_credentials_vars_map.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            main_config[CREDENTIALS][conf_var] = env_value


def get_configuration_dict():
    main_config = read_configuration_file_into_map()
    read_environment_variables(main_config)
    return main_config
