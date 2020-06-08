import logging
from logging.config import fileConfig

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import TRACKING_POINT, PAYLOAD, URL

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('parser')


def payload_has_json_post_error(payload):
    return payload_is_http_error(payload) and payload_has_json_mismatch_message(payload)


def payload_is_json_post_request(payload):
    return payload and payload.get(TRACKING_POINT) == "PAYLOAD [movement JSON POST request]"


def payload_is_http_error(payload):
    return payload and payload.get(TRACKING_POINT) == "PAYLOAD [Error: HTTP Response: 400]"


def payload_has_json_mismatch_message(payload):
    return payload and payload.get(PAYLOAD) == "{\"message\":\"preg_replace(): Parameter mismatch, pattern is a string while replacement is an array\",\"code\":0}"
