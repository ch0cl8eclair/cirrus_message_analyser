import os
import unittest
import json

from main.algorithms.empty_fields import DocumentMandatoryFieldsParser
from test.test_empty_fields import AbstractFieldsParserTest
from test.test_utils import read_payload_file

XML_MOVEMENT_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_payload_6.xml')
JSON_PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_payload_7.json')


class DocumentMandatoryFieldsParserTest(AbstractFieldsParserTest):

    def createSUT(self, parameters_map):
        return DocumentMandatoryFieldsParser(parameters_map)

    def test_parse_json_payload_lines_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_lines_mandatory_fields": ["order_qty", "order_uom"],
            "type": "lines"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        print(result_map)
        self.assertIsNotNone(result_map)
        self.assertHasNoHeader(result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_json_payload_all(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_header_mandatory_fields": ["shipto_address_4", "order_date"],
            "document_lines_mandatory_fields": ["order_qty", "order_uom"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_json_payload_no_mandatory_fields(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": []}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_json_payload_exclude_non_existing(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["non_existing"],
            "line_exclude_fields": ["non_existing"],
            "document_header_mandatory_fields": ["shipto_address_4", "order_date", "non_existing"],
            "document_lines_mandatory_fields": ["order_qty", "order_uom", "non_existing"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date", "non_existing"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom", "non_existing"]}]', result_map)

    def test_parse_json_payload_header_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_header_mandatory_fields": ["shipto_address_4", "order_date"],
            "type": "header"
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
            "document_header_mandatory_fields": ["shipto_address_4", "order_date"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_json_payload_with_include_filter_with_lines(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_uom"],
            "document_header_mandatory_fields": ["shipto_address_4"],
            "document_lines_mandatory_fields": ["order_uom"],
            "type": "all"
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
            "document_header_mandatory_fields": ["shipto_address_4"],
            "document_lines_mandatory_fields": [ "order_uom"],
            "type": "all"
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
            "document_header_mandatory_fields": ["shipto_address_4"],
            "document_lines_mandatory_fields": ["order_qty"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, JSON_PAYLOAD_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty"]}]', result_map)

    def test_parse_xml_json_payload_lines_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_lines_mandatory_fields": ["order_qty", "order_uom"],
            "type": "lines"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        print(result_map)
        self.assertIsNotNone(result_map)
        self.assertHasNoHeader(result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_xml_json_payload_all(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_header_mandatory_fields": ["shipto_address_4", "order_date"],
            "document_lines_mandatory_fields": ["order_qty", "order_uom"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom"]}]', result_map)

    def test_parse_xml_json_payload_no_mandatory_fields(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": []}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_xml_json_payload_exclude_non_existing(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["non_existing"],
            "line_exclude_fields": ["non_existing"],
            "document_header_mandatory_fields": ["shipto_address_4", "order_date", "non_existing"],
            "document_lines_mandatory_fields": ["order_qty", "order_uom", "non_existing"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date", "non_existing"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty", "order_uom", "non_existing"]}]', result_map)

    def test_parse_xml_json_payload_header_only(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_header_mandatory_fields": ["shipto_address_4", "order_date"],
            "type": "header"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_xml_json_payload_with_include_filter(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4"],
            "line_include_fields": ["order_uom"],
            "document_header_mandatory_fields": ["shipto_address_4", "order_date"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4", "order_date"]}', result_map)
        self.assertHasNoLines(result_map)

    def test_parse_xml_json_payload_with_include_filter_with_lines(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_uom"],
            "document_header_mandatory_fields": ["shipto_address_4"],
            "document_lines_mandatory_fields": ["order_uom"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_xml_json_payload_with_exclude_filter(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_exclude_fields": ["order_date"],
            "line_exclude_fields": ["order_qty"],
            "document_header_mandatory_fields": ["shipto_address_4"],
            "document_lines_mandatory_fields": [ "order_uom"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_uom"]}]', result_map)

    def test_parse_xml_json_payload_with_include_exclude_filters(self):
        parameters_map = {
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "header_include_fields": ["shipto_address_4", "movement_lines"],
            "line_include_fields": ["order_qty"],
            "header_exclude_fields": ["order_date"],
            "line_exclude_fields": ["order_uom"],
            "document_header_mandatory_fields": ["shipto_address_4"],
            "document_lines_mandatory_fields": ["order_qty"],
            "type": "all"
        }
        result_map = self.run_sut(parameters_map, XML_MOVEMENT_FILE)
        self.assertIsNotNone(result_map)
        self.assertHasHeaderValues('{"index": 1, "header_fields": ["shipto_address_4"]}', result_map)
        self.assertHasLineValues('[{"index": 1, "fields": ["order_qty"]}]', result_map)


if __name__ == '__main__':
    unittest.main()