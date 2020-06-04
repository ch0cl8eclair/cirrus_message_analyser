from enum import Enum
import operator
from functools import reduce

from main.algorithms.payload_operations import get_missing_movement_line_fields_for_payload
from main.algorithms.xpath_lookup import get_xpath_text
from main.algorithms.xsl_parser import XSLParser
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE
import logging
from logging.config import fileConfig

from main.config.constants import NAME, TRACKING_POINT, URL, PAYLOAD
from main.model.model_utils import *

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('parser')

PAYLOAD_INDEX = "payload-index"
STEP = "step"


class TransformStagesAnalyser:
    TRANSFORM_IGNORE_STEPS = ["Extension Replacement", "F4F XML Validation"]

    def __init__(self, payloads, transforms, cirrus_proxy):
        self.transform_stages = []
        self.payloads = payloads
        self.results_map = {}
        self.xsl_parser = XSLParser(cirrus_proxy)
        self._is_verbose = True
        self._is_quiet = False
        self.__generate_transform_summary_lists(payloads, transforms)

    def __generate_transform_summary_lists(self, payloads_list, transforms_list):
        """Generates the transform stage names as per payloads from the transforms list"""
        if not transforms_list:
            logger.error("No transforms found for message to generate transform steps")
            return None

        self.transform_stages = []
        current_channel = ""
        for current_transform in transforms_list:
            current_stage = {}
            channel_name = (current_transform.get("transform-channel"))
            if channel_name != current_channel:
                self.__create_channel_stage(channel_name)
                current_channel = channel_name
            prefix = current_transform.get("transform-name")
            for current_step in current_transform.get("transform-steps"):
                step_name = current_step.get("transform-step-name")
                if step_name in self.TRANSFORM_IGNORE_STEPS:
                    continue
                self.__create_transform_stage(prefix, current_step)
        self.__add_remaining_payloads(payloads_list)
        if self._is_verbose:
            self.__output_stage_struct()

    def __add_remaining_payloads(self, payloads_list):
        last_payload_index = max([transform_stage[PAYLOAD_INDEX] for transform_stage in self.transform_stages if transform_stage[PAYLOAD_INDEX] != -1])
        # last_payload_index = self.transform_stages[-1][PAYLOAD_INDEX]
        last_payload_index = last_payload_index + 1
        payloads_found = False
        for current_payload in payloads_list[last_payload_index:]:
            if current_payload[TRACKING_POINT].startswith("PAYLOAD ["):
                payloads_found = True
                self.__create_step(current_payload[TRACKING_POINT])
            # Break out once we have processed the group of payloads
            elif payloads_found:
                break

    def __create_channel_stage(self, channel_name):
        self.__create_step(channel_name)

    def __create_transform_stage(self, prefix, step):
        step_name = step.get("transform-step-name")
        step_type = step.get("transform-step-type")
        translated_type = translate_step_type_to_payload_type(step_type)
        stage_name = "{} - {}({})".format(translated_type, prefix, step_name)
        self.__create_step(stage_name, step)

    def __create_step(self, step_name, step=None):
        self.transform_stages.append({NAME: step_name,
                                   PAYLOAD_INDEX: get_payload_index(step_name, self.payloads),
                                   STEP: step})

    def __output_stage_struct(self):
        for stage in self.transform_stages:
            logger.info("{}, payload: {}, step: {}".format(stage[NAME], stage[PAYLOAD_INDEX], self.__step_to_str(stage[STEP])))

    def __step_to_str(self, step):
        if step:
            return "{}-{}".format(step["transform-step-type"], step[URL])
        else:
            return ""

    def __get_payload(self, stage):
        index = stage[PAYLOAD_INDEX]
        if index != -1:
            return self.payloads[index]
        return None

    def analyse(self):
        """Iterate through transforms with corresponding payloads and trace backwards the missing fields to the original document,
        all results go in a table with rows for each field and the columns being the transform stages"""
        # Go through in reverse order
        for index, transform_stage in enumerate(reversed(self.transform_stages)):
            logger.info("Processing stage: {} name: [{}]".format(index, transform_stage.get(NAME)))
            # Get initial empty fields
            if transform_stage[NAME] == "PAYLOAD [movement JSON POST request]":
                # Get empty fields
                missing_json_fields_map = get_missing_movement_line_fields_for_payload(self.__get_payload(transform_stage))
                self.__print_missing_movement_line_fields(missing_json_fields_map)
                if missing_json_fields_map:
                    fields_set = self.__get_missing_fields_set(missing_json_fields_map)
                    # Sort the results for easier reading and to align results set
                    self.__add_stage_results(fields_set, TransformStage.json_missing_fields)
                    continue
                else:
                    # Unable to continue
                    logger.error("No missing fields found for transform stage: [{}]".format(transform_stage[NAME]))
                    # TODO throw an exception
                    return False

            elif transform_stage[NAME] == "TRANSFORM - Movement - COP(Convert V5 To Movement JSON)" and self.__is_xslt_transform(transform_stage):
                missing_fields = self.__get_stage_results(TransformStage.json_missing_fields)
                if not missing_fields:
                    # Unable to continue
                    logger.error("No missing fields found to process at stage: [{}]".format(transform_stage[NAME]))
                    return False
                xsl_url = self.__get_xsl_transform_url(transform_stage)
                field_xpaths_map = self.xsl_parser.parse(xsl_url, missing_fields)
                if field_xpaths_map:
                    self.__add_mapped_stage_results(field_xpaths_map, TransformStage.v5_to_movement_xpaths)
                    continue
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            elif transform_stage[NAME] == "TRANSFORM - Movement - COP(IDOC to F4Fv5 XML)" and self.__is_xslt_transform(transform_stage):
                missing_field_xpaths = self.__get_stage_results(TransformStage.v5_to_movement_xpaths)
                if not missing_field_xpaths:
                    # Unable to continue
                    logger.error("No missing field xpaths found to process at stage: [{}]".format(transform_stage[NAME]))
                    return False
                results_list = []
                xsl_url = self.__get_xsl_transform_url(transform_stage)
                for xpath in missing_field_xpaths:
                    result = self.xsl_parser.parse_xsl(xsl_url, xpath)
                    if not result:
                        logger.error("Failed to find xpath mapping for {} within stage: [{}]".format(xpath, transform_stage[NAME]))
                    else:
                        results_list.append(result)
                if results_list:
                    self.__add_stage_results(results_list, TransformStage.idoc_to_f4fv5_xpaths)
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            elif transform_stage[NAME] == "IN":
                missing_field_xpaths = self.__get_stage_results(TransformStage.idoc_to_f4fv5_xpaths)
                if not missing_field_xpaths:
                    # Unable to continue
                    logger.error("No missing field xpaths found to process at stage: [{}]".format(transform_stage[NAME]))
                    return False
                results_list = []
                for xpath in missing_field_xpaths:
                    payload_str = self.__get_payload(transform_stage).get(PAYLOAD)
                    result = get_xpath_text(payload_str, xpath)
                    if not result:
                        logger.error("Failed to find xpath mapping for {} within stage: [{}]".format(xpath, transform_stage[NAME]))
                    else:
                        results_list.append(result)
                if results_list:
                    self.__add_stage_results(results_list, TransformStage.idoc)
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            else:
                logger.debug("Ignoring transform stage: [{}]".format(transform_stage[NAME]))
        return True

    def __print_missing_movement_line_fields(self, fields_map):
        if fields_map:
            for line, fields in fields_map.items():
                logger.info("Movement line[{}] missing fields: [{}]".format(line, fields))
        else:
            logger.error("No missing fields found for movement message")

    def __get_missing_fields_set(self, fields_map):
        fields_set = set()
        fields_set.update(reduce(operator.concat, fields_map.values()))
        # Convert to sorted list
        as_list = list(fields_set)
        as_list.sort()
        logger.info("Distinct missing movement fields set: [{}]".format(as_list))
        return as_list

    def __add_stage_results(self, data, stage):
        logger.debug("Adding data for stage: {}, values: {}".format(stage, data))
        self.results_map[stage] = data

    def __add_mapped_stage_results(self, data_map, stage):
        fields = list(data_map.keys())
        fields.sort()
        self.results_map[stage] = [data_map[key] for key in fields]

    def __get_stage_results(self, stage):
        if stage in self.results_map:
            return self.results_map[stage]
        return None

    def __is_xslt_transform(self, transform_stage):
        return transform_stage and STEP in transform_stage and transform_stage[STEP].get("transform-step-type") == "XALAN"

    def __get_xsl_transform_url(self, transform_stage):
        if transform_stage and STEP in transform_stage and URL in transform_stage[STEP]:
            return transform_stage[STEP].get(URL)
        return None

    def __restructure_column_data_to_rows(self, data):
        records = []
        sample_row_data = data.get(TransformStage.json_missing_fields)
        row_count = len(sample_row_data) if sample_row_data else 0
        for counter in range(row_count):
            record = []
            for stage in TransformStage:
                stage_list = data.get(stage)
                record.append(stage_list[counter] if stage_list and counter < len(stage_list) else "")
            records.append(record)
        return records

    def get_results_records(self):
        return self.__restructure_column_data_to_rows(self.results_map)


class TransformStage(Enum):
    json_missing_fields = 0
    v5_to_movement_xpaths = 1
    idoc_to_f4fv5_xpaths = 2
    idoc = 3
