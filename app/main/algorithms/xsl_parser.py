from bs4 import BeautifulSoup, Tag

from main.algorithms.xpath_lookup import get_final_tag_from_xpath, get_attribute_for_tag, get_final_attribute_of_xpath
from main.config.configuration import get_configuration_dict, ConfigSingleton
from main.http.cirrus_proxy import CirrusProxy

from main.config.configuration import LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')

SELECT = "select"


class XSLParser:

    def __init__(self, cirrus_proxy):
        self.proxy = cirrus_proxy

    # def __find_xpath(self, node):
    #     """Goes through the xsl tree and returns the select value ie xpath"""
    #     if node and node.children:
    #         filtered_children = [child for child in node.children if self.__is_not_attribute(child)]
    #         result = list(map(self.__attribute_text_to_str, filter(self.__xsl_text_nodes, filtered_children)))
    #         if result:
    #             return result[0]
    #     return None
    def __find_xpath(self, node):
        """Goes through the xsl tree and returns the select value ie xpath"""
        if node and node.children:
            for child in node.children:
                if not isinstance(child, Tag):
                    continue
                if child.name == "xsl:attribute":
                    continue
                if child.has_attr(SELECT):
                    return child[SELECT]
                if child.children:
                    match = self.__find_xpath(child)
                    if match:
                        return match
        return None

    def __is_attribute(self, x):
        return isinstance(x, Tag) and x.name == "xsl:attribute"

    def __is_not_attribute(self, x):
        return isinstance(x, Tag) and x.name != "xsl:attribute"

    def __is_attribute_with_name(self, x, name):
        return isinstance(x, Tag) and x.name == "xsl:attribute" and x.has_attr("name") and x["name"] == name

    def __xsl_text_nodes(self, x):
        return isinstance(x, Tag) and x.name in ["xsl:text", "xsl:value-of", "xsl:with-param"]

    def __attribute_text_to_str(self, x):
        if isinstance(x, Tag) and x.name == "xsl:text":
            return x.text
        elif isinstance(x, Tag) and x.name in ["xsl:value-of", "xsl:with-param"] and x.has_attr(SELECT):
            return x[SELECT]
        return None

    def __get_tag_value_str(self, node):
        if node and node.children:
            for child in node.descendants:
                if not self.__xsl_text_nodes(child):
                    continue
                text = self.__attribute_text_to_str(child)
                if text:
                    return text
                if child.children:
                    match = self.__get_tag_value_str(child)
                    if match:
                        return match
        return None

    def __get_xsl_attr_value(self, node, attribute_name):
        """Goes through the xsl tree and returns the value of an attribute for a tag"""
        if node and node.children:
            matching_attributes = [x for x in node.children if self.__is_attribute_with_name(x, attribute_name)]
            # matching_attributes = list(filter(self.__is_attribute_with_name, node.children, attribute_name))
            if matching_attributes:
                return self.__get_tag_value_str(matching_attributes[0])
        return None

    def parse(self, xsl_url, search_fields_list):
        """Find the given field xpaths within the given xsl file"""
        xsl_str = self.proxy.get(xsl_url)
        return self.parse_text(xsl_str, search_fields_list)

    def parse_text(self, xml_text, search_fields_list):
        result_map = {}
        soup = BeautifulSoup(xml_text, "lxml")
        for field in search_fields_list:
            result = soup.find(field.lower())
            # TODO what happens when we have an array
            match = self.__find_xpath(result)
            if match:
                logger.info("Field: {} is resolved to xpath: {}".format(field, match))
                result_map[field] = match
        return result_map

    def parse_xsl(self, xsl_url, xpath):
        """Find the given field xpaths within the given xsl file"""
        xsl_str = self.proxy.get(xsl_url)
        return self.find_xsl_element(xsl_str, xpath)

    def find_xsl_element(self, xsl_text, xpath):
        result_map = {}
        soup = BeautifulSoup(xsl_text, "lxml")
        search_tag = get_final_tag_from_xpath(xpath)
        logger.debug("Attempting for find tag: {} within xsl file".format(search_tag))
        if search_tag:
            result_list = soup.find_all(search_tag.lower())
            logger.debug("Found {} matches for tag: {}".format(len(result_list), search_tag))
            if len(result_list) == 1:
                # great a single match
                logger.debug("Found a single match")
                # process and obtain the xpath
                return self.__find_xpath(result_list[0])
            else:
                attr_dict = get_attribute_for_tag(search_tag, xpath)
                # need to do further filtering or just select the first
                for result in result_list:
                    break_result_processing = False
                    for attr in attr_dict.keys():
                        # attributes_of_children_list = list(filter(self.__is_attribute_with_name(attr), result.children))
                        attributes_of_children_list = [x for x in result.children if self.__is_attribute_with_name(x, attr)]
                        for child in attributes_of_children_list:
                            logger.debug("Processing potential match from xsl: {}, with attr: {}".format(child.name, child.attrs))
                            child_value = self.__get_tag_value_str(child)
                            logger.debug("Matched child having required attribute, attempting to match values: {} with {}".format(child_value, attr_dict[attr]))
                            if child_value == attr_dict[attr]:
                                logger.debug("Found matching result from xsl that has match child attr value: {}:{}".format(attr, attr_dict[attr]))
                                xpath_lookup_value = get_final_attribute_of_xpath(xpath)
                                if xpath_lookup_value == search_tag:
                                    return self.__find_xpath(result)
                                else:
                                    return self.__get_xsl_attr_value(result, xpath_lookup_value)
                            else:
                                # abort loop as we have found matching attribute
                                break_result_processing = True
                                break
        return None


def main():
    # Read in config
    config = ConfigSingleton(get_configuration_dict())
    cirrus_proxy = CirrusProxy()
    parser = XSLParser(cirrus_proxy)
    url = "http://mappings.f4f.com/prd/uk0000000037/ZESADV_F4Fv5Movement.xsl"
    # parser.parse(url, ["order_qty", "order_uom"])
    logger.info(parser.parse_xsl(url, "LineComponent/Product/Quantity[@Type='Ordered']"))


if __name__ == '__main__':
    main()
