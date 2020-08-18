import re

# Please keep this here as it is dynamically invoked
from main.algorithms import payload_predicates
from main.algorithms.payload_predicates import *
from main.config.constants import TRACKING_POINT, SEARCH_PARAMETERS, TYPE, DESTINATION, SOURCE, MESSAGE_STATUS, \
    ALGORITHM_STATS, MESSAGE_ID, algorithm_data_type_map, TRANSFORM, VALIDATE, ID


def translate_step_type_to_payload_type(step_type):
    if step_type in ["XALAN", "XMLJSON"]:
        return TRANSFORM
    elif step_type == "XSD":
        return VALIDATE
    return TRANSFORM


def is_valid_step_type(payload_transform_step_type, transform_step):
    if payload_transform_step_type == TRANSFORM and transform_step.get("transform-step-type") in ["XALAN", "XMLJSON"]:
        return True
    elif payload_transform_step_type == VALIDATE and transform_step.get("transform-step-type") == "XSD":
        return True
    return False


def get_matching_transform_step(transforms, stage_type, transform_name, transform_step_name):
    for current_transform in transforms:
        if current_transform.get("transform-name") == transform_name:
            for current_step in current_transform.get("transform-steps"):
                if current_step.get("transform-step-name") == transform_step_name and is_valid_step_type(stage_type, current_step):
                    return current_step
    return None


def get_transform_step_from_payload(payload, transforms):
    transform_stage = payload.get("tracking-point")
    match = re.match(r'^(\w+)\s*-\s*(.*)\((.*)\)$', transform_stage)
    if match:
        stage_type = match.group(1)
        transform_name = match.group(2)
        transform_step_name = match.group(3)
        return get_matching_transform_step(transforms, stage_type, transform_name, transform_step_name)
    return None


def obtain_transform_details_from_payload_tracking_point(payload):
    transform_stage = payload.get("tracking-point")
    match = re.match(r'^(\w+)\s*-\s*(.*)\((.*)\)$', transform_stage)
    if match:
        stage_type = match.group(1)
        transform_name = match.group(2)
        transform_step_name = match.group(3)
        return stage_type, transform_name, transform_step_name
    return None

def get_payload_index(stage_name, payloads_list):
    for index, current_payload in enumerate(payloads_list):
        if current_payload.get(TRACKING_POINT) == stage_name:
            return index
    return -1


def get_payload_object(stage_name, payloads_list):
    for index, current_payload in enumerate(payloads_list):
        if current_payload.get(TRACKING_POINT) == stage_name:
            return current_payload
    return None


def get_transform_search_parameters(cfg_rule):
    search_parameters = {}
    if cfg_rule and SEARCH_PARAMETERS in cfg_rule:
        for key in [SOURCE, DESTINATION, TYPE]:
            search_parameters[key] = cfg_rule.get(SEARCH_PARAMETERS).get(key)
    else:
        raise MissingConfigException("Failed to obtain search parameters to query Cirrus for transforms")
    return search_parameters


def explode_search_criteria(search_criteria_dict):
    return search_criteria_dict.get(SOURCE, "*"), search_criteria_dict.get(DESTINATION, "*"), search_criteria_dict.get(TYPE, "*")


def filter_transforms(search_criteria_dict, transform_data):
    source, destination, message_type = explode_search_criteria(search_criteria_dict)
    filtered_list = []
    processed_transform_ids = set()
    if transform_data:
        original_length = len(transform_data)
        for current_transform in transform_data:
            # TODO need to make sure this works correctly with Cirrus data, may need to use substring matching instead
            if current_transform[TYPE] != message_type:
                continue
            if current_transform[SOURCE] not in [source, "*"]:
                continue
            if current_transform[DESTINATION] not in [destination, "*"]:
                continue
            if current_transform[ID] in processed_transform_ids:
                continue
            filtered_list.append(current_transform)
            processed_transform_ids.add(current_transform[ID])
        filtered_length = len(filtered_list)
        logger.info(f"Filtered transforms list from {original_length} to {filtered_length} for source: {source}, destination: {destination} and message type: {message_type}")
    return filtered_list


def extract_search_parameters_from_message_detail(message_details):
    if message_details and len(message_details) >= 1:
        return {key: message_details[0].get(key, None) for key in [SOURCE, DESTINATION, TYPE]}
    return None


# def get_algorithm_results_per_message(statistics_map, algorithm_name):
#     return [statistics_map[message_id][algorithm_name] for message_id in statistics_map.keys() if algorithm_name in statistics_map[message_id]]


def get_algorithm_results_per_message(statistics_map, algorithm_name, func_to_call):
    return [func_to_call(message_id, statistics_map[message_id][algorithm_name]) for message_id in statistics_map.keys() if algorithm_name in statistics_map[message_id]]


def prefix_message_id_to_lines(message_id, lines):
    if isinstance(lines, list):
        return [[message_id, *x] for x in lines]
    return lines


def merge_message_status_with_algo_results(message_status_map, algorithm_results_map):
    message_status_map.update(algorithm_results_map)
    return message_status_map


def enrich_message_analysis_status_results(statistics_map):
    return [merge_message_status_with_algo_results(statistics_map[message_id][MESSAGE_STATUS], statistics_map[message_id][ALGORITHM_STATS]) for message_id in statistics_map.keys()]


def process_message_payloads(payloads_list, predicate_function):
    method_to_call = getattr(payload_predicates, predicate_function)
    if payloads_list:
        for payload in payloads_list:
            if method_to_call(payload):
                return True
    return False


def get_data_type_for_algorithm(algorithm_name):
    return algorithm_data_type_map[algorithm_name]


# Note this is only for custom data algos
def get_algorithm_name_from_data_type(data_type):
    for k, v in algorithm_data_type_map.items():
        if v == data_type:
            return k
    return None


class InvalidStateException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Illegal state exception: {}".format(self.message)


class MissingConfigException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Missing data exception: {}".format(self.message)


class InvalidConfigException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return "Invalid config exception: {}".format(self.message)


class CacheMissException(Exception):
    def __init__(self, cache_key):
        self.cache_key = cache_key

    def __str__(self):
        return "Failed to find key: {} in cache".format(self.cache_key)


class MissingPayloadException(Exception):
    def __str__(self):
        return "Failed to parse payload for message as it was None"


class SuspectedMissingTransformsException(Exception):
    def __str__(self):
        return "Suspected missing transforms, please retrieve with wider parameters"