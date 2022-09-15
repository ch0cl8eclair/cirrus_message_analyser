from enum import Enum
import os

APPLICATIONS = "applications"
CREDENTIALS = "credentials"
RULES = "rules"
ELASTICSEARCH_CREDENTIALS = "elastic_log_search"
CIRRUS_CREDENTIALS = "cirrus"
ICE_CREDENTIALS = "ice_dashboard"
ADM_CREDENTIALS = "adm_package_manager"
GITLAB = "gitlab"
GITLAB_CONFIG_FILE = "gitlab_config_file"
GITLAB_DEFAULT_ID = "gitlab_id"

OUTPUT = 'output'
QUIET = 'quiet'
VERBOSE = 'verbose'

CSV = 'csv'
JSON = 'json'
TABLE = 'table'
FILE = 'file'

WILDCARD = "*"
ENV = "env"
CONFIG = "config"
ENDPOINTS = "endpoints"

PRD = 'PRD'
OAT = 'OAT'
DEV = 'DEV'
EU = 'EU'
US = 'US'

ID = "id"
URL = "url"
URLS = "urls"
NAME = "name"
TYPE = "type"
SOURCE = "source"
DESTINATION = "destination"
GET = "GET"
POST = "POST"

DATA_DICT = "data_dict"
MSG_UID = "msg_uid"

USERNAME = "username"
CIRRUS_USERNAME = "CIRRUS_USERNAME"
PASSWORD = "password"
CIRRUS_PASSWORD = "CIRRUS_PASSWORD"

FUNCTION = 'function'
ENTITY = 'entity'
RULE = 'rule'
TIME = 'time'
UID = 'uid'
OPTIONS = 'options'
LIMIT = "limit"
PROJECT = 'project'
GROUP = 'group'
GROUPS = 'groups'
PROJECTS_FOR_TEAM = "projects-for-team"
COMMITS = 'commits'
TAGS = 'tags'
BRANCHES = 'branches'
PARAMETERS = 'parameters'

TODAY = "today"
YESTERDAY = "yesterday"
DAYS = "days"
HOURS = "hours"
SEARCH_PARAMETERS = "search_parameters"
ALGORITHMS = "algorithms"

START_DATETIME = "start-datetime"
END_DATETIME = "end-datetime"
START_DATE = "start-date"
END_DATE = "end-date"

CIRRUS_COOKIE = "cirrus_cookie"
CACHED_COOKIE_FILE = os.path.join(os.path.dirname(__file__), '../../../cache/cirrus_cookies.txt')

MESSAGE_ID = "message-id"
TRACKING_POINT = "tracking-point"
PAYLOAD = "payload"

MESSAGE_STATUS = "message-status"
UNIQUE_ID = "unique-id"

CHROME_DRIVER_FOLDER = "chrome-driver-folder"

PAYLOAD_INDEX = "payload-index"
STEP = "step"
# ROUTE = "ROUTE"
# SEND = "SEND"
YARA_MOVEMENT_POST_JSON_ALGO = "YaraMovementPostJson"
HAS_EMPTY_FIELDS_FOR_PAYLOAD = "HasEmptyFieldsForPayload"
HAS_MANDATORY_FIELDS_FOR_PAYLOAD = "HasMandatoryFieldsForPayload"
TRANSFORM_BACKTRACE_FIELDS = "TransformBacktraceFields"
ALGORITHM_STATS = "algorithm_stats"

CACHE_REF = "cache-ref"
CACHED_COOKIE = "cached-cookie"
# Cache expire constants
SEC_30 = 30
MIN_30 = 60 * 30
HOUR_1 = 3600
DAY_1 = HOUR_1 * 24
WEEK = 7 * DAY_1

FIELDS = "fields"
LINES = "lines"
DOCUMENT_LINES = "document_lines"
HEADER_FIELDS = "header_fields"
DOCUMENTS = "documents"
INDEX = "index"
PAYLOAD_TRACKING_POINT = "payload-tracking-point"
ARGUMENTS = "arguments"

FIELD_TYPE = "field_type"

CIRRUS_LOGIN = "CIRRUS_LOGIN"
ENABLE_SELENIUM_LOGIN = "enable_selenium_login"
ENABLE_ELASTICSEARCH_QUERY = "enable_elasticsearch_query"
ELASTICSEARCH_HOST = "elasticsearch_host"
ELASTICSEARCH_PORT = "elasticsearch_port"
ELASTICSEARCH_SCHEME = "elasticsearch_scheme"
ELASTICSEARCH_INDEX = "elasticsearch_index"
ELASTICSEARCH_SECONDS_MARGIN = "elasticsearch_seconds_margin"
ELASTICSEARCH_SECONDS_MARGIN_FOR_ICE = "elasticsearch_seconds_margin_for_ice"
ELASTICSEARCH_EXCLUDE_LOG_FILES = "elasticsearch_exclude_log_files"
ELASTICSEARCH_RETAIN_SERVER_OUTPUT = "elasticsearch_retain_server_output"

HOST = "host"
LOGFILE = "logfile"
# LOG_MESSAGE = "log_message"
LOG_CORRELATION_ID = "log_correlation_id" # used as table header in output
HOST_LOG_CORRELATION_ID = "host_log_correlation_id"
HOST_LOG_MAPPINGS = "host_log_mappings"
LOG_LINES = "log_lines"
LOG_LINE_STATS = "log_line_stats"
LINE = "line"
LEVEL = "level"
LOG_STATEMENT_FOUND = "log_statements_found"

OUTPUT_FOLDER = "output_folder"
ZIP_OUTPUT_FOLDER = "zip-output_folder"
ERROR_COUNT = "errors"
TOTAL_COUNT = "totals"

TRANSFORM = "TRANSFORM"
VALIDATE = "VALIDATE"

PROJECTS = "projects"
NAME = "name"
SYSTEM = "system"
ICE = "Ice"
ICE_CFG = "ICE"
CIRRUS = "Cirrus"
CIRRUS_CFG = "CIRRUS"
ADM_CFG = 'ADM'
MISC_CFG = 'MISC'

REGION = "region"
ADAPTER_ID = "adapter_id"

BASE_URL = "base_url"

MESSAGE_ID_HEADING = 'Message ID'
EVENT_DATE_HEADING = 'Event Date'

ENABLE_ICE_PROXY = "enable_ice_login"

ADM_LOGIN = "ADM_LOGIN"
ADM_SUBMIT = "ADM_SUBMIT"
ADM_LOCATIONS = "ADM_LOCATIONS"
ADM_VERSIONS = "ADM_VERSIONS"
ADM_SCRIPTS = "ADM_SCRIPTS"
ADM_CONFIGS = "ADM_CONFIGS"
ADM_ARTIFACTS = "ADM_ARTIFACTS"
ADM_ARTIFACTS_STATUS = "ADM_ARTIFACTS_STATUS"
ICE_LOGIN = "ICE_LOGIN"
ICE_SUBMIT = "ICE_SUBMIT"
ICE_CALM_DASHBOARD = "ICE_CALM_DASHBOARD"
ICE_FAILED_MESSAGES = "ICE_FAILED_MESSAGES"

LOGIN = 'LOGIN'

# Declaring these enums here to avoid circular reference issues, that are such a pain
class DataType(Enum):
    config_rule = 1
    cirrus_messages = 2
    cirrus_payloads = 3
    cirrus_metadata = 4
    cirrus_events = 5
    cirrus_transforms = 6
    analysis_yara_movements = 7
    analysis_messages = 8
    empty_fields_for_payload = 9
    mandatory_fields_for_payload = 10
    transform_backtrace_fields = 11
    cirrus_transforms_steps = 12
    payload_transform_mappings = 13
    host_log_mappings = 14
    log_statements = 15
    elastic_search_results = 16
    elastic_search_results_correlated = 17
    ice_dashboard = 18
    ice_failed_messages = 19
    adm_locations = 20
    adm_configs = 21
    adm_versions = 22
    adm_scripts = 23
    adm_artifacts = 24
    git_projects = 25
    git_groups = 26
    git_branches = 27
    git_tags = 28
    git_commits = 29


class DataRequisites(Enum):
    status = 0
    payloads = 1
    events = 2
    metadata = 3
    transforms = 4


class TransformStage(Enum):
    json_missing_fields = 0
    v5_to_movement_xpaths = 1
    idoc_to_f4fv5_xpaths = 2
    idoc = 3


class OutputFormat(Enum):
    json = 0
    table = 1
    csv = 2
    file = 3


class LogSearchDirection(Enum):
    both = 0
    forward = 1
    backward = 2


# This is for custom data algorithms
algorithm_data_type_map = {
    YARA_MOVEMENT_POST_JSON_ALGO: DataType.analysis_yara_movements,
    HAS_EMPTY_FIELDS_FOR_PAYLOAD: DataType.empty_fields_for_payload,
    HAS_MANDATORY_FIELDS_FOR_PAYLOAD: DataType.mandatory_fields_for_payload,
    TRANSFORM_BACKTRACE_FIELDS: DataType.transform_backtrace_fields
}

output_formats_to_extention_map = {
    OutputFormat.json: ".json",
    OutputFormat.csv: ".csv",
    OutputFormat.table: ".txt",
    OutputFormat.file: ".json"
}
