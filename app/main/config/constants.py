from enum import Enum
import os

CREDENTIALS = "credentials"
RULES = "rules"

OUTPUT = 'output'
QUIET = 'quiet'
VERBOSE = 'verbose'

CSV = 'csv'
JSON = 'json'
TABLE = 'table'

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
RULE = 'rule'
TIME = 'time'
UID = 'uid'
OPTIONS = 'options'
LIMIT = "limit"

TODAY = "today"
YESTERDAY = "yesterday"
DAYS = "days"
HOURS = "hours"
SEARCH_PARAMETERS = "search_parameters"
ALGORITHMS = "algorithms"

START_DATETIME = "start-datetime"
END_DATETIME = "end-datetime"

CIRRUS_COOKIE = "cirrus_cookie"
CACHED_COOKIE_FILE = os.path.join(os.path.dirname(__file__), '../../../cache/cirrus_cookies.txt')

MESSAGE_ID = "message-id"
TRACKING_POINT = "tracking-point"
PAYLOAD = "payload"

MESSAGE_STATUS = "message-status"
UNIQUE_ID = "unique-id"

CHROME_DRIVER_FOLDER = "chrome-driver-folder"
CIRRUS_CONNECT_WEB_URL = "cirrus_connect_web_url"

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


# This is for custom data algorithms
algorithm_data_type_map = {
    YARA_MOVEMENT_POST_JSON_ALGO: DataType.analysis_yara_movements,
    HAS_EMPTY_FIELDS_FOR_PAYLOAD: DataType.empty_fields_for_payload,
    HAS_MANDATORY_FIELDS_FOR_PAYLOAD: DataType.mandatory_fields_for_payload,
    TRANSFORM_BACKTRACE_FIELDS: DataType.transform_backtrace_fields
}
