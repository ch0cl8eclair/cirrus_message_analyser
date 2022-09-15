import argparse
import json

import requests
import urllib3
from bs4 import BeautifulSoup, Tag

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE, get_configuration_dict
from main.config.constants import URLS, URL, CREDENTIALS, USERNAME, PASSWORD, \
    ICE_CREDENTIALS, ADM_CREDENTIALS, PROJECTS, NAME, DataType, ICE, SEC_30, REGION, ADAPTER_ID, SOURCE, DESTINATION, \
    TYPE, MESSAGE_ID_HEADING, EVENT_DATE_HEADING, ICE_LOGIN, ICE_SUBMIT, ADM_LOGIN, ADM_SUBMIT, ADM_LOCATIONS, \
    ADM_CONFIGS, ADM_VERSIONS, ADM_SCRIPTS, ADM_ARTIFACTS, ICE_FAILED_MESSAGES, ICE_CALM_DASHBOARD, WEEK, ADM_CFG, ENV, \
    CONFIG, GET, OPTIONS
from main.formatter.formatter import Formatter
from main.http.cirrus_session_proxy import obtain_cookies_from_cirrus_driver, \
    capture_site_cookies_from_session
from main.http.proxy_cache import FailedToCommunicateWithSystem, ProxyCache
from main.model.model_utils import CacheMissException
from main.utils.utils import get_configuration_for_app, get_config_endpoint, form_system_url, unpack_endpoint_cfg, \
    unpack_config, get_endpoint_url, update_session_with_cookie, cookies_file_exists

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import logging
from logging.config import fileConfig

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:7.0.1) Gecko/20100101 Firefox/7.0.1'}


fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')

ADM_PROJECTS = "adm-projects"


class WebPageParser:
    """Abstract class that serves as a base to allow data to be read from a website"""
    def __init__(self, config_site_code):
        self.config_site_code = config_site_code
        self.configuration = ConfigSingleton()
        self.session = requests.session()
        self.session.headers.update(headers)
        self.initialised = False
        self.cache = ProxyCache()

    def get_app_config(self, format_options):
        app_cfg = get_configuration_for_app(self.configuration, self.config_site_code, format_options.get(ENV), format_options.get(REGION))
        return app_cfg

    def get_app_endpoint(self, endpoint_name):
        submit_endpoint_cfg = get_config_endpoint(self.configuration, self.config_site_code, endpoint_name)
        return unpack_endpoint_cfg(submit_endpoint_cfg)

    def get_app_endpoint_url(self, app_cfg, endpoint_name):
        endpoint_cfg = get_config_endpoint(self.configuration, self.config_site_code, endpoint_name)
        endpoint_url = form_system_url(app_cfg.get(self.config_site_code).get(CONFIG), unpack_endpoint_cfg(endpoint_cfg))
        return endpoint_url

    def get_app_endpoint_url2(self, endpoint_name, merged_app_cfg):
        endpoint_url = get_endpoint_url(self.configuration, merged_app_cfg, self.config_site_code, endpoint_name)
        return endpoint_url

    def get_config_for_website(self, url_name):
        sites_cfg = self.configuration.get(URLS)
        for site in sites_cfg:
            if site["name"] == url_name:
                return site
        return None

    def _get_url_by_name(self, url_name):
        site_config = self.get_config_for_website(url_name)
        return site_config[URL]

    def _get_default_cache_duration(self):
        return WEEK

    @staticmethod
    def pretty_print_request(req):
        """
        At this point it is completely built and ready
        to be fired; it is "prepared".

        However pay attention at the formatting used in
        this function because it is programmed to be pretty
        printed and may differ from the actual request.
        """
        logger.debug('{}\n{}\r\n{}\r\n\r\nBody: [{}]\r\n{}\n'.format(
            '-----------START-----------',
            req.method + ' ' + req.url,
            '\r\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
            req.body,
            '-----------END-----------',
            ))

    def issue_get_request(self, url, merged_app_cfg):
        logger.debug("Issuing webpage request: GET {}".format(url))
        # Check the cache first. Don't use cache until user has logged in.
        if self.initialised:
            try:
                return self.cache.get_cache_result(url)
            except CacheMissException as ce:
                pass

        get = self.session.get(url, verify=False)
        WebPageParser.pretty_print_request(get.request)
        if get.status_code != requests.codes["ok"]:
            logger.error("Failed get webpage: {}, status code: {}".format(url, get.status_code))
            raise FailedToCommunicateWithSystem(self.config_site_code, url, get.status_code)
        # cache the get result
        if self.initialised:
            self.cache.store_cache_result(url, get.text, self._get_default_cache_duration())
        return get.text

    def issue_post_request(self, url, merged_app_cfg, data_dict):
        logger.debug("Issuing webpage request: POST {}".format(url))

        post = self.session.post(url, data=data_dict, verify=False)
        WebPageParser.pretty_print_request(post.request)
        if post.status_code != requests.codes["ok"]:
            logger.error("Failed to issue request successfully: {}, {}".format(url, post.status_code))
            raise FailedToCommunicateWithSystem(self.config_site_code, url, post.status_code)
        return post.text

    def parse_data_page(self, url, merged_app_cfg, endpoint_cfg=None):
        endpoint_type = GET
        if endpoint_cfg:
            endpoint_type = endpoint_cfg.get(TYPE)

        if endpoint_type == GET:
            site_text = self.issue_get_request(url, merged_app_cfg)
        else:
            site_text = self.issue_post_request(url, merged_app_cfg, None)
        logger.debug("Attempting to parse page text: {}".format(site_text[0:100].encode()))
        soup = BeautifulSoup(site_text, features="html.parser")
        return soup

    def login_to_site(self, merged_app_cfg):
        submit_url = get_endpoint_url(self.configuration, merged_app_cfg, self.config_site_code, self.submit_url)
        login_url = get_endpoint_url(self.configuration, merged_app_cfg, self.config_site_code, self.login_url)
        logger.debug("Logging into site: {}".format(submit_url))
        self.issue_post_request(
            submit_url,
            merged_app_cfg,
            self.update_with_site_credentials(self.generate_login_form_data(login_url, merged_app_cfg), merged_app_cfg)
        )
        logger.debug("Login to site completed")

    def initialise(self, merged_app_cfg):
        """This could throw a FailedToCommunicateWithSystem"""
        logger.debug(f"Initialising class: {self.__class__.__name__}, config site code is: {self.config_site_code}, initializsed: {self.initialised}")
        # check if we login in previously by checking for the cookie in our cache
        env = unpack_config(merged_app_cfg, self.config_site_code, OPTIONS, ENV)
        region = unpack_config(merged_app_cfg, self.config_site_code, OPTIONS, REGION)

        already_logged_in = cookies_file_exists(self.configuration, self.config_site_code, env, region)
        if already_logged_in:
            logger.debug("Skipping login with cached session cookie")
            # Update session with cached cookie
            env = unpack_config(merged_app_cfg, self.config_site_code, OPTIONS, ENV)
            region = unpack_config(merged_app_cfg, self.config_site_code, OPTIONS, REGION)
            update_session_with_cookie(self.configuration, self.session, self.config_site_code, env, region)
            self.initialised = True
        else:
            if not self.initialised:
                self.login_to_site(merged_app_cfg)
                capture_site_cookies_from_session(self.configuration, self.session, self.config_site_code, merged_app_cfg)
                self.initialised = True

    def generate_login_form_data(self, login_form_url, merged_app_cfg):
        soup = self.parse_data_page(login_form_url, merged_app_cfg)
        svars = {}
        if soup:
            for var in soup.findAll('input', type="hidden"):
                svars[var['name']] = var['value']
        return svars

    def update_with_site_credentials(self, form_data, merged_app_cfg):
        logger.debug(f"Obtaining credentials for site: {self.config_site_code} ")
        username = unpack_config(merged_app_cfg, self.config_site_code, CREDENTIALS, USERNAME)
        password = unpack_config(merged_app_cfg, self.config_site_code, CREDENTIALS, PASSWORD)

        form_data["username"] = username
        form_data["password"] = password
        form_data["submit"] = "Login"
        return form_data
