import re

from main.config.constants import TRACKING_POINT, SEARCH_PARAMETERS, TYPE, DESTINATION, SOURCE


def translate_step_type_to_payload_type(step_type):
    if step_type in ["XALAN", "XMLJSON"]:
        return "TRANSFORM"
    elif step_type == "XSD":
        return "VALIDATE"
    return "TRANSFORM"


def is_valid_step_type(payload_transform_step_type, transform_step):
    if payload_transform_step_type == "TRANSFORM" and transform_step.get("transform-step-type") in ["XALAN", "XMLJSON"]:
        return True
    elif payload_transform_step_type == "VALIDATE" and transform_step.get("transform-step-type") == "XSD":
        return True
    return False


def get_matching_transform_step(transforms, stage_type, transform_name, transform_step_name):
    for current_transform in transforms:
        current_transform.get("transform-name") == transform_name
        for current_step in current_transform.get("transform-steps"):
            if current_step.get("transform-step-name") == transform_step_name and is_valid_step_type(stage_type, current_step):
                return current_step
    return None


def get_transform_step_from_payload(self, payload, tranforms):
    transform_stage = payload.get("tracking-point")
    match = re.match(r'^(\w+)\s*-\s*(.*)\((.*)\)$', transform_stage)
    if match:
        stage_type = match.group(1)
        transform_name = match.group(2)
        transform_step_name = match.group(3)
        return self.__get_matching_transform_step(tranforms, stage_type, transform_name, transform_step_name)
    return None


def get_payload_index(stage_name, payloads_list):
    for index, current_payload in enumerate(payloads_list):
        if current_payload.get(TRACKING_POINT) == stage_name:
            return index
    return -1


def get_transform_search_parameters(cfg_rule):
    search_parameters = {}
    if cfg_rule and SEARCH_PARAMETERS in cfg_rule:
        for key in [SOURCE, DESTINATION, TYPE]:
            search_parameters[key] = cfg_rule.get(SEARCH_PARAMETERS).get(key)
    else:
        raise MissingConfigException("Failed to obtain search parameters to query Cirrus for transforms")
    return search_parameters


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
