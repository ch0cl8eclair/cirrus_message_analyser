import argparse
import json

import requests
import urllib3
from bs4 import BeautifulSoup, Tag

from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE, get_configuration_dict
from main.config.constants import URLS, URL, CREDENTIALS, USERNAME, PASSWORD, \
    ICE_CREDENTIALS, ADM_CREDENTIALS, PROJECTS, NAME, DataType, ICE, SEC_30, REGION, ADAPTER_ID, SOURCE, DESTINATION, \
    TYPE, MESSAGE_ID_HEADING, EVENT_DATE_HEADING, ICE_LOGIN, ICE_SUBMIT, ADM_LOGIN, ADM_SUBMIT, ADM_LOCATIONS, \
    ADM_CONFIGS, ADM_VERSIONS, ADM_SCRIPTS, ADM_ARTIFACTS, ICE_FAILED_MESSAGES, ICE_CALM_DASHBOARD, WEEK
from main.formatter.formatter import Formatter
from main.http.proxy_cache import FailedToCommunicateWithSystem, ProxyCache
from main.model.model_utils import CacheMissException

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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

    def issue_get_request(self, url):
        logger.debug("Issuing webpage request: {}".format(url))
        # Check the cache first. Don't use cache until user has logged in.
        if self.initialised:
            try:
                return self.cache.get_cache_result(url)
            except CacheMissException as ce:
                pass
        get = self.session.get(url)
        if get.status_code != requests.codes["ok"]:
            logger.error("Failed get webpage: {}, status code: {}".format(url, get.status_code))
            raise FailedToCommunicateWithSystem(ICE, url, get.status_code)
        # cache the get result
        if self.initialised:
            self.cache.store_cache_result(url, get.text, self._get_default_cache_duration())
        return get.text

    def issue_post_request(self, url, data_dict):
        post = self.session.post(url, data=data_dict)
        if post.status_code != requests.codes["ok"]:
            logger.error("Failed to login successfully: {}".format(url))
            raise FailedToCommunicateWithSystem(ICE, url, post.status_code)

    def parse_data_page(self, url):
        site_text = self.issue_get_request(url)
        logger.debug("Attempting to parse page text: {}".format(site_text[0:100].encode()))
        soup = BeautifulSoup(site_text, features="html.parser")
        return soup

    def login_to_site(self):
        submit_url = self._get_url_by_name(self.submit_url)
        logger.debug("Logging into site: {}".format(submit_url))
        self.issue_post_request(
            submit_url,
            self.update_with_site_credentials(self.generate_login_form_data(self._get_url_by_name(self.login_url))
            )
        )
        logger.debug("Login to site completed")

    def initialise(self):
        """This could throw a FailedToCommunicateWithSystem"""
        if not self.initialised:
            self.login_to_site()
            self.initialised = True

    def generate_login_form_data(self, login_form_url):
        soup = self.parse_data_page(login_form_url)
        svars = {}
        if soup:
            for var in soup.findAll('input', type="hidden"):
                svars[var['name']] = var['value']
        return svars

    def update_with_site_credentials(self, form_data):
        # credentials_data = parse_json_from_file(CREDENTIALS_FILE)
        username = self.configuration.get(CREDENTIALS).get(self.credentials_section_name).get(USERNAME)
        password = self.configuration.get(CREDENTIALS).get(self.credentials_section_name).get(PASSWORD)

        form_data["username"] = username
        form_data["password"] = password
        form_data["submit"] = "Login"
        return form_data


class ADMProxy(WebPageParser):
    """All fetch functionality for ADM access"""
    ADM_FILTER_COLUMN_FOR_PROJECT_DICT = {ADM_LOCATIONS: 0, ADM_CONFIGS: 0, ADM_VERSIONS: 0, ADM_SCRIPTS: 1, ADM_ARTIFACTS: 1}

    def __init__(self):
        WebPageParser.__init__(self, "ADM")
        self.credentials_section_name = ADM_CREDENTIALS
        self.login_url = ADM_LOGIN
        self.submit_url = ADM_SUBMIT

    def fetch_locations(self):
        site_config = self.get_config_for_website()
        soup = self.parse_data_page(self._get_url_by_name(ADM_LOCATIONS))

    def fetch_header_data(self, soup):
        thead = soup.find("thead")
        if thead is None:
            logger.error("Failed to find thead tag in page!")
            return []
        header_row = thead.findChildren("tr")[0]
        return [td.get_text() for td in header_row.findChildren("td")]

    def fetch_project_fields(self, soup, filter_column, project_name, get_all=False, process_all_rows=False):
        result = []
        tbody = soup.find("tbody")
        if tbody is None:
            logger.error("Failed to find tbody tag in page!")
            return []
        # For page with dynamic table we need to fetch to rows from the top level not from the tbody
        # currently only an issues for adm configs page
        if process_all_rows:
            table_rows = soup.find_all("tr")
        else:
            table_rows = tbody.findChildren("tr")
        for row in table_rows:
            td_list = row.findChildren("td")
            parent_element_name = row.parent.name
            if row.parent.name != "thead":
                if get_all or td_list[filter_column].get_text() == project_name:
                    result.append([td.get_text() for td in td_list])
        return result

    def fetch_project_fields_for_project_group(self, soup, filter_column, project_names_list, process_all_rows=False):
        result = []
        tbody = soup.find("tbody")
        if tbody is None:
            logger.error("Failed to find tbody tag in page!")
            return []
        # For page with dynamic table we need to fetch to rows from the top level not from the tbody
        # currently only an issues for adm configs page
        if process_all_rows:
            table_rows = soup.find_all("tr")
        else:
            table_rows = tbody.findChildren("tr")
        for row in table_rows:
            td_list = row.findChildren("td")
            parent_element_name = row.parent.name
            if row.parent.name != "thead":
                if td_list[filter_column].get_text() in project_names_list:
                    result.append([td.get_text() for td in td_list])
        return result

    def get_data_for_project(self, url_key, project_name):
        soup = self.parse_data_page(self._get_url_by_name(url_key))
        filter_column = self.ADM_FILTER_COLUMN_FOR_PROJECT_DICT[url_key]
        data = self.fetch_project_fields(soup, filter_column, project_name, False, url_key == ADM_CONFIGS)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_configs(self):
        soup = self.parse_data_page(self._get_url_by_name(ADM_CONFIGS))
        data = self.fetch_project_fields(soup, -1, None, True, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_locations(self):
        soup = self.parse_data_page(self._get_url_by_name(ADM_LOCATIONS))
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_versions(self):
        soup = self.parse_data_page(self._get_url_by_name(ADM_VERSIONS))
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_scripts(self):
        soup = self.parse_data_page(self._get_url_by_name(ADM_SCRIPTS))
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_artifacts(self):
        soup = self.parse_data_page(self._get_url_by_name(ADM_ARTIFACTS))
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_locations_for_project(self, project_name):
        return self.get_data_for_project(ADM_LOCATIONS, project_name)

    def get_configs_for_project(self, project_name):
        return self.get_data_for_project(ADM_CONFIGS, project_name)

    def get_versions_for_project(self, project_name):
        return self.get_data_for_project(ADM_VERSIONS, project_name)

    def get_scripts_for_project(self, project_name):
        return self.get_data_for_project(ADM_SCRIPTS, project_name)

    def get_artifacts_for_project(self, project_name):
        return self.get_data_for_project(ADM_ARTIFACTS, project_name)

    def get_locations_for_group(self, group_name):
        return self.get_data_for_group(ADM_LOCATIONS, group_name)

    def get_configs_for_group(self, group_name):
        return self.get_data_for_group(ADM_CONFIGS, group_name)

    def get_versions_for_group(self, group_name):
        return self.get_data_for_group(ADM_VERSIONS, group_name)

    def get_scripts_for_group(self, group_name):
        return self.get_data_for_group(ADM_SCRIPTS, group_name)

    def get_artifacts_for_group(self, group_name):
        return self.get_data_for_group(ADM_ARTIFACTS, group_name)

    def get_data_for_group(self, url_key, group_name):
        soup = self.parse_data_page(self._get_url_by_name(url_key))
        requested_group_projects = [group[PROJECTS] for group in self.configuration.get(ADM_PROJECTS) if group[NAME] == group_name][0]
        filter_column = self.ADM_FILTER_COLUMN_FOR_PROJECT_DICT[url_key]
        if requested_group_projects:
            header_line = self.fetch_header_data(soup)
            data_lines = self.fetch_project_fields_for_project_group(soup, filter_column, requested_group_projects, url_key == ADM_CONFIGS)
            return [header_line] + data_lines
        else:
            logger.error("The given group: {} could not be found in the config".format(group_name))
        return None


class ICEProxy(WebPageParser):
    """All fetch functionality for ICE Dashboard access"""

    COMMUNITY_HEADING = "Community"
    IN_PROCESS_HEADING = "In Progress Messages"
    FAILED_HEADING = "Failed Event Messages"
    HEARTBEAT_HEADING = "Heartbeat Failures"
    ALERTS_HEADING = "CALM Alerts"

    ADAPTER_ID_HEADING = 'Adapter ID'
    SERVICE_HEADING = 'Service Details'
    SOURCE_HEADING = 'Source'
    DESTINATION_HEADING = 'Destination'
    MESSAGE_TYPE_HEADING = 'Message Type'
    REGION_HEADING = 'Region'
    DELETE_HEADING = 'Delete'

    CALM_DASHBOARD_COLUMNS_MAP = {COMMUNITY_HEADING: 0, IN_PROCESS_HEADING: 1, FAILED_HEADING: 2, HEARTBEAT_HEADING: 3, ALERTS_HEADING: 4}
    FAILED_MESSAGES_COLUMNS_MAP = {EVENT_DATE_HEADING: 0, MESSAGE_ID_HEADING: 1, ADAPTER_ID_HEADING: 2, SERVICE_HEADING: 3, SOURCE_HEADING: 4, DESTINATION_HEADING: 5, MESSAGE_TYPE_HEADING: 6, REGION_HEADING: 7, DELETE_HEADING: 8}
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

    def get_failed_messages_data(self, region_code):
        logger.debug("Attempting to retrieve failed message for region: {}".format(region_code))
        url = self._get_url_by_name(ICE_FAILED_MESSAGES).format(region_code)
        soup = self.parse_data_page(url)
        main_panel = soup.find("div", class_="panel-body")
        table_dict_list = []
        if main_panel:
            thead = main_panel.find("thead")
            if thead:
                first_header_row = thead.find("tr")
                headings = first_header_row.find_all("td")
                heading_data = [item.get_text() for item in headings]
            tbody = main_panel.find("tbody")
            table_dict_list = self._obtain_table_data(tbody, self.FAILED_MESSAGES_COLUMNS_MAP)
        logger.debug("Found {} failed messages for region: {}".format(len(table_dict_list), region_code))
        return table_dict_list

    def _obtain_table_data(self, soup_table_body, columns_map):
        table_dict_list = []
        if soup_table_body:
            table_rows = soup_table_body.find_all("tr")
            if table_rows:
                for row_count, table_row in enumerate(table_rows):
                    row_dict = {}
                    for col_index, column_item_child in enumerate(table_row.find_all("td")):
                        if isinstance(column_item_child, Tag):
                            column_value = column_item_child.get_text().strip()
                            field_name = self._map_column_index_to_name(columns_map, col_index)
                            if field_name:
                                row_dict[field_name] = column_value
                            else:
                                logger.warning("Failed to find field name for col index: {}".format(col_index))
                    table_dict_list.append(row_dict)
        return table_dict_list

    def get_calm_dashboard_data(self):
        logger.debug("Attempting to retrieve calm dashboard data")
        dashboard_url = self._get_url_by_name(ICE_CALM_DASHBOARD)
        try:
            return self.cache.get_cache_result(dashboard_url)
        except CacheMissException as ce:
            logger.debug(str(ce))
        soup = self.parse_data_page(dashboard_url)
        main_panel = soup.find("div", class_="panel-body")
        thead = main_panel.find("thead")
        if thead:
            first_header_row = thead.find("tr")
            headings = first_header_row.find_all("th")
            heading_data = [item.get_text() for item in headings]
        tbody = main_panel.find("tbody")
        table_dict_list = self._obtain_table_data(tbody, self.CALM_DASHBOARD_COLUMNS_MAP)
        self.cache.store_cache_result(dashboard_url, table_dict_list, SEC_30)
        return table_dict_list

    def list_messages(self, search_criteria):
        logger.info("Checking failed messages count from ICE")
        dashboard_stats = self.get_calm_dashboard_data()
        region_code = search_criteria.get(REGION)
        region_failed_msg_count = self.get_failure_count_for_region(dashboard_stats, region_code)
        if region_code and region_failed_msg_count:
            logger.info("Getting failed messages from ICE")
            failed_details = self.get_failed_messages_data(region_code)
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

    # session = requests.session()
    # session.headers.update(headers)

    ice_proxy = ICEProxy()
    # soup = adm_proxy.parse_data_page(LOGIN_FORM_URL)
    # svars = {}
    # if soup:
    #     for var in soup.findAll('input', type="hidden"):
    #         svars[var['name']] = var['value']

    try:
        ice_proxy.login_to_site()
    except FailedToCommunicateWithSystem as err:
        logger.error(str(err))


    formatter = Formatter()
    region = "EU"
    results = ice_proxy.get_calm_dashboard_data()
    print(json.dumps(results))
    format_options = {'output': 'table', 'quiet': False, 'verbose': False}
    formatter.format(DataType.ice_dashboard, results, format_options)

    if ice_proxy.get_failure_count_for_region(results, region) > 0:
        failed_details = ice_proxy.get_failed_messages_data(region)
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
