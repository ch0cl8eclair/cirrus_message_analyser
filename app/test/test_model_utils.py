import os
import unittest

from main.config.constants import TRANSFORM, VALIDATE
from main.model.model_utils import translate_step_type_to_payload_type, XALAN, SAXON, XMLJSON, JSONXML, \
    is_valid_step_type


class ModelUtilsTest(unittest.TestCase):
    def test_translate_step_type_to_payload_type(self):
        self.assertEqual(TRANSFORM, translate_step_type_to_payload_type(XALAN))
        self.assertEqual(TRANSFORM, translate_step_type_to_payload_type(SAXON))
        self.assertEqual(TRANSFORM, translate_step_type_to_payload_type(XMLJSON))
        self.assertEqual(TRANSFORM, translate_step_type_to_payload_type(JSONXML))
        self.assertEqual(VALIDATE, translate_step_type_to_payload_type("XSD"))
        self.assertEqual(TRANSFORM, translate_step_type_to_payload_type("anything else"))

    def test_is_valid_step_type(self):
        self.assertEqual(True, is_valid_step_type(TRANSFORM, {"transform-step-type": XALAN}))
        self.assertEqual(True, is_valid_step_type(TRANSFORM, {"transform-step-type": SAXON}))
        self.assertEqual(True, is_valid_step_type(TRANSFORM, {"transform-step-type": XMLJSON}))
        self.assertEqual(True, is_valid_step_type(TRANSFORM, {"transform-step-type": JSONXML}))
        self.assertEqual(False, is_valid_step_type(TRANSFORM, {"transform-step-type": "XSD"}))
        self.assertEqual(False, is_valid_step_type(VALIDATE, {"transform-step-type": XALAN}))
        self.assertEqual(True, is_valid_step_type(VALIDATE, {"transform-step-type": "XSD"}))
        self.assertEqual(False, is_valid_step_type(VALIDATE, {"transform-step-type": "SAXON"}))
        self.assertEqual(False, is_valid_step_type(TRANSFORM, {"transform-step-type": "something"}))

    def test_get_matching_transform_step(self):
        pass

    def test_get_matching_transform_and_step(self):
        pass

    def test_get_transform_step_from_payload(self):
        pass

    def test_obtain_transform_details_from_payload_tracking_point(self):
        pass

    def test_get_payload_index(self):
        pass

    def test_get_payload_object(self):
        pass

    def test_get_transform_search_parameters(self):
        pass

    def test_explode_search_criteria(self):
        pass

    def test_filter_transforms(self):
        pass

    def test_extract_search_parameters_from_message_detail(self):
        pass

    def test_get_algorithm_results_per_message(self):
        pass

    def test_prefix_message_id_to_lines(self):
        pass

    def test_merge_message_status_with_algo_results(self):
        pass

    def test_enrich_message_analysis_status_results(self):
        pass

    def test_process_message_payloads(self):
        pass

    def test_get_data_type_for_algorithm(self):
        pass

    def test_get_algorithm_name_from_data_type(self):
        pass


if __name__ == '__main__':
    unittest.main()