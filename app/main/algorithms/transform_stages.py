import operator
from functools import reduce

from main.algorithms.empty_fields import DocumentEmptyFieldsParser, FlattenJsonOutputToCSV
from main.algorithms.payload_operations import get_missing_movement_line_fields_for_payload
from main.algorithms.xpath_lookup import get_xpath_text
from main.algorithms.xsl_parser import XSLParser

from main.config.constants import NAME, TRACKING_POINT, URL, PAYLOAD, PAYLOAD_INDEX, STEP, TransformStage
from main.model.model_utils import *

TRANSFORM_STEP_TYPE = "transform-step-type"
TRANSFORM_STEP_NAME = "transform-step-name"
TRANSFORM_STEPS = "transform-steps"
TRANSFORM_NAME = "transform-name"
TRANSFORM_CHANNEL = "transform-channel"

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('parser')

"""
This class is a special analyser that is closely coupled to cirrus datastructures
Cirrus stores all payloads against a msg id with a tracking-point field, this field can should the transform step executed eg:
    IN
    TRANSFORM - Movement - COP(Extension Replacement)
    TRANSFORM - Movement - COP(IDOC to F4Fv5 XML)
    VALIDATE - Movement - COP(F4F XML Validation)
    ROUTE
    OUT
    TRANSFORM - Movement - COP(Convert V5 To Movement JSON)
    TRANSFORM - Movement - COP(JSON Transform)
    SEND
    PAYLOAD [movement JSON POST request]
    PAYLOAD [Error: HTTP Response: 400]
 
Now we are just interested in the Transform payloads above as these show the payload post transform. The text also helps us to
identify the exact transform step as defined in Cirrus.
Transforms are stored by source, destination and msg type. The have a Channel, with each channel have a number of steps.
Each step too has a name and a reference to a xsl file. We are interested in this xsl file to obtain the the field mapping.

So what do we do:
1) Obtain payloads For a given msg
2) Obtain the transforms for the source, destination and msg type
3) Now focus on the Transform payloads
4) Obtain the transform steps for the transform payloads
5) From the transform step obtain the xsl
6.1) Work backward through the transform payloads, for the first payload obtain the empty fields
6.2) Now for the transform step obtain the xpaths from the xsl for the missing fields
6.3) Lookup xpath from previous xpath for the transform xsl
6.4) For the final payload (which is the initial IN payload), resolve the final xpath against the document to see the source field value.
7) Output the results
"""


class TransformStagesAnalyser:
    TRANSFORM_IGNORE_STEPS = ["Extension Replacement", "F4F XML Validation"]

    def __init__(self, payloads, transforms, cirrus_proxy, filter_options_dict=None):
        self.transform_stages = []
        self.payloads = payloads
        self.results_map = {}
        self.xsl_parser = XSLParser(cirrus_proxy)
        self._is_verbose = True
        self._is_quiet = False
        self.parse_filter_options(filter_options_dict)
        self._create_transform_to_payload_mapping_structure(payloads, transforms)

    def parse_filter_options(self, filter_options_dict):
        pass

    def _create_transform_to_payload_mapping_structure(self, payloads_list, transforms_list):
        """Generates the transform stage names as per payloads from the transforms list"""
        if not transforms_list:
            logger.error("No transforms found for message to generate transform steps")
            return None

        self.transform_stages = []
        current_channel = ""
        for current_transform in transforms_list:
            # current_stage = {}
            channel_name = (current_transform.get(TRANSFORM_CHANNEL))
            if channel_name != current_channel:
                self._create_channel_stage(channel_name)
                current_channel = channel_name
            prefix = current_transform.get(TRANSFORM_NAME)
            for current_step in current_transform.get(TRANSFORM_STEPS):
                step_name = current_step.get(TRANSFORM_STEP_NAME)
                if step_name in self.TRANSFORM_IGNORE_STEPS:
                    continue
                self._create_transform_stage(prefix, current_step)
        self._add_remaining_payloads(payloads_list)
        if self._is_verbose:
            self._output_stage_struct()
    
    def _add_remaining_payloads(self, payloads_list):
        last_payload_index = max([transform_stage[PAYLOAD_INDEX] for transform_stage in self.transform_stages if
                                  transform_stage[PAYLOAD_INDEX] != -1])
        last_payload_index = last_payload_index + 1
        payloads_found = False
        for current_payload in payloads_list[last_payload_index:]:
            if current_payload[TRACKING_POINT].startswith("PAYLOAD ["):
                payloads_found = True
                self._create_step(current_payload[TRACKING_POINT])
            # Break out once we have processed the group of payloads
            elif payloads_found:
                break

    def _create_channel_stage(self, channel_name):
        self._create_step(channel_name)

    def _create_transform_stage(self, prefix, step):
        step_name = step.get(TRANSFORM_STEP_NAME)
        step_type = step.get(TRANSFORM_STEP_TYPE)
        translated_type = translate_step_type_to_payload_type(step_type)
        stage_name = "{} - {}({})".format(translated_type, prefix, step_name)
        self._create_step(stage_name, step)

    def _create_step(self, step_name, step=None):
        self.transform_stages.append({NAME: step_name,
                                      PAYLOAD_INDEX: get_payload_index(step_name, self.payloads),
                                      STEP: step})

    def _upsert_step(self, step_name, step=None):
        original_payload_position = get_payload_index(step_name, self.payloads)
        new_transform_stage = {NAME: step_name, PAYLOAD_INDEX: original_payload_position, STEP: step}
        transform_stage_payload_indexes = [x[PAYLOAD_INDEX] for x in self.transform_stages]
        insert_position = 0
        while insert_position < len(transform_stage_payload_indexes):
            if original_payload_position > transform_stage_payload_indexes[insert_position]:
                pass
            else:
                break
            insert_position = insert_position + 1
        self.transform_stages.insert(insert_position, new_transform_stage)

    def _get_transform_stage_names(self):
        return [x[NAME] for x in self.transform_stages]

    def _output_stage_struct(self):
        for stage in self.transform_stages:
            logger.info("{}, payload: {}, step: {}".format(stage[NAME], stage[PAYLOAD_INDEX], self._step_to_str(stage[STEP])))

    def _step_to_str(self, step):
        if step:
            return "{}-{}".format(step[TRANSFORM_STEP_TYPE], step[URL])
        return ""

    def _get_payload(self, stage):
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
                missing_json_fields_map = get_missing_movement_line_fields_for_payload(self._get_payload(transform_stage))
                self._print_missing_movement_line_fields(missing_json_fields_map)
                if missing_json_fields_map:
                    fields_set = self._get_missing_fields_set(missing_json_fields_map)
                    # Sort the results for easier reading and to align results set
                    self._add_stage_results(fields_set, TransformStage.json_missing_fields)
                    continue
                else:
                    # Unable to continue
                    logger.error("No missing fields found for transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            elif transform_stage[NAME] == "TRANSFORM - Movement - COP(Convert V5 To Movement JSON)" and self._is_xslt_transform(transform_stage):
                missing_fields = self._get_stage_results(TransformStage.json_missing_fields)
                if not missing_fields:
                    # Unable to continue
                    logger.error("No missing fields found to process at stage: [{}]".format(transform_stage[NAME]))
                    return False
                xsl_url = self._get_xsl_transform_url(transform_stage)
                field_xpaths_map = self.xsl_parser.parse(xsl_url, missing_fields)
                if field_xpaths_map:
                    self._add_mapped_stage_results(field_xpaths_map, TransformStage.v5_to_movement_xpaths)
                    continue
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            elif transform_stage[NAME] == "TRANSFORM - Movement - COP(IDOC to F4Fv5 XML)" and self._is_xslt_transform(transform_stage):
                missing_field_xpaths = self._get_stage_results(TransformStage.v5_to_movement_xpaths)
                if not missing_field_xpaths:
                    # Unable to continue
                    logger.error("No missing field xpaths found to process at stage: [{}]".format(transform_stage[NAME]))
                    return False
                results_list = []
                xsl_url = self._get_xsl_transform_url(transform_stage)
                for xpath in missing_field_xpaths:
                    result = self.xsl_parser.parse_xsl(xsl_url, xpath)
                    if not result:
                        logger.error("Failed to find xpath mapping for {} within stage: [{}]".format(xpath, transform_stage[NAME]))
                    else:
                        results_list.append(result)
                if results_list:
                    self._add_stage_results(results_list, TransformStage.idoc_to_f4fv5_xpaths)
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            elif transform_stage[NAME] == "IN":
                missing_field_xpaths = self._get_stage_results(TransformStage.idoc_to_f4fv5_xpaths)
                if not missing_field_xpaths:
                    # Unable to continue
                    logger.error("No missing field xpaths found to process at stage: [{}]".format(transform_stage[NAME]))
                    return False
                results_list = []
                for xpath in missing_field_xpaths:
                    payload_str = self._get_payload(transform_stage).get(PAYLOAD)
                    result = get_xpath_text(payload_str, xpath)
                    if not result:
                        logger.error("Failed to find xpath mapping for {} within stage: [{}]".format(xpath, transform_stage[NAME]))
                    else:
                        results_list.append(result)
                if results_list:
                    self._add_stage_results(results_list, TransformStage.idoc)
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage[NAME]))
                    return False

            else:
                logger.debug("Ignoring transform stage: [{}]".format(transform_stage[NAME]))
        return True

    def _print_missing_movement_line_fields(self, fields_map):
        if fields_map:
            for line, fields in fields_map.items():
                logger.info("Movement line[{}] missing fields: [{}]".format(line, fields))
        else:
            logger.error("No missing fields found for movement message")

    def _get_missing_fields_set(self, fields_map):
        fields_set = set()
        fields_set.update(reduce(operator.concat, fields_map.values()))
        # Convert to sorted list
        as_list = list(fields_set)
        as_list.sort()
        logger.info("Distinct missing movement fields set: [{}]".format(as_list))
        return as_list

    def _add_stage_results(self, data, stage):
        logger.debug("Adding data for stage: {}, values: {}".format(stage, data))
        self.results_map[stage] = data

    def _add_mapped_stage_results(self, data_map, stage):
        fields = list(data_map.keys())
        fields.sort()
        self.results_map[stage] = [data_map[key] for key in fields]

    def _get_stage_results(self, stage):
        if stage in self.results_map:
            return self.results_map[stage]
        return None

    def _is_xslt_transform(self, transform_stage):
        return transform_stage and STEP in transform_stage and self._is_xslt_transform_step(transform_stage[STEP])

    def _is_xslt_transform_step(self, transform_step):
        return transform_step and transform_step.get(TRANSFORM_STEP_TYPE) == "XALAN"

    def _get_xsl_transform_url(self, transform_stage):
        if transform_stage and STEP in transform_stage and URL in transform_stage[STEP]:
            return transform_stage[STEP].get(URL)
        return None

    def _restructure_column_data_to_rows(self, data):
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

    def _restructure_column_data_to_rows_by_index(self, data):
        records = []
        sample_row_data = data.get(0)
        row_count = len(sample_row_data) if sample_row_data else 0

        column_headings = list(data.keys())
        column_headings.sort()
        for counter in range(row_count):
            row_items = []
            for stage in self.processed_transform_stages:
                if data.get(stage) is not None:
                    if isinstance(data.get(stage), list):
                        stage_list = data.get(stage)
                    row_items.append(stage_list[counter] if stage_list and counter < len(stage_list) else "")
                else:
                    row_items.append("")
            records.append(row_items)
        return records

    def get_results_records(self):
        return self._restructure_column_data_to_rows(self.results_map)


class ConfigurableTransformStagesAnalyser(TransformStagesAnalyser):

    # Overridden
    def parse_filter_options(self, filter_options_dict):
        self.include_transforms = ConfigurableTransformStagesAnalyser._get_filter_option(filter_options_dict, "include_transforms")
        self.exclude_transforms = ConfigurableTransformStagesAnalyser._get_filter_option(filter_options_dict, "exclude_transforms")
        self.include_payloads = ConfigurableTransformStagesAnalyser._get_filter_option(filter_options_dict, "include_payloads")
        self.exclude_payloads = ConfigurableTransformStagesAnalyser._get_filter_option(filter_options_dict, "exclude_payloads")

        self.fields_parser = DocumentEmptyFieldsParser(filter_options_dict)

    @staticmethod
    def _get_filter_option(filter_options_dict, parameter_name):
        if filter_options_dict and parameter_name in filter_options_dict:
            return filter_options_dict[parameter_name]
        return None

    def _include_transform_step(self, step_name):
        if self.include_transforms and step_name in self.include_transforms:
            return True
        return False

    def _exclude_transform_step(self, step_name):
        if self.exclude_transforms and step_name in self.exclude_transforms:
            return True
        return False

    # Overridden
    def _create_transform_to_payload_mapping_structure(self, payloads_list, transforms_list):
        """Generates the transform stage names as per payloads from the transforms list"""
        if not transforms_list:
            logger.error("No transforms found for message to generate transform steps")
            return None

        self.transform_stages = []
        current_channel = ""
        # Iterate through top level transforms (each transform can have a number of transform steps)
        for current_transform in transforms_list:
            # The payloads list will also have the transform channel name as the tracking-point ie IN
            channel_name = (current_transform.get(TRANSFORM_CHANNEL))
            if channel_name != current_channel:
                current_channel = channel_name
                if not self._exclude_transform_step(channel_name):
                    self._create_channel_stage(channel_name)

            prefix = current_transform.get(TRANSFORM_NAME)
            for current_step in current_transform.get(TRANSFORM_STEPS):
                step_name = current_step.get(TRANSFORM_STEP_NAME)
                if self._exclude_transform_step(step_name):
                    continue
                if self._include_transform_step(step_name) or self._is_xslt_transform_step(current_step):
                    self._create_transform_stage(prefix, current_step)
        # Add any additional payloads as indicated by their tracking-points
        self._add_remaining_payloads(payloads_list)
        if self._is_verbose:
            self._output_stage_struct()

    # Overridden
    def _add_remaining_payloads(self, payloads_list):
        existing_payload_names = self._get_transform_stage_names()
        for current_payload in payloads_list:
            if current_payload[TRACKING_POINT] in existing_payload_names:
                continue
            if self.exclude_payloads and current_payload[TRACKING_POINT] in self.exclude_payloads:
                continue
            if self.include_payloads and current_payload[TRACKING_POINT] in self.include_payloads:
                self._upsert_step(current_payload[TRACKING_POINT])

    def _get_missing_fields_set_for_payload(self, payload_object):
        result = self.fields_parser.parse(payload_object)
        field_set = FlattenJsonOutputToCSV.to_set(result)
        field_list = []
        if field_set:
            field_list = list(field_set)
            field_list.sort()
        # missing_json_fields_map = get_missing_movement_line_fields_for_payload(payload_object)
        # self._print_missing_movement_line_fields(missing_json_fields_map)
        # if missing_json_fields_map:
        #     # Create a unique set of fields from the missing fields map
        #     fields_set = self._get_missing_fields_set(missing_json_fields_map)
        #     return fields_set
        # return None
        return field_list

    # Overridden
    def analyse(self):
        """Iterate through transforms with corresponding payloads and trace backwards the missing fields to the original document,
        all results go in a table with rows for each field and the columns being the transform stages"""
        # Go through in reverse order
        self.processed_transform_stages = []
        self.processed_transform_stage_names = []
        first_payload_index = len(self.transform_stages) - 1
        for index, transform_stage in enumerate(reversed(self.transform_stages)):
            transform_stage_name = transform_stage.get(NAME)
            logger.info("Processing stage: {} name: [{}]".format(index, transform_stage_name))
            # Get initial empty fields
            # We expect the payload to be a json or xml of document format ie having headers and lines
            if index == 0:
                # Get empty fields set
                fields_set = self._get_missing_fields_set_for_payload(self._get_payload(transform_stage))
                self.__add_processed_transform_stage(index, transform_stage_name)
                if fields_set:
                    self.__add_stage_results_by_index(fields_set, index)
                    logger.info("Adding results for initial transform stage: {}".format(index))
                    continue
                else:
                    # Unable to continue
                    logger.error("No missing fields found for transform stage: [{}]".format(transform_stage_name))
                    return False

            # If this is the final payload to process, ie the first one from the customer then resolve the collected
            # xpaths against this doc
            if index == first_payload_index:
                missing_field_xpaths = self.__get_previous_stage_results_by_index(index)
                self.__add_processed_transform_stage(index, transform_stage_name)
                if not missing_field_xpaths:
                    # Unable to continue
                    logger.error("No missing field xpaths found to process at stage: [{}]".format(transform_stage_name))
                    return False
                results_list = self._resolve_xpaths_against_payload(transform_stage, missing_field_xpaths)
                if results_list:
                    self.__add_stage_results_by_index(results_list, index)
                    logger.info("Adding results for final transform stage: {}".format(index))
                    continue
                else:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage_name))
                    return False

            # Any non transform payload will be ignored
            elif self._is_xslt_transform(transform_stage):
                missing_fields = self.__get_previous_stage_results_by_index(index)
                self.__add_processed_transform_stage(index, transform_stage_name)
                if not missing_fields:
                    # Unable to continue
                    logger.error("No missing fields found to process at stage: [{}]".format(transform_stage_name))
                    return False

                # The first transform must lookup the missing text fields against an xsl
                # subsequent transform lookups are xpaths against an xsl
                failed_to_resolve = False
                if self._is_first_transform_step(index, transform_stage):
                    field_xpaths_map = self._get_xpaths_from_fields(transform_stage, missing_fields)
                    if field_xpaths_map:
                        self.__add_mapped_stage_results_by_index(field_xpaths_map, index)
                        logger.info("Adding results for intermediate(1) transform stage: {}".format(index))
                    else:
                        failed_to_resolve = True
                else:
                    results_list = self._resolve_xpaths_against_xsl(transform_stage, missing_fields)
                    if results_list:
                        self.__add_stage_results_by_index(results_list, index)
                        logger.info("Adding results for intermediate(2) transform stage: {}".format(index))
                    else:
                        failed_to_resolve = True
                if failed_to_resolve:
                    logger.error("Failed to find xpaths for missing fields from transform stage: [{}]".format(transform_stage_name))
                    return False

            else:
                logger.debug("Ignoring transform stage: [{}], {}".format(transform_stage_name, index))
        return True

    def __add_mapped_stage_results_by_index(self, data_map, stage_index):
        fields = list(data_map.keys())
        # Sort the results for easier reading and to align results set
        fields.sort()
        self.results_map[stage_index] = [data_map[key] for key in fields]

    def __add_stage_results_by_index(self, data, stage_index):
        logger.debug("Adding data for stage: {}, values: {}".format(stage_index, data))
        self.results_map[stage_index] = data

    def __get_stage_results_by_index(self, stage_index):
        if stage_index in self.results_map:
            return self.results_map[stage_index]
        return None

    def __get_previous_stage_index(self, index):
        current_keys = list(self.results_map.keys())
        current_keys.sort()
        current_pos = 0
        last_value = current_keys[0]
        while current_pos < len(current_keys):
            if current_keys[current_pos] < index:
                pass
            elif index >= current_keys[current_pos]:
                return None if current_pos == 0 else last_value
            last_value = current_keys[current_pos]
            current_pos = current_pos + 1
        return last_value

    def __get_previous_stage_results_by_index(self, index):
        """to get the previous index results from the given index"""
        previous_index = self.__get_previous_stage_index(index)
        if previous_index is not None:
            return self.results_map[previous_index]
        return None

    def _resolve_xpaths_against_payload(self, transform_stage, missing_field_xpaths):
        results_list = []
        if missing_field_xpaths:
            payload_str = self._get_payload(transform_stage).get(PAYLOAD)
            for xpath in missing_field_xpaths:
                result = get_xpath_text(payload_str, xpath)
                if result:
                    results_list.append(result)
                else:
                    logger.error("Failed to find xpath mapping for {} within stage: [{}]".format(xpath, transform_stage.get(NAME)))
        return results_list

    def _resolve_xpaths_against_xsl(self, transform_stage, missing_field_xpaths):
        results_list = []
        if missing_field_xpaths:
            xsl_url = self._get_xsl_transform_url(transform_stage)
            for xpath in missing_field_xpaths:
                result = self.xsl_parser.parse_xsl(xsl_url, xpath)
                if not result:
                    logger.error("Failed to find xpath mapping for {} within stage: [{}]".format(xpath, transform_stage.get(NAME)))
                else:
                    results_list.append(result)
        return results_list

    def _get_xpaths_from_fields(self, transform_stage, missing_fields):
        if missing_fields:
            xsl_url = self._get_xsl_transform_url(transform_stage)
            field_xpaths_map = self.xsl_parser.parse(xsl_url, missing_fields)
            return field_xpaths_map
        return None

    def _is_first_transform_step(self, index, transform_stage):
        # We don't consider the first item a transform step
        if index == 0:
            return False
        # Skip over initial non transforms
        reversed_transforms = list(reversed(self.transform_stages))
        # reversed_transforms.reverse()
        for x in range(1, len(self.transform_stages)):
            if self._is_xslt_transform(reversed_transforms[x]):
                return x == index
        return False

    # Overridden
    def get_results_records(self):
        print("Processed stage names: " + ', '.join(self.processed_transform_stage_names))
        return self._restructure_column_data_to_rows_by_index(self.results_map)

    def __add_processed_transform_stage(self, index, stage_name):
        self.processed_transform_stages.append(index)
        self.processed_transform_stage_names.append(stage_name)

