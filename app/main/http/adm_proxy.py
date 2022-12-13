import urllib3

from main.config.constants import *
from main.http.webpage_proxy import WebPageParser, ADM_PROJECTS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import logging
from logging.config import fileConfig

headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux i686; rv:7.0.1) Gecko/20100101 Firefox/7.0.1'}

LOGGING_CONFIG_FILE = os.path.join(os.path.dirname(__file__), '../../resources/logging_config.ini')
fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')


class ADMProxy(WebPageParser):
    """All fetch functionality for ADM access"""
    ADM_FILTER_COLUMN_FOR_PROJECT_DICT = {ADM_LOCATIONS: 0, ADM_CONFIGS: 0, ADM_VERSIONS: 0, ADM_SCRIPTS: 1, ADM_ARTIFACTS: 1}

    def __init__(self):
        WebPageParser.__init__(self, ADM_CFG)
        self.credentials_section_name = ADM_CREDENTIALS
        self.login_url = ADM_LOGIN
        self.submit_url = ADM_SUBMIT

    # def fetch_locations(self, options):
    #     url = self.get_app_endpoint_url2(ADM_LOCATIONS, options)
    #     soup = self.parse_data_page(url)

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

    def get_data_for_project(self, url_key, project_name, merged_app_cfg):
        url = self.get_app_endpoint_url2(url_key, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        filter_column = self.ADM_FILTER_COLUMN_FOR_PROJECT_DICT[url_key]
        data = self.fetch_project_fields(soup, filter_column, project_name, False, url_key == ADM_CONFIGS)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_configs(self, merged_app_cfg):
        url = self.get_app_endpoint_url2(ADM_CONFIGS, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        data = self.fetch_project_fields(soup, -1, None, True, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_locations(self, merged_app_cfg):
        url = self.get_app_endpoint_url2(ADM_LOCATIONS, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_versions(self, merged_app_cfg):
        url = self.get_app_endpoint_url2(ADM_VERSIONS, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_scripts(self, merged_app_cfg):
        url = self.get_app_endpoint_url2(ADM_SCRIPTS, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_artifacts(self, merged_app_cfg):
        url = self.get_app_endpoint_url2(ADM_ARTIFACTS, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        data = self.fetch_project_fields(soup, -1, None, True)
        data.insert(0, self.fetch_header_data(soup))
        return data

    def get_locations_for_project(self, project_name, merged_app_cfg):
        return self.get_data_for_project(ADM_LOCATIONS, project_name, merged_app_cfg)

    def get_configs_for_project(self, project_name, merged_app_cfg):
        return self.get_data_for_project(ADM_CONFIGS, project_name, merged_app_cfg)

    def get_versions_for_project(self, project_name, merged_app_cfg):
        return self.get_data_for_project(ADM_VERSIONS, project_name, merged_app_cfg)

    def get_scripts_for_project(self, project_name, merged_app_cfg):
        return self.get_data_for_project(ADM_SCRIPTS, project_name, merged_app_cfg)

    def get_artifacts_for_project(self, project_name, merged_app_cfg):
        return self.get_data_for_project(ADM_ARTIFACTS, project_name, merged_app_cfg)

    def get_locations_for_group(self, group_name, merged_app_cfg):
        return self.get_data_for_group(ADM_LOCATIONS, group_name, merged_app_cfg)

    def get_configs_for_group(self, group_name, merged_app_cfg):
        return self.get_data_for_group(ADM_CONFIGS, group_name, merged_app_cfg)

    def get_versions_for_group(self, group_name, merged_app_cfg):
        return self.get_data_for_group(ADM_VERSIONS, group_name, merged_app_cfg)

    def get_scripts_for_group(self, group_name, merged_app_cfg):
        return self.get_data_for_group(ADM_SCRIPTS, group_name, merged_app_cfg)

    def get_artifacts_for_group(self, group_name, merged_app_cfg):
        return self.get_data_for_group(ADM_ARTIFACTS, group_name, merged_app_cfg)

    def get_data_for_group(self, url_key, group_name, merged_app_cfg):
        url = self.get_app_endpoint_url2(url_key, merged_app_cfg)
        soup = self.parse_data_page(url, merged_app_cfg)
        requested_group_projects = [group[PROJECTS] for group in self.configuration.get(ADM_PROJECTS) if group[NAME] == group_name][0]
        filter_column = self.ADM_FILTER_COLUMN_FOR_PROJECT_DICT[url_key]
        if requested_group_projects:
            header_line = self.fetch_header_data(soup)
            data_lines = self.fetch_project_fields_for_project_group(soup, filter_column, requested_group_projects, url_key == ADM_CONFIGS)
            return [header_line] + data_lines
        else:
            logger.error("The given group: {} could not be found in the config".format(group_name))
        return None
