import urllib3
import requests
import base64
import json

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import CREDENTIALS, USERNAME, PASSWORD, URLS, \
    NAME, URL, GET, TYPE, POST, DATA_DICT, MSG_UID, CIRRUS_COOKIE, CACHE_REF, CACHED_COOKIE, WEEK, DAY_1, \
    CIRRUS_CREDENTIALS, ICE, MESSAGE_STATUS, DESTINATION, SOURCE, CIRRUS
from main.http.cirrus_session_proxy import read_cookies_file
from main.http.proxy_cache import ProxyCache, FailedToCommunicateWithSystem
from main.model.model_utils import CacheMissException
import urllib.parse

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')

VALID_CIRRUS_SEARCH_FIELDS = [SOURCE, DESTINATION, TYPE, MESSAGE_STATUS]


class CirrusProxy:

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.cache = ProxyCache()

    def __get_headers(self):
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': self.__generate_auth_string(),
            'Cookie': self.__get_cached_cookies(),
            'Tenant': 'eu0000000001',
            'Cache-Control': 'no-cache'
        }
        return headers

    def get(self, url):
        """Issue a simple http get to fetch an xsl file or similiar"""
        logger.debug("Issuing simple get request: {}".format(url))
        try:
            return self.cache.get_cache_result(url)
        except CacheMissException as ce:
            logger.debug(str(ce))
        response = requests.get(url)
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed get url: {}, status code: {}".format(url, response.status_code))
            raise FailedToCommunicateWithSystem(CIRRUS, url, response.status_code)
        self.cache.store_cache_result(url, response.text, WEEK)
        return response.text

    def check_if_valid_url(self, url):
        """This is a HEAD request to a given url to make sure it exists"""
        logger.debug("Issuing simple head request: {}".format(url))
        response = requests.head(url)
        return response.status_code == requests.codes["ok"]

    def __issue_cirrus_get_request(self, url):
        logger.debug("Issuing get request: {}".format(url))
        try:
            return self.cache.get_cache_result(url)
        except CacheMissException as ce:
            logger.debug(str(ce))
        response = requests.get(url, headers=self.__get_headers())
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed get webpage: {}, status code: {}".format(url, response.status_code))
            raise FailedToCommunicateWithSystem(CIRRUS, url, response.status_code)
        # logger.debug("FIELD_TYPE is: %s", response.text)
        self.cache.store_cache_result(url, response.json(), DAY_1)
        return response.json()

    def __issue_cirrus_post_request(self, url, data_dict, cache_expiry):
        logger.debug("Issuing post request: {}".format(url))
        logger.debug("Request headers are: {}".format(self.__get_headers()))
        cache_key = self.cache.generate_cache_key_for_post(url, data_dict)
        try:
            return self.cache.get_cache_result_via_key(cache_key)
        except CacheMissException as ce:
            logger.debug(str(ce))
        form_data = json.dumps(data_dict)
        logger.debug("Request data is: {}".format(form_data))
        response = requests.post(url, data=form_data, headers=self.__get_headers())
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed to issue post request to: {}, received error code: {}".format(url, response.status_code))
            if response.text:
                logger.error("Error response from server is: {}".format(response.json()))
            raise FailedToCommunicateWithSystem(CIRRUS, url, response.status_code)
        logger.debug("Response from server is: {}".format(response.text))
        self.cache.store_cache_result_with_key(cache_key, response.json(), cache_expiry)
        return response.json()

    def __get_url_and_issue_request(self, url_type, data_parameters_dict):
        config = self.__get_config_url(url_type)
        # TODO handle null where we fail to retrieve the given url_type, unlikely though
        if config.get(TYPE) == POST:
            cache_expiry = WEEK if url_type == "GET_MESSAGE_TRANSFORMS" else 30
            default_request_data = config.get(DATA_DICT)
            # Not additional information in the data_parameters_dict, could cause the post request schema failure
            merged_dict = {**default_request_data, **data_parameters_dict}
            return self.__issue_cirrus_post_request(config.get(URL), merged_dict, cache_expiry)
        else:
            url = config.get(URL).format(data_parameters_dict.get(MSG_UID))
            return self.__issue_cirrus_get_request(url)

    def search_for_messages(self, search_parameters):
        logger.info("Issue search for messages to cirrus")
        filtered_params = self.__filter_valid_search_params(search_parameters)
        return self.__get_url_and_issue_request("SEARCH_MESSAGES", filtered_params)

    def get_payloads_for_message(self, msg_uid):
        logger.info("Issue search for message payloads to cirrus")
        return self.__get_url_and_issue_request("GET_MESSAGE_PAYLOADS", {MSG_UID: msg_uid})

    def get_events_for_message(self, msg_uid):
        logger.info("Issue search for message events to cirrus")
        return self.__get_url_and_issue_request("GET_MESSAGE_EVENTS", {MSG_UID: msg_uid})

    def get_metadata_for_message(self, msg_uid):
        logger.info("Issue search for message metadata to cirrus")
        return self.__get_url_and_issue_request("GET_MESSAGE_METADATA", {MSG_UID: msg_uid})

    def get_transforms_for_message(self, search_parameters):
        logger.info("Issue search for message transforms to cirrus")
        filtered_params = self.__filter_valid_search_params(search_parameters)
        return self.__get_url_and_issue_request("GET_MESSAGE_TRANSFORMS", filtered_params)

    def get_message_by_uid(self, msg_uid):
        logger.info("Issue search for message id to cirrus")
        return self.__get_url_and_issue_request("FIND_MESSAGE_BY_ID", {MSG_UID: msg_uid})

    def __generate_auth_string(self):
        config_credentials = self.configuration.get(CREDENTIALS)[CIRRUS_CREDENTIALS]
        up_str = "{}:{}".format(config_credentials.get(USERNAME), config_credentials.get(PASSWORD))

        message_bytes = up_str.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
        logger.debug("Credentials encoded as: {}".format(base64_message))

        return "Basic {}".format(base64_message)

    def __get_cached_cookies(self):
        return read_cookies_file(self.configuration)

    def __get_config_url(self, url_name):
        configured_urls = self.configuration.get(URLS)
        for config_url in configured_urls:
            if config_url[NAME] == url_name:
                return config_url
        return None

    def __filter_valid_search_params(self, search_parameters_dict):
        """Ensure we only send valid search parameters to cirrus else we will break the schema if additional items are sent"""
        return {k:v for (k, v) in search_parameters_dict.items() if k in VALID_CIRRUS_SEARCH_FIELDS}
