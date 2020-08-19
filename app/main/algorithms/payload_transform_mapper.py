import logging
import re
from logging.config import fileConfig

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import VALIDATE, TRANSFORM
from main.model.model_utils import translate_step_type_to_payload_type, \
    SuspectedMissingTransformsException, \
    obtain_transform_details_from_payload_tracking_point, get_matching_transform_and_step

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


class PayloadTransformMapper:
    HEADINGS = ["tracking-point", "type", "transform-step-name", "url", "transform-step-type"]

    def __init__(self, payloads, transforms, cirrus_proxy):
        self.payloads = payloads
        self.transforms = transforms
        self.mapping_records = []
        self.cirrus_proxy = cirrus_proxy

    def reset(self, transforms):
        self.transforms = transforms
        self.mapping_records = []

    def map(self):
        if not self.payloads:
            return
        missing_transforms = 0
        for current_payload in self.payloads:
            transform_details_tuple = obtain_transform_details_from_payload_tracking_point(current_payload)
            if transform_details_tuple:
                stage_type, transform_name, transform_step_name = transform_details_tuple
                transform_obj, transform_step = get_matching_transform_and_step(self.transforms, stage_type, transform_name, transform_step_name)
                if not transform_step and stage_type in [TRANSFORM, VALIDATE]:
                    missing_transforms = missing_transforms + 1
            else:
                transform_obj, transform_step = (None, None)
            self.mapping_records.append(self._create_record(current_payload, transform_obj, transform_step))
        if missing_transforms:
            raise SuspectedMissingTransformsException()

    def get_records(self):
        return self.mapping_records

    def _create_record(self, current_payload, transform_obj, transform_step):
        new_record = {'tracking-point': current_payload.get("tracking-point")}
        if transform_step:
            new_record['type'] = translate_step_type_to_payload_type(transform_step.get("transform-step-type"))
            new_record['transform-step-name'] = transform_step.get("transform-step-name")
            new_record['url'] = self._get_variable_resolved_url(transform_obj, transform_step)
            new_record['transform-step-type'] = transform_step.get("transform-step-type")
        return new_record

    def _get_variable_resolved_url(self, transform_obj, transform_step):
        """Cirrus transforms can have variable in their xsl/xsd files, so attempt to resolve them here"""
        current_url = transform_step.get("url")
        if not current_url:
            return current_url
        variable_names = re.findall(r'\$\{(\w+)\}', current_url)
        variable_mappings = {}
        if not variable_names:
            return current_url

        # Create a map of variable name to variable value from the defined transform settings
        for current_variable in variable_names:
            # for now just look in transform pre metadata and not post transform metadata
            variable_value = self._find_transform_metadata(transform_obj, "transform-pre-metadata", current_variable)
            variable_mappings[current_variable] = variable_value

        # Attempt to resolve each variable with the url
        # Note some variable may have a variable itself as a value, not guaranteed to have a literal here
        new_url_str = current_url
        has_env_variable = False
        for k, v in variable_mappings.items():
            if v is None:
                if k == "ENV":
                    has_env_variable = True
                pass
            elif v == "${ENV}":
                # Replace other variables and then try after
                has_env_variable = True
                pass
            elif v.startswith("${"):
                # There's not much we can do here
                pass
            else:
                new_url_str = new_url_str.replace("${" + k + "}", v)
        # Now apply a targeted guess and issue a http head request to confirm
        if has_env_variable:
            # for this we can guess the value given that we are only dealing with PRD
            for replacement_variable in ["live", "PRD", "prd"]:
                if self.cirrus_proxy.check_if_valid_url(new_url_str.replace("${ENV}", replacement_variable)):
                    new_url_str = new_url_str.replace("${ENV}", replacement_variable)
                    break
        logger.info("Resolved the following transform url: {} to {}".format(current_url, new_url_str))
        return new_url_str

    def _find_transform_metadata(self, transform_obj, transform_sub_list_name, variable_name):
        for item in transform_obj.get(transform_sub_list_name, []):
            if "metadata-name" in item and item.get("metadata-name") == variable_name and "metadata-value" in item:
                return item.get("metadata-value")
        return None
