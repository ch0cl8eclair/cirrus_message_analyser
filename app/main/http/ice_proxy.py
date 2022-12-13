import argparse
import json

import urllib3
from bs4 import Tag

from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.config.constants import *
from main.formatter.formatter import Formatter
from main.http.proxy_cache import FailedToCommunicateWithSystem
from main.http.webpage_proxy import WebPageParser
from main.model.model_utils import CacheMissException
from main.utils.utils import get_configuration_for_app, unpack_config, get_merged_app_cfg, error_and_exit

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import logging
from logging.config import fileConfig

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:7.0.1) Gecko/20100101 Firefox/7.0.1'}

LOGGING_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../../resources/logging_config.ini')
fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')


class ICEProxy(WebPageParser):
    """All fetch functionality for ICE Dashboard access"""

    COMMUNITY_HEADING = "Community"
    IN_PROCESS_HEADING = "In Progress Messages"
    FAILED_HEADING = "Failed Event Messages"
    VIEW_SUMMARY = "view summary"
    HEARTBEAT_HEADING = "Heartbeat Failures"
    ALERTS_HEADING = "CALM Alerts"

    ADAPTER_ID_HEADING = 'Adapter ID'
    SERVICE_HEADING = 'Service Details'
    SOURCE_HEADING = 'Source'
    DESTINATION_HEADING = 'Destination'
    MESSAGE_TYPE_HEADING = 'Message Type'
    REGION_HEADING = 'Region'
    DELETE_HEADING = 'Delete'

    COUNT_HEADING = 'Count'
    OLDEST_DATE_HEADING = 'Oldest Date'
    NEWEST_DATE_HEADING = 'Newest Date'
    SERVICE_CLASS_HEADING = 'Service Class'
    NOTES_HEADING = 'Notes'
    SUMMARY_HEADING = 'Summary'


    CALM_DASHBOARD_COLUMNS_MAP = {COMMUNITY_HEADING: 0, IN_PROCESS_HEADING: 1, FAILED_HEADING: 2, HEARTBEAT_HEADING: 3, ALERTS_HEADING: 4}
#    FAILED_MESSAGES_COLUMNS_MAP = {EVENT_DATE_HEADING: 0, MESSAGE_ID_HEADING: 1, ADAPTER_ID_HEADING: 2, SERVICE_HEADING: 3, SOURCE_HEADING: 4, DESTINATION_HEADING: 5, MESSAGE_TYPE_HEADING: 6, REGION_HEADING: 7, DELETE_HEADING: 8}
    FAILED_MESSAGES_COLUMNS_MAP = {COUNT_HEADING: 0, OLDEST_DATE_HEADING: 1, NEWEST_DATE_HEADING: 2, ADAPTER_ID_HEADING: 3, SOURCE_HEADING: 4, DESTINATION_HEADING: 5, MESSAGE_TYPE_HEADING: 6, SERVICE_CLASS_HEADING: 7, NOTES_HEADING: 8, SUMMARY_HEADING: 9, DELETE_HEADING: 10}
    ICE_UNDEFINED_VALUES = ["NA", "Not Available"]

    def __init__(self):
        WebPageParser.__init__(self, "ICE")
        self.credentials_section_name = ICE_CREDENTIALS
        self.login_url = ICE_LOGIN
        self.submit_url = ICE_SUBMIT

    def _filter_dashboard_data_for_region(self, data_item, region_code):
        if region_code:
            return data_item.get(self.COMMUNITY_HEADING, "") == region_code
        return True

    def get_failure_count_for_region(self, dashboard_data, region_code):
        filtered_list = [x for x in dashboard_data if self._filter_dashboard_data_for_region(x, region_code)]
        logger.info("{} vs {}".format(len(dashboard_data), len(filtered_list)))
        return next((int(x.get(self.FAILED_HEADING, 0)) for x in dashboard_data if self._filter_dashboard_data_for_region(x, region_code)), 0)

    def _map_column_index_to_name(self, columns_map, column_index):
        for k, v in columns_map.items():
            if v == column_index:
                return k
        return None

    def _get_default_cache_duration(self):
        return SEC_30

    def get_failed_messages_data(self, merged_app_cfg):
        region_code = unpack_config(merged_app_cfg, self.config_site_code, OPTIONS, REGION)
        logger.debug("Attempting to retrieve failed message for region: {}".format(region_code))
        target_endpoint_name = ICE_FAILED_MESSAGES
        url_base = self.get_app_endpoint_url2(target_endpoint_name, merged_app_cfg)
        endpoint_cfg = self.get_app_endpoint(target_endpoint_name)
        url = url_base.format(region_code)
        soup = self.parse_data_page(url, merged_app_cfg)
        main_panel = soup.find("div", class_="panel-body")
        table_dict_list = []
        if main_panel:
            thead = main_panel.find("thead")
            if thead:
                first_header_row = thead.find("tr")
                headings = first_header_row.find_all("td")
                heading_data = [item.get_text() for item in headings]
                print(heading_data)
            tbody = main_panel.find("tbody")
            table_dict_list = self._obtain_table_data(tbody, self.FAILED_MESSAGES_COLUMNS_MAP)
        logger.debug("Found {} failed messages for region: {}".format(len(table_dict_list), region_code))
        return table_dict_list

    def _obtain_table_data(self, soup_table_body, columns_map):
        table_dict_list = []
        column_count = len(columns_map.keys())
        if soup_table_body:
            table_rows = soup_table_body.find_all("tr")
            if table_rows:
                for row_count, table_row in enumerate(table_rows):
                    row_dict = {}
                    column_data = table_row.find_all("td")
                    if len(column_data) < column_count - 1:
                        continue
                    for col_index, column_item_child in enumerate(column_data):
                        if isinstance(column_item_child, Tag):
                            column_value = column_item_child.get_text().strip().replace(self.VIEW_SUMMARY, '')
                            field_name = self._map_column_index_to_name(columns_map, col_index)
                            if field_name == ICEProxy.COUNT_HEADING and column_value == "Delete":
                                logger.debug(f"Something off in row: {row_count}")
                            if field_name in [ICEProxy.NOTES_HEADING, ICEProxy.DELETE_HEADING, ICEProxy.SUMMARY_HEADING]:
                                column_value = ""
                            if field_name:
                                row_dict[field_name] = column_value
                            else:
                                logger.warning("Failed to find field name for col index: {}".format(col_index))
                    table_dict_list.append(row_dict)
        return table_dict_list

    def get_calm_dashboard_data(self, merged_app_cfg):
        logger.debug("Attempting to retrieve calm dashboard data")
        dashboard_url = self.get_app_endpoint_url2(ICE_CALM_DASHBOARD, merged_app_cfg)
        try:
            return self.cache.get_cache_result(dashboard_url)
        except CacheMissException as ce:
            logger.debug(str(ce))
        soup = self.parse_data_page(dashboard_url, merged_app_cfg)
        main_panel = soup.find("div", class_="panel-body")
        if not main_panel:
            if "To access this page, you need to" in soup.get_text():
                logger.error("Need to login to site!")
            error_and_exit("Failed to retrieve page as expected!")
        thead = main_panel.find("thead")
        if thead:
            first_header_row = thead.find("tr")
            headings = first_header_row.find_all("th")
            heading_data = [item.get_text() for item in headings]
        tbody = main_panel.find("tbody")
        table_dict_list = self._obtain_table_data(tbody, self.CALM_DASHBOARD_COLUMNS_MAP)
        self.cache.store_cache_result(dashboard_url, table_dict_list, SEC_30)
        return table_dict_list

    def list_messages(self, search_criteria, merged_app_cfg):
        logger.info("Checking failed messages count from ICE")
        dashboard_stats = self.get_calm_dashboard_data(merged_app_cfg)
        region_code = search_criteria.get(REGION)
        region_failed_msg_count = self.get_failure_count_for_region(dashboard_stats, region_code)
        if region_code and region_failed_msg_count:
            logger.info("Getting failed messages from ICE")
            failed_details = self.get_failed_messages_data(merged_app_cfg)
            logger.info("Filtering failed messages")
            return self._filter_failed_messages(failed_details, search_criteria)
        return []

    def _filter_failed_messages(self, messages, search_criteria):
        filtered_messages = []
        for current_message in messages:
            filter_flags = [self._filter_message(current_message, search_criteria, self.ADAPTER_ID_HEADING, ADAPTER_ID),
                            self._filter_message(current_message, search_criteria, self.SOURCE_HEADING, SOURCE),
                            self._filter_message(current_message, search_criteria, self.DESTINATION_HEADING, DESTINATION),
                            self._filter_message(current_message, search_criteria, self.MESSAGE_TYPE_HEADING, TYPE)]
            if all(filter_flags):
                filtered_messages.append(current_message)
        logger.info("Failed messages have been filtered from {} to {}".format(len(messages), len(filtered_messages)))
        return filtered_messages

    def _filter_message(self, message, search_criteria, message_field_name, search_criteria_field_name):
        search_string = search_criteria.get(search_criteria_field_name, None)
        message_string = message.get(message_field_name, None)
        if search_string:
            if message_string:
                message_undefined = message_string in self.ICE_UNDEFINED_VALUES
                return not message_undefined and (search_string == message_string)
        return True


def main():
    config = ConfigSingleton(get_configuration_dict())

    parser = argparse.ArgumentParser(description="This is a program to make it easier to get information from gitlab")
    parser.add_argument("--verbose", "-v", help="show extra details", action="store_true")
    parser.add_argument("--project", "-p", help="project name")
    parser.add_argument("--group", "-g", help="project group name eg proagrica-network")
    args = parser.parse_args()

    verbose = True if args.verbose else False

    ice_proxy = ICEProxy()
    formatter = Formatter()
    region = "US"
    format_options = {'output': 'table', 'quiet': False, 'verbose': False, 'env': 'PRD', 'region': region}
    merged_app_cfg = get_merged_app_cfg(config, ICE_CFG, format_options)

    try:
        ice_proxy.initialise(merged_app_cfg)
    except FailedToCommunicateWithSystem as err:
        logger.error(str(err))

    results = ice_proxy.get_calm_dashboard_data(merged_app_cfg)
    print(json.dumps(results))
    formatter.format(DataType.ice_dashboard, results, format_options)

    if ice_proxy.get_failure_count_for_region(results, region) > 0:
        failed_details = ice_proxy.get_failed_messages_data(merged_app_cfg)
        formatter.format(DataType.ice_failed_messages, failed_details, format_options)
    else:
        print("No failures found on dashboard for region: {}".format(region))

    # Fetch ADM login url
    # r = session.get(login_url)
    # if r.status_code != requests.codes["ok"]:
    #     print("Failed to load login page: {}".format(login_url), file=sys.stderr)
    #     exit(-1)
    # Pull out all the input field incl csrf_token
    # soup = BeautifulSoup(r.content, features="html.parser")
    # svars = {}
    # for var in soup.findAll('input', type="hidden"):
    #     svars[var['name']] = var['value']

    # Now add in our credential from the config file
    # config_file = os.path.join(os.path.dirname(__file__), CREDENTIALS_FILE)
    # credentials_data = parse_json_from_file(CREDENTIALS_FILE)
    # for item in credentials_data:
    #     if item['type'] == 'ADM':
    #         svars["username"] = item["username"]
    #         svars["password"] = item["password"]
    #         break
    # svars["submit"] = "Login"
    # # print(svars)

    # Issue the login request
    # print("Issuing login request...")
    # post = session.post(login_submit_url, data=svars)
    # if post.status_code != requests.codes["ok"]:
    #     print("Failed to login successfully: {}".format(login_submit_url), file=sys.stderr)
    #     exit(-1)
    # now issue the request we are interested in
    # print("Issuing adm locations request...")
    # soup = adm_proxy.parse_data_page(locations_url)
    # r = session.get(locations_url)
    # if r.status_code != requests.codes["ok"]:
    #     print("Failed get locations post login: {}".format(locations_url), file=sys.stderr)
    #     exit(-1)

    # 1 - convert the retrieved response into simple html, as it is a html response with encoded html!?!
    # print(r.content)
    # features="html.parser"
    # with open("c:/temp/python-php-locations0.html", "w") as outputfile:
    #     outputfile.write(r.text)
    #
    # soup2 = BeautifulSoup(r.text)
    # with open("c:/temp/python-php-locations1.html", "w") as outputfile:
    #     outputfile.write(soup2.get_text())

    # soup = BeautifulSoup(r.text, features="html.parser")
    # with open("c:/temp/python-php-locations2.html", "w") as outputfile:
    #     outputfile.write(soup.get_text())

    # Parse the config file
    # parse_config()
    # if args.project:
    #     format_records(adm_proxy.get_locations_for_project(args.project), verbose)
    # if args.group:
    #     format_records(adm_proxy.get_locations_for_group(args.group), verbose)


if __name__ == '__main__':
    main()
