import json
import os
import unittest
from main.algorithms.payload_transform_mapper import PayloadTransformMapper
from test.test_utils import read_json_data_file

PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_movement_post_error_payloads.json')
TRANSFORM_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_msg_transforms.json')


class PayloadTransformMapperTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.payloads_list = read_json_data_file(PAYLOAD_FILE)
        cls.transforms_list = read_json_data_file(TRANSFORM_FILE)

    def test_map(self):
        sut = PayloadTransformMapper(self.payloads_list, self.transforms_list, MockCirrusProxy())
        sut.map()
        results = sut.get_records()
        self.assertEqual(11, len(self.payloads_list))
        self.assertEqual(11, len(results))

        self.assert_output_record(results, 0, None, None, None, None)
        self.assert_output_record(results, 1, "TRANSFORM", "Extension Replacement", "http://mappings.f4f.com/prd/uk0000000037/ext-replacement.xsl", "XALAN")
        self.assert_output_record(results, 2, "TRANSFORM", "IDOC to F4Fv5 XML", "http://mappings.f4f.com/prd/uk0000000037/ZESADV_F4Fv5Movement.xsl", "XALAN")
        self.assert_output_record(results, 3, "VALIDATE", "F4F XML Validation", "http://mappings.f4f.com/F4FXML/Schemas/v5/movement.xsd", "XSD")
        self.assert_output_record(results, 4, None, None, None, None)
        self.assert_output_record(results, 5, None, None, None, None)
        self.assert_output_record(results, 6, "TRANSFORM", "Convert V5 To Movement JSON", "http://mappings.f4f.com/prd/uk0000000036/F4Fv5Movement_JSONMovementPost.xsl", "XALAN")
        self.assert_output_record(results, 7, "TRANSFORM", "JSON Transform", "", "XMLJSON")
        self.assert_output_record(results, 8, None, None, None, None)
        self.assert_output_record(results, 9, None, None, None, None)
        self.assert_output_record(results, 10, None, None, None, None)

    def assert_output_record(self, results, index, data_type, name, url, transform_type):
        self.assertEqual(self.payloads_list[index]["tracking-point"], results[index]["tracking-point"])
        if not data_type:
            self.assertFalse("type" in results[index])
            self.assertFalse("transform-step-name" in results[index])
            self.assertFalse("url" in results[index])
            self.assertFalse("transform-step-type" in results[index])
        else:
            self.assertEqual(data_type, results[index]["type"])
            self.assertEqual(name, results[index]["transform-step-name"])
            self.assertEqual(url, results[index]["url"])
            self.assertEqual(transform_type, results[index]["transform-step-type"])

    def test_reset(self):
        # Run normally
        sut = PayloadTransformMapper(self.payloads_list, self.transforms_list, MockCirrusProxy())
        sut.map()
        results = sut.get_records()
        self.assertEqual(11, len(results))
        # now reset and check it worked
        transform_sub_list = self.transforms_list[0:1]
        sut.reset(transform_sub_list)
        self.assertEqual([], sut.get_records())
        self.assertEqual(sut.transforms, transform_sub_list)

    def test_create_record(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        transform_obj = self.transforms_list[0]
        payload = self.payloads_list[0]
        transform_step = transform_obj.get("transform-steps")[0]
        result = sut.wrapped_create_record(payload, transform_obj, transform_step)
        self.assertEqual("IN", result.get("tracking-point"))
        self.assertEqual("TRANSFORM", result.get("type"))
        self.assertEqual("Extension Replacement", result.get("transform-step-name"))
        self.assertEqual("http://mappings.f4f.com/prd/uk0000000037/ext-replacement.xsl", result.get("url"))
        self.assertEqual("XALAN", result.get("transform-step-type"))

    def test_get_variable_resolved_url_null(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        result = sut.wrapped_get_variable_resolved_url({}, {"url": None})
        self.assertIsNone(result)

    def test_get_variable_resolved_url_normal(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        transform_obj = self.transforms_list[0]
        transform_step = transform_obj.get("transform-steps")[0]
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/prd/uk0000000037/ext-replacement.xsl", result)

    def test_get_variable_resolved_url_single_var(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        metadata_vars_dict = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        metadata_vars_dict["metadata-name"] = "ENV"
        metadata_vars_dict["metadata-value"] = "oat"
        transform_obj = {"transform-pre-metadata": [metadata_vars_dict]}
        transform_step = {"url": "http://mappings.f4f.com/${ENV}/uk0000000037/ext-replacement.xsl"}
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/oat/uk0000000037/ext-replacement.xsl", result)

    def test_get_variable_resolved_url_empty_var(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        metadata_vars_dict = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        metadata_vars_dict["metadata-name"] = "ENV"
        metadata_vars_dict["metadata-value"] = None
        transform_obj = {"transform-pre-metadata": [metadata_vars_dict]}
        transform_step = {"url": "http://mappings.f4f.com/${ENV}/uk0000000037/ext-replacement.xsl"}
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/live/uk0000000037/ext-replacement.xsl", result)

    def test_get_variable_resolved_url_env_dynamic_lookup_var(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        metadata_vars_dict = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        metadata_vars_dict["metadata-name"] = "ENV"
        metadata_vars_dict["metadata-value"] = "${ENV}"
        transform_obj = {"transform-pre-metadata": [metadata_vars_dict]}
        transform_step = {"url": "http://mappings.f4f.com/${ENV}/uk0000000037/ext-replacement.xsl"}
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/live/uk0000000037/ext-replacement.xsl", result)

    def test_get_variable_resolved_url_env_dynamic_lookup_var_failure(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy(False))
        metadata_vars_dict = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        metadata_vars_dict["metadata-name"] = "ENV"
        metadata_vars_dict["metadata-value"] = "${ENV}"
        transform_obj = {"transform-pre-metadata": [metadata_vars_dict]}
        transform_step = {"url": "http://mappings.f4f.com/${ENV}/uk0000000037/ext-replacement.xsl"}
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/${ENV}/uk0000000037/ext-replacement.xsl", result)

    def test_get_variable_resolved_url_multi_var(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        metadata_vars_dict = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        metadata_vars_dict["metadata-name"] = "SYS"
        metadata_vars_dict["metadata-value"] = "DEV"
        metadata_vars_dict2 = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        metadata_vars_dict2["metadata-name"] = "ADAPTER"
        metadata_vars_dict2["metadata-value"] = "uk0000000037"
        transform_obj = {"transform-pre-metadata": [metadata_vars_dict, metadata_vars_dict2]}
        transform_step = {"url": "http://mappings.f4f.com/${SYS}/${ADAPTER}/ext-replacement.xsl"}
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/DEV/uk0000000037/ext-replacement.xsl", result)

    def test_get_variable_resolved_url_failed_replacement(self):
        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        metadata_vars_dict = dict(self.transforms_list[0].get("transform-pre-metadata")[0])
        transform_obj = {"transform-pre-metadata": [metadata_vars_dict]}
        transform_step = {"url": "http://mappings.f4f.com/${gremlin}/uk0000000037/ext-replacement.xsl"}
        result = sut.wrapped_get_variable_resolved_url(transform_obj, transform_step)
        self.assertEqual("http://mappings.f4f.com/${gremlin}/uk0000000037/ext-replacement.xsl", result)

    def test_find_transform_metadata_simple(self):
        search_key = "transform-pre-metadata"
        transform_obj = dict(self.transforms_list[0])
        metadata_key = "ENV"
        metadata_value = "${ENV}"

        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        result = sut.wrapped_find_transform_metadata(transform_obj, search_key, metadata_key)
        self.assertEqual(metadata_value, result)

    def test_find_transform_metadata_key_with_no_value(self):
        search_key = "transform-pre-metadata"
        metadata_key = "ENV"
        metadata_vars_dict = dict(self.transforms_list[0].get(search_key)[0])
        del metadata_vars_dict["metadata-value"]
        transform_obj = {search_key: [metadata_vars_dict]}

        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        result = sut.wrapped_find_transform_metadata(transform_obj, search_key, metadata_key)
        self.assertIsNone(result)

    def test_find_transform_metadata_key_with_no_key(self):
        search_key = "transform-pre-metadata"
        metadata_key = "ENV"
        metadata_vars_dict = dict(self.transforms_list[0].get(search_key)[0])
        del metadata_vars_dict["metadata-name"]
        transform_obj = {search_key: [metadata_vars_dict]}

        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        result = sut.wrapped_find_transform_metadata(transform_obj, search_key, metadata_key)
        self.assertIsNone(result)

    def test_find_transform_metadata_empty_transform(self):
        search_key = "transform-pre-metadata"
        metadata_key = "ENV"

        sut = PayloadTransformMapperTestSubclass(self.payloads_list, self.transforms_list, MockCirrusProxy())
        result = sut.wrapped_find_transform_metadata({}, search_key, metadata_key)
        self.assertIsNone(result)


class MockCirrusProxy:
    def __init__(self, url_lookup_result=True):
        self.check_result = url_lookup_result

    def check_if_valid_url(self, url):
        return self.check_result


class PayloadTransformMapperTestSubclass(PayloadTransformMapper):
    def wrapped_find_transform_metadata(self, transform_obj, transform_sub_list_name, variable_name):
        return self._find_transform_metadata(transform_obj, transform_sub_list_name, variable_name)

    def wrapped_create_record(self, current_payload, transform_obj, transform_step):
        return self._create_record(current_payload, transform_obj, transform_step)

    def wrapped_get_variable_resolved_url(self, transform_obj, transform_step):
        return self._get_variable_resolved_url(transform_obj, transform_step)


if __name__ == '__main__':
    unittest.main()
