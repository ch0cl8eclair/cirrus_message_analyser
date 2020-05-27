import urllib3
import requests
import base64
import binascii
from cache_to_disk import cache_to_disk

from config.configuration import ConfigSingleton, CREDENTIALS, USERNAME, PASSWORD, LOGGING_CONFIG_FILE, URLS, \
    NAME, URL, GET, TYPE, POST, DATA_DICT, MSG_UID

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')


class CirrusProxy:

    def __init__(self):
        self.configuration = ConfigSingleton()

    def __get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'Authorization': self.__generate_auth_string(),
            'Tenant': 'eu0000000001'
        }
        return headers

    def __issue_get_request(self, url):
        logger.debug("Issuing get request: {}".format(url))
        response = requests.get(url, headers=self.__get_headers())
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed get webpage: {}, status code: {}".format(url, response.status_code))
            return None
        return response.json()

    def __issue_post_request(self, url, data_dict):
        logger.debug("Issuing post request: {}".format(url))
        response = requests.post(url, data=data_dict, headers=self.__get_headers())
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed to login successfully: {}".format(url))
            return None
        return response.json()

    def __get_url_and_issue(self, url_type, data_parameters_dict):
        config = self.__get_config_url(url_type)
        # TODO handle null where we fail to retrieve the given url_type, unlikely though
        if config.get(TYPE) == POST:
            default_request_data = config.get(DATA_DICT)
            merged_dict = {**default_request_data, **data_parameters_dict}
            self.__issue_post_request(config.get(URL), merged_dict)
        else:
            url = config.get(URL).format(data_parameters_dict.get(MSG_UID))
            self.__issue_get_request(url)

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
    def get_transforms_for_message(self, msg_uid):
        logger.info("Issue search for message transforms to cirrus")
        return self.__get_url_and_issue("GET_MESSAGE_TRANSFORMS", {MSG_UID: msg_uid})

    @cache_to_disk(7)
    def __generate_auth_string(self):
        config_credentials = self.configuration.get(CREDENTIALS)
        up_str = "{}:{}".format(config_credentials.get(USERNAME), config_credentials.get(PASSWORD))
        encoded = base64.b64encode(binascii.a2b_uu(up_str))
        return "Authorization: Basic {}".format(encoded)

    def __get_config_url(self, url_name):
        configured_urls = self.configuration.get(URLS)
        for config_url in configured_urls:
            if config_url[NAME] == url_name:
                return config_url
        return None
