import urllib3
import requests
import base64
import json
from cache_to_disk import cache_to_disk

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import CREDENTIALS, USERNAME, PASSWORD, URLS, \
    NAME, URL, GET, TYPE, POST, DATA_DICT, MSG_UID, CIRRUS_COOKIE
from main.http.cirrus_session_proxy import read_cookies_file

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')


class FailedToCommunicateWithCirrus(Exception):
    """Exception raised for failed communications with Cirrus"""

    def __init__(self, url, response_code):
        self.url = url
        self.response_code = response_code

    def __str__(self):
        return "Failed to get success code from url: {}, obtained: {}".format(self.url, self.response_code)


class CirrusProxy:

    def __init__(self):
        self.configuration = ConfigSingleton()

    def __get_headers(self):
        # Removed             'Cache-Control': 'no-cache',
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': self.__generate_auth_string(),
            'Cookie': self.__get_cached_cookies(),
            'Tenant': 'eu0000000001'
        }
        return headers

    @cache_to_disk(7)
    def get(self, url):
        """Issue a simple http get to fetch an xsl file or similiar"""
        logger.debug("Issuing simple get request: {}".format(url))
        response = requests.get(url)
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed get url: {}, status code: {}".format(url, response.status_code))
            raise FailedToCommunicateWithCirrus(url, response.status_code)
        return response.text

    def __issue_cirrus_get_request(self, url):
        logger.debug("Issuing get request: {}".format(url))
        response = requests.get(url, headers=self.__get_headers())
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed get webpage: {}, status code: {}".format(url, response.status_code))
            raise FailedToCommunicateWithCirrus(url, response.status_code)
        logger.debug("Response from server is: %s", response.text)
        return response.json()

    def __issue_cirrus_post_request(self, url, data_dict):
        logger.debug("Issuing post request: {}".format(url))
        logger.debug("Request headers are: {}".format(self.__get_headers()))
        form_data = json.dumps(data_dict)
        logger.debug("Request data is: {}".format(form_data))
        response = requests.post(url, data=form_data, headers=self.__get_headers())
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed to issue post request to: {}, received error code: {}".format(url, response.status_code))
            if response.text:
                logger.error("Error response from server is: {}".format(response.json()))
            raise FailedToCommunicateWithCirrus(url, response.status_code)
        logger.debug("Response from server is: %s", response.text)
        return response.json()

    def __get_url_and_issue(self, url_type, data_parameters_dict):
        config = self.__get_config_url(url_type)
        # TODO handle null where we fail to retrieve the given url_type, unlikely though
        if config.get(TYPE) == POST:
            default_request_data = config.get(DATA_DICT)
            merged_dict = {**default_request_data, **data_parameters_dict}
            return self.__issue_cirrus_post_request(config.get(URL), merged_dict)
        else:
            url = config.get(URL).format(data_parameters_dict.get(MSG_UID))
            return self.__issue_cirrus_get_request(url)

    @cache_to_disk(1)
    def search_for_messages(self, search_parameters):
        logger.info("Issue search for messages to cirrus")
        return self.__get_url_and_issue("SEARCH_MESSAGES", search_parameters)

    @cache_to_disk(1)
    def get_payloads_for_message(self, msg_uid):
        logger.info("Issue search for message payloads to cirrus")
        return self.__get_url_and_issue("GET_MESSAGE_PAYLOADS", {MSG_UID: msg_uid})

    @cache_to_disk(1)
    def get_events_for_message(self, msg_uid):
        logger.info("Issue search for message events to cirrus")
        return self.__get_url_and_issue("GET_MESSAGE_EVENTS", {MSG_UID: msg_uid})

    @cache_to_disk(1)
    def get_metadata_for_message(self, msg_uid):
        logger.info("Issue search for message metadata to cirrus")
        return self.__get_url_and_issue("GET_MESSAGE_METADATA", {MSG_UID: msg_uid})

    @cache_to_disk(7)
    def get_transforms_for_message(self, search_parameters):
        logger.info("Issue search for message transforms to cirrus")
        return self.__get_url_and_issue("GET_MESSAGE_TRANSFORMS", search_parameters)

    @cache_to_disk(7)
    def __generate_auth_string(self):
        config_credentials = self.configuration.get(CREDENTIALS)
        up_str = "{}:{}".format(config_credentials.get(USERNAME), config_credentials.get(PASSWORD))

        message_bytes = up_str.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
        logger.debug("Credentials encoded as: {}".format(base64_message))

        return "Basic {}".format(base64_message)

    @cache_to_disk(1)
    def __get_cached_cookies(self):
        return read_cookies_file()

    def __get_config_url(self, url_name):
        configured_urls = self.configuration.get(URLS)
        for config_url in configured_urls:
            if config_url[NAME] == url_name:
                return config_url
        return None
