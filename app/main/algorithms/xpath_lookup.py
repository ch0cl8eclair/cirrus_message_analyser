import os
import re
from lxml import etree
from main.utils.utils import clear_quotes

from main.config.configuration import LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


def __parse_text_and_perform_xpath_lookup(payload_str, xpath, is_absolute=False):
    xml = bytes(bytearray(payload_str, encoding='utf-8'))
    tree = etree.XML(xml)
    # If it is not an absolute xpath then add relative prefix
    if not is_absolute:
        xpath = "//" + xpath
    result = tree.xpath(xpath)
    return result


def lookup_xpath(payload_str, xpath, is_absolute=False):
    result = __parse_text_and_perform_xpath_lookup(payload_str, xpath, is_absolute)
    if result:
        return result[0].tag
    return None


def lookup_xpath_get_node(payload_str, xpath, is_absolute=False):
    result = __parse_text_and_perform_xpath_lookup(payload_str, xpath, is_absolute)
    if result:
        return etree.tostring(result[0], pretty_print=False)
    return None


def get_xpath_text(payload_str, xpath, is_absolute=False):
    result = __parse_text_and_perform_xpath_lookup(payload_str, xpath, is_absolute)
    # Distinguish between none and empty string based on if xpath is resolved or not
    if result:
        return result[0].text if result[0].text else ""
    return None


def get_final_tag_from_xpath(xpath_expression):
    if xpath_expression:
        components = xpath_expression.split("/")
    done = False
    while not done and components:
        current_element = components.pop(-1)
        if current_element.startswith("@"):
            continue
        # Check if there are brackets
        match = re.match(r'(\w+)\[', current_element)
        if match:
            return match.group(1)
        else:
            return current_element
    return None


def get_attribute_for_tag(search_tag, xpath_expression):
    if xpath_expression:
        components = xpath_expression.split("/")
    done = False
    while not done and components:
        current_element = components.pop(-1)
        if current_element.startswith("@"):
            continue
        # Check if there are brackets
        match = re.match(r'(\w+)\[', current_element)
        if match and match.group(1).startswith(search_tag):
            # ok we have a match with attr
            attr_match = re.match(r'(\w+)\[@(\w+)\s*=\s*(.*)\]', current_element)
            if attr_match:
                return {attr_match.group(2): clear_quotes(attr_match.group(3))}
            else:
                logger.error("Found matching tag with multiple attr, unable to process")
                return None
        elif current_element == search_tag:
            return None


def get_final_attribute_of_xpath(xpath_expression):
    if xpath_expression:
        components = xpath_expression.split("/")
        last_element = components.pop(-1)
        if last_element.startswith("@"):
            return last_element[1:]
    return get_final_tag_from_xpath(xpath_expression)


def main():
    PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), '../../test/resources/yara_payload_5.xml')
    with open(PAYLOAD_FILE) as f:
        payload_str = f.read()
        # lookup = lookup_xpath(payload_str, "LineComponent/Product/Quantity[@Type='Ordered']")
        # lookup = lookup_xpath(payload_str, "LineComponent/Product/Quantity")
        # print(lookup)
        print(get_attribute_for_tag("Quantity", "LineComponent/Product/Quantity[@Type='Ordered']"))


if __name__ == '__main__':
    main()
