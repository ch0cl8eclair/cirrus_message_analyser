from enum import Enum

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
GET = "GET"
POST = "POST"

DATA_DICT = "data_dict"
MSG_UID = "msg_uid"

USERNAME = "username"
PASSWORD = "password"

FUNCTION = 'function'
RULE = 'rule'
TIME = 'time'
UID = 'uid'
OPTIONS = 'options'

TODAY = "today"
YESTERDAY = "yesterday"
DAYS = "days"
HOURS = "hours"
SEARCH_PARAMETERS = "search_parameters"

START_DATETIME = "start-datetime"
END_DATETIME = "end-datetime"


class DataType(Enum):
    config_rule = 1
    cirrus_messages = 2
    cirrus_payloads = 3
    cirrus_metadata = 4
    cirrus_events = 5
    cirrus_transforms = 6
