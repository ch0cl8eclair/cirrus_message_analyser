import base64
import json

import requests
import urllib3

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import CREDENTIALS, USERNAME, PASSWORD, NAME, TYPE, POST, DATA_DICT, MSG_UID, WEEK, DAY_1, \
    MESSAGE_STATUS, DESTINATION, SOURCE, CIRRUS, CIRRUS_CFG, CONFIG, ENV, OPTIONS, REGION, PRD, DEV
from main.http.proxy_cache import ProxyCache, FailedToCommunicateWithSystem
from main.model.model_utils import CacheMissException
from main.utils.utils import get_config_endpoint, unpack_endpoint_cfg, form_system_url, unpack_config, read_cookies_file

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')

VALID_CIRRUS_SEARCH_FIELDS = [SOURCE, DESTINATION, TYPE, MESSAGE_STATUS]


class CirrusProxy:

    def __init__(self):
        self.configuration = ConfigSingleton()
        self.cache = ProxyCache()

    def __get_headers(self, merged_app_cfg):
        env = unpack_config(merged_app_cfg, CIRRUS_CFG, OPTIONS, ENV)
        region = unpack_config(merged_app_cfg, CIRRUS_CFG, OPTIONS, REGION)
        cookie = self.__get_cached_cookies(merged_app_cfg)
        logger.debug(f"Cooked returned as: [{cookie}]")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': self.__generate_auth_string(merged_app_cfg),
            'Cookie': cookie,
            'Cache-Control': 'no-cache'
        }
        if env == 'EU' and region == PRD:
            headers['Tenant'] = 'eu0000000001'
        if env == 'EU' and region == DEV:
            headers['Tenant'] = 'pn0000000015'
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

    def __issue_cirrus_get_request(self, url, merged_app_cfg):
        logger.debug("Issuing get request: {}".format(url))
        try:
            return self.cache.get_cache_result(url)
        except CacheMissException as ce:
            logger.debug(str(ce))
        response = requests.get(url, headers=self.__get_headers(merged_app_cfg))
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed get webpage: {}, status code: {}".format(url, response.status_code))
            raise FailedToCommunicateWithSystem(CIRRUS, url, response.status_code)
        # logger.debug("FIELD_TYPE is: %s", response.text)
        self.cache.store_cache_result(url, response.json(), DAY_1)
        return response.json()

    def __issue_cirrus_post_request(self, url, data_dict, cache_expiry, merged_app_cfg):
        logger.debug("Issuing post request: {}".format(url))
        headers = self.__get_headers(merged_app_cfg)
        logger.debug("Request headers are: {}".format(headers))
        cache_key = self.cache.generate_cache_key_for_post(url, data_dict)
        try:
            return self.cache.get_cache_result_via_key(cache_key)
        except CacheMissException as ce:
            logger.debug(str(ce))
        form_data = json.dumps(data_dict)
        logger.debug("Request data is: {}".format(form_data))
        response = requests.post(url, data=form_data, headers=headers, verify=False)
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed to issue post request to: {}, received error code: {}".format(url, response.status_code))
            if response.text:
                logger.error("Error response from server is: {}".format(response.text.strip()[0:200]))
            raise FailedToCommunicateWithSystem(CIRRUS, url, response.status_code)
        logger.debug("Response from server is: {}".format(response.text))
        self.cache.store_cache_result_with_key(cache_key, response.json(), cache_expiry)
        return response.json()

    def __get_target_system_and_issue_request(self, data_parameters_dict, merged_app_cfg, endpoint_cfg):
        # TODO handle null where we fail to retrieve the given url_type, unlikely though
        target_endpoint = unpack_endpoint_cfg(endpoint_cfg)
        target_url = form_system_url(merged_app_cfg.get(CIRRUS_CFG).get(CONFIG), target_endpoint)
        if target_endpoint.get(TYPE) == POST:
            cache_expiry = WEEK if target_endpoint.get(NAME) == "GET_MESSAGE_TRANSFORMS" else 30
            default_request_data = target_endpoint.get(DATA_DICT)
            # Not additional information in the data_parameters_dict, could cause the post request schema failure
            merged_dict = {**default_request_data, **data_parameters_dict}
            return self.__issue_cirrus_post_request(target_url, merged_dict, cache_expiry, merged_app_cfg)
        else:
            # url is formed of base url and endpoint url
            url = target_url.format(data_parameters_dict.get(MSG_UID))
            return self.__issue_cirrus_get_request(url, merged_app_cfg)

    def search_for_messages(self, search_parameters, merged_app_cfg):
        logger.info("Issue search for messages to cirrus")
        filtered_params = self.__filter_valid_search_params(search_parameters)
        endpoint_name = "SEARCH_MESSAGES"
        endpoint_cfg = get_config_endpoint(self.configuration, CIRRUS_CFG, endpoint_name)
        return self.__get_target_system_and_issue_request(filtered_params, merged_app_cfg, endpoint_cfg)

    def get_payloads_for_message(self, msg_uid, merged_app_cfg):
        logger.info("Issue search for message payloads to cirrus")
        endpoint_name = "GET_MESSAGE_PAYLOADS"
        request_params = {MSG_UID: msg_uid}
        endpoint_cfg = get_config_endpoint(self.configuration, CIRRUS_CFG, endpoint_name)
        return self.__get_target_system_and_issue_request(request_params, merged_app_cfg, endpoint_cfg)

    def get_events_for_message(self, msg_uid, merged_app_cfg):
        logger.info("Issue search for message events to cirrus")
        endpoint_name = "GET_MESSAGE_EVENTS"
        request_params = {MSG_UID: msg_uid}
        endpoint_cfg = get_config_endpoint(self.configuration, CIRRUS_CFG, endpoint_name)
        return self.__get_target_system_and_issue_request(request_params, merged_app_cfg, endpoint_cfg)

    def get_metadata_for_message(self, msg_uid, merged_app_cfg):
        logger.info("Issue search for message metadata to cirrus")
        endpoint_name = "GET_MESSAGE_METADATA"
        request_params = {MSG_UID: msg_uid}
        endpoint_cfg = get_config_endpoint(self.configuration, CIRRUS_CFG, endpoint_name)
        return self.__get_target_system_and_issue_request(request_params, merged_app_cfg, endpoint_cfg)

    def get_transforms_for_message(self, search_parameters, merged_app_cfg):
        logger.info("Issue search for message transforms to cirrus")
        filtered_params = self.__filter_valid_search_params(search_parameters)
        endpoint_name = "GET_MESSAGE_TRANSFORMS"
        endpoint_cfg = get_config_endpoint(self.configuration, CIRRUS_CFG, endpoint_name)
        return self.__get_target_system_and_issue_request(filtered_params, merged_app_cfg, endpoint_cfg)

    def get_message_by_uid(self, msg_uid, merged_app_cfg):
        logger.info("Issue search for message id to cirrus")
        endpoint_name = "FIND_MESSAGE_BY_ID"
        request_params = {MSG_UID: msg_uid}
        endpoint_cfg = get_config_endpoint(self.configuration, CIRRUS_CFG, endpoint_name)
        return self.__get_target_system_and_issue_request(request_params, merged_app_cfg, endpoint_cfg)

    def __generate_auth_string(self, merged_app_cfg):
        username = unpack_config(merged_app_cfg, CIRRUS_CFG, CREDENTIALS, USERNAME)
        password = unpack_config(merged_app_cfg, CIRRUS_CFG, CREDENTIALS, PASSWORD)
        up_str = "{}:{}".format(username, password)

        message_bytes = up_str.encode('ascii')
        base64_bytes = base64.b64encode(message_bytes)
        base64_message = base64_bytes.decode('ascii')
        logger.debug("Credentials encoded as: {}".format(base64_message))

        return "Basic {}".format(base64_message)

    def __get_cached_cookies(self, merged_app_cfg):
        env = unpack_config(merged_app_cfg, CIRRUS_CFG, OPTIONS, ENV)
        region = unpack_config(merged_app_cfg, CIRRUS_CFG, OPTIONS, REGION)
        return read_cookies_file(self.configuration, CIRRUS_CFG, env, region)

    # def __get_config_url(self, url_name):
    #     configured_urls = self.configuration.get(URLS)
    #     for config_url in configured_urls:
    #         if config_url[NAME] == url_name:
    #             return config_url
    #     return None

    def __filter_valid_search_params(self, search_parameters_dict):
        """Ensure we only send valid search parameters to cirrus else we will break the schema if additional items are sent"""
        return {k:v for (k, v) in search_parameters_dict.items() if k in VALID_CIRRUS_SEARCH_FIELDS}
