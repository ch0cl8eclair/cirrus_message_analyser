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


class DataType(Enum):
    config_rule = 1
    cirrus_messages = 2
    cirrus_payloads = 3
    cirrus_metadata = 4
    cirrus_events = 5
    cirrus_transforms = 6
    analysis_yara_movements = 7
    analysis_messages = 8
