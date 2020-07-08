import os
import unittest
import json
from lxml import etree

from main.algorithms.empty_fields import DocumentEmptyFieldsParser
from main.config.constants import FIELD_TYPE
from test.test_utils import read_payload_file

XML_MOVEMENT_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_payload_6.xml')
JSON_PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_payload_7.json')


class AbstractFieldsParserTest(unittest.TestCase):

    def run_sut(self, parameters_map, payload_file):
        sut = self.createSUT(parameters_map)
        payload_str = read_payload_file(payload_file)
        payload_dict = {"payload": payload_str}
        return sut.parse(payload_dict)

    def createSUT(self, parameters_map):
        """To be implemented by subclass"""
        return None

    def assertHasNoHeader(self, result_map, document_index=0):
        self.assertEqual(0, len(result_map.get("documents")[document_index].get("header_fields")))

    def assertHasNoLines(self, result_map, document_index=0):
        lines = result_map.get("documents")[document_index].get("document_lines")
        self.assertTrue(lines is None or len(lines) == 0)

    def assertHasLineValues(self, expected_json, result_map, document_index=0):
        expected_lines = json.loads(expected_json)
        actual_lines = result_map.get("documents")[document_index].get("document_lines")
        self.assertEqual(len(expected_lines) if expected_lines else 0, len(actual_lines) if actual_lines else 0, "Number of fields do not match")
        for expected, actual in zip(expected_lines, actual_lines):
            for ek, ev in expected.items():
                self.assertEqual(ev, actual[ek])

    def assertHasHeaderValues(self, expected_json, result_map, document_index=0):
        expected_document = json.loads(expected_json)
        expected_fields = expected_document["header_fields"]
        actual_document = result_map.get("documents")[document_index]
        actual_fields = actual_document.get("header_fields")
        self.assertEqual(1, len(result_map.get("documents")))
        self.assertEqual(expected_document["index"], actual_document["index"])
        self.assertEqual(len(expected_fields), len(actual_fields))
        self.assertEqual(expected_fields, actual_fields)


class DocumentEmptyFieldsParserTest(AbstractFieldsParserTest):

    def createSUT(self, parameters_map):
        return DocumentEmptyFieldsParser(parameters_map)

    def test_parse_json_payload_lines_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "lines"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasNoHeader(result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_json_payload_all(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_json_payload_exclude_non_existing(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["non_existing"],
            "line_exclude_fields": ["non_existing"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_json_payload_header_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "header"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_json_payload_with_include_filter(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4"],
            "line_include_fields": ["order_uom"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_json_payload_with_include_filter_with_lines(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_uom"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_json_payload_with_exclude_filter(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["order_date"],
            "line_exclude_fields": ["order_qty"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_json_payload_with_include_exclude_filters(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_qty"],
            "header_exclude_fields": ["order_date"],
            "line_exclude_fields": ["order_uom"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty"]}]', result_map)

    def test_parse_xml_payload_lines_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "lines"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasNoHeader(result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_xml_payload_all(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_xml_payload_exclude_non_existing(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["non_existing"],
            "line_exclude_fields": ["non_existing"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_xml_payload_header_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "header"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_xml_payload_with_include_filter(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4"],
            "line_include_fields": ["order_uom"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_xml_payload_with_include_filter_with_lines(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_uom"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_xml_payload_with_exclude_filter(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["order_date"],
            "line_exclude_fields": ["order_qty"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_xml_payload_with_include_exclude_filters(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_qty"],
            "header_exclude_fields": ["order_date"],
            "line_exclude_fields": ["order_uom"],
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty"]}]', result_map)

    def test_format_to_csv(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            FIELD_TYPE: "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)
        csv_2d_array = DocumentEmptyFieldsParser.format_as_csv(result_map)
        self.assertEqual(2, len(csv_2d_array))
        self.assertEqual([1, 'shipto_address_4, order_date', None, None], csv_2d_array[0])
        self.assertEqual([1, None, 1, 'order_qty, order_uom'], csv_2d_array[1])

    def test_read_xml(self):
        payload_str = read_payload_file(XML_MOVEMENT_FILE)
        xml = bytes(bytearray(payload_str, encoding='utf-8'))
        tree = etree.XML(xml)
        result = tree.find("movements")
        print(type(result))
        print(result)


if __name__ == '__main__':
    unittest.main()
