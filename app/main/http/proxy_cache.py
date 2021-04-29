import json
import urllib

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import CACHE_REF
from main.model.model_utils import CacheMissException
import logging
from logging.config import fileConfig
fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')


class ProxyCache:

    def __init__(self):
        self.configuration = ConfigSingleton()

    def __get_cache(self):
        if self.configuration.has_key(CACHE_REF):
            return self.configuration.get(CACHE_REF)
        # Exceptions for unit tests
        raise CacheMissException("No cache configured")

    def __generate_cache_key(self, url):
        return url

    def __generate_cache_key_with_dict(self, url, form_dict):
        return "{}:{}".format(url, urllib.parse.urlencode(form_dict))

    def __get_cache_value_if_present(self, cache_key):
        if cache_key in self.__get_cache():
            return self.__get_cache()[cache_key]
        raise CacheMissException(cache_key)

    def __store_cache(self, key, value, expiry_secs):
        try:
            self.__get_cache().set(key, value, expire=expiry_secs)
        except CacheMissException:
            pass

    def get_cache_result(self, url):
        logger.debug(f"Getting cached result for key: {url}")
        cache_key = self.__generate_cache_key(url)
        return self.get_cache_result_via_key(cache_key)

    def get_cache_result_dict(self, url):
        return json.loads(self.get_cache_result(url))

    def get_cache_result_via_key(self, cache_key):
        try:
            return self.__get_cache_value_if_present(cache_key)
        except CacheMissException as ce:
            raise ce

    def store_cache_result(self, url, data, duration):
        logger.debug(f"Storing cache for key: {url}")
        cache_key = self.__generate_cache_key(url)
        self.__store_cache(cache_key, data, duration)

    def store_cache_result_dict(self, url, data, duration):
        self.store_cache_result(url, json.dumps(data), duration)

    def store_cache_result_with_key(self, cache_key, data, duration):
        self.__store_cache(cache_key, data, duration)

    def generate_cache_key_for_post(self, url, form_dict):
        cache_key = self.__generate_cache_key_with_dict(url, form_dict)
        return cache_key


class FailedToCommunicateWithSystem(Exception):
    """Exception raised for failed communications with ICE"""

    def __init__(self, system, url, response_code):
        self.system = system
        self.url = url
        self.response_code = response_code

    def __str__(self):
        return "Failed to get success code from {}, url: {}, obtained: {}".format(self.system, self.url, self.response_code)