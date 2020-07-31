import json
import os
import unittest
from main.algorithms.payload_transform_mapper import PayloadTransformMapper

PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_movement_post_error_payloads.json')
TRANSFORM_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_msg_transforms.json')


class PayloadTransformMapperTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(PAYLOAD_FILE, 'r') as myfile:
            payload_data = myfile.read()
        cls.payloads_list = json.loads(payload_data)

        with open(TRANSFORM_FILE, 'r') as transformfile:
            transform_data = transformfile.read()
        cls.transforms_list = json.loads(transform_data)

    def test_map(self):
        sut = PayloadTransformMapper(self.payloads_list, self.transforms_list)
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

    def assert_output_record(self, results, index, type, name, url, transform_type):
        self.assertEqual(self.payloads_list[index]["tracking-point"], results[index]["tracking-point"])
        if not type:
            self.assertFalse("type" in results[index])
            self.assertFalse("transform-step-name" in results[index])
            self.assertFalse("url" in results[index])
            self.assertFalse("transform-step-type" in results[index])
        else:
            self.assertEqual(type, results[index]["type"])
            self.assertEqual(name, results[index]["transform-step-name"])
            self.assertEqual(url, results[index]["url"])
            self.assertEqual(transform_type, results[index]["transform-step-type"])


if __name__ == '__main__':
    unittest.main()
