from urllib.parse import urlencode, urlparse, urlunparse, parse_qs, quote

import requests
import urllib3
from requests.compat import urljoin

from main.cli.cli_parser import LOKI
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
from main.config.constants import WEEK, CONFIG, ENV, BASE_URL, \
    START_DATE, END_DATE, QUERY
from main.http.proxy_cache import FailedToCommunicateWithSystem
from main.utils.utils import unpack_config, \
    get_configuration_for_app, parse_datetime_from_zulu, convert_datetime_to_unix

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')

LOKI_API_V1 = "/api/datasources/proxy/2/loki/api/v1/"
LOKI_SEARCH_ENDPOINT = "query_range"


class LokiProxy:

    def __init__(self):
        self.configuration = ConfigSingleton()

    def fetch_logs(self, search_parameters):
        query_str = search_parameters.get(QUERY)
        start_date = search_parameters.get(START_DATE)
        to_date = search_parameters.get(END_DATE)
        env = search_parameters.get(ENV, "*")

        target_url = self.get_endpoint_url(env, query_str, start_date, to_date)
        logger.debug(parse_qs(target_url))
        result = self.execute_loki_request(target_url, self.get_body(), self.get_headers())
        return result

    def get_endpoint_url(self, env, query_str, start_date, to_date):
        app_cfg = get_configuration_for_app(self.configuration, LOKI, env, "*")
        env_base_url = unpack_config(app_cfg, LOKI, CONFIG, BASE_URL)
        join_url = urljoin(urljoin(env_base_url, LOKI_API_V1), LOKI_SEARCH_ENDPOINT)
        query_args = {'query': query_str}
        # query_args = {'query': query_str, 'from': self.convert_datetime_to_unix(start_date), 'to': self.convert_datetime_to_unix(to_date)}
        target_url = self.build_url(join_url, query_args)
        return target_url

    def build_url(self, base_url, args_dict):
        return base_url.rstrip('?') + '?' + urlencode(args_dict, quote_via=quote, doseq=True)

    def get_headers(self):
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache'
        }
        return headers

    def get_body(self):
        return None

    def execute_loki_request(self, url, form_data, headers):
        """Issue a simple http request to perform query"""
        logger.debug("Issuing loki POST request: {}".format(url))

        response = requests.get(url, headers=headers, verify=False)
        if response.status_code != requests.codes["ok"]:
            logger.error("Failed to issue request to: {}, received error code: {}".format(url, response.status_code))
            if response.text:
                logger.error("Error response from server is: {}".format(response.text.strip()[0:200]))
            raise FailedToCommunicateWithSystem(LOKI, url, response.status_code)
        return response.json()

    def convert_datetime_to_unix(self, datetime_str):
        datetime_obj = parse_datetime_from_zulu(datetime_str)
        return convert_datetime_to_unix(datetime_obj)


if __name__ == '__main__':
    url = "https://grafana-eks-2.aga.eu-west-1.dsg.lnrsg.io/api/datasources/proxy/2/loki/api/v1/query_range"
    print(f"Attempting to call url: {url}")
    params = {"query": '{namespace="omnichannel-test",app="adapter"}|="msg produced"|logfmt'}
    target_url = url.rstrip('?') + '?' + urlencode(params, quote_via=quote, doseq=True)
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    res = requests.get(target_url, headers=headers, verify=False)
    print(f"status is {res.status_code}")
    print("Pyth request was: /api/datasources/proxy/2/loki/api/v1/query_range?" + urlencode(params, quote_via=quote))
    if res.status_code == 200:
        print(res.json())
    curl_data  = "/api/datasources/proxy/2/loki/api/v1/query_range?query=%7Bnamespace%3D%22omnichannel-test%22%2Capp%3D%22adapter%22%7D%7C%3D%22msg%20produced%22%7Clogfmt"
    curl_data2 = "/api/datasources/proxy/2/loki/api/query_range?query=%7Bnamespace%3D%22omnichannel-test%22%2Capp%3D%22adapter%22%7D%7C%3D%22msg%20produced%22"
    # print(f"Curl request was: {curl_data}")
    # res2 = requests.get("https://grafana-eks-2.aga.eu-west-1.dsg.lnrsg.io" + curl_data, headers=headers, verify=False)
    # print(f"status is {res2.status_code}")