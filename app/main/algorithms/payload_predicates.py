import logging
from logging.config import fileConfig

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import TRACKING_POINT, PAYLOAD, URL

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('parser')


def payload_has_json_post_error(payload):
    if payload:
        return payload.get(TRACKING_POINT) == "PAYLOAD [Error: HTTP Response: 400]" and\
        payload.get(PAYLOAD) == "{\"message\":\"preg_replace(): Parameter mismatch, pattern is a string while replacement is an array\",\"code\":0}"
    return False


def payload_is_json_post_request(payload):
    return payload and payload.get(TRACKING_POINT) == "PAYLOAD [movement JSON POST request]"


def is_xslt_transform(payload):
    return payload and URL in payload and payload.get("transform-step-type") == "XALAN"


def payloads_match_single_yara_movement_case(payloads_list, transform_stages):
    unmatched_pos = -1
    for payload_ptr, payload in enumerate(payloads_list):
        if payload_ptr < len(transform_stages):
            if payload.get("tracking-point") == transform_stages[payload_ptr]:
                continue
            else:
                unmatched_pos = payload_ptr
                break
        else:
            unmatched_pos = payload_ptr
            break
    # Check if we did not match all payloads against all transform stages
    if unmatched_pos > -1:
        if len(payloads_list) - len(transform_stages) <= 2:
            # Using unmatchedpos +1 instead of -1 so if the msg has been replayed we can still identify it as original problem
            if (payload_has_json_post_error(payloads_list[unmatched_pos +1])) and payload_is_json_post_request(payloads_list[unmatched_pos]):
                return True
    return False


# def is_yara_movement_post_problem(cirrus_proxy, payloads_list, transform_stages):
#     function_name = "main yara predicate"
#     """Top level function to determine if this is the main yara movement post issue"""
#     if not payloads_match_single_yara_movement_case(payloads_list, transform_stages):
#         logger.debug("{} does not matching transform stages".format(function_name))
#         return False
#
#     last_transform_stage = len(transform_stages) - 1
#     if payload_has_json_post_error(payloads_list[last_transform_stage]):
#         logger.debug("{} does not have {}".format(function_name, "Json post error"))
#         return False
#
#     # Get missing fields from final json payload
#     missing_json_fields_map = get_missing_movement_line_fields_for_payload(payloads_list[last_transform_stage - 1])
#
#     # How many movement lines are there, just one hopefully?
#     if missing_json_fields_map:
#         fields_set = {}
#         fields_set.update(missing_json_fields_map.values())
#         logger.info("Found the following missing fields from the movement lines: [{}]".format(fields_set))
#     else:
#         logger.warn("Failed to get any missing fields from the movement lines, unable to continue analysis")
#         return False
#
#     # TODO now need to work with transforms and payloads together
#     # Now lookup missing fields from last xslt
#     start_ptr = last_transform_stage - 2
#     found = False
#     fields_to_find = list(fields_set)
#     field_xpaths_map = {}
#     while not found and start_ptr >= 0:
#         # With  fields we look at xslt payloads for xpaths
#         if is_xslt_transform(payloads_list[start_ptr]):
#             found = True
#             parser = XSLParser(cirrus_proxy)
#             # field_xpaths_map.clear()
#             field_xpaths_map = parser.parser(payloads_list[start_ptr].get(URL), fields_to_find)
#             if field_xpaths_map:
#                 logger.info("Found xpaths for fields within payload stage: {} : {}".format(payloads_list[start_ptr].get("transform-step-name"), str(field_xpaths_map)))
#                 fields_to_find.clear()
#                 for current_xpath in field_xpaths_map.values():
#                     matched_tag = lookup_xpath(payloads_list[start_ptr - 1].get(PAYLOAD), current_xpath)
#                     if not matched_tag:
#                         # need to determine tag from xpath
#                         matched_tag = get_final_tag_from_xpath(current_xpath)
#                     fields_to_find.append(matched_tag)
#             else:
#                 # we can proceed no further
#                 logger.warn("Failed to obtain xpaths for fields")
#                 break
#         else:
#             start_ptr = start_ptr - 1
#
#
#
#     # # now find the next xslt
#     # start_ptr = start_ptr -1
#     #
#     #
#     # # Define reverse lookup
#     # LOOKUP_PAYLOAD_DATA = [
#     #     {
#     #         "payload-name": "PAYLOAD [movement JSON POST request]",
#     #         "type": "json",
#     #         "operation": "get-fields"
#     #     },
#     #     {
#     #         "payload-name": "TRANSFORM - Movement - COP(Convert V5 To Movement JSON)",
#     #         "type": "xsl",
#     #         "operation": "get-xpaths"
#     #     },
#     #     {
#     #         "payload-name": "TRANSFORM - Movement - COP(IDOC to F4Fv5 XML)",
#     #         "type": "xsl",
#     #         "operation": "get-xpaths"
#     #     },
#     #     {
#     #         "payload-name": "TRANSFORM - Movement - COP(Extension Replacement)",
#     #         "type": "xsl",
#     #         "operation": "get-xpaths"
#     #     },
#     # ]