import os
import unittest
import importlib
import json
from main.cli.cli_parser import parse_command_line_statement
from main.config.constants import DataRequisites, NAME
from main.model.message_model import Message
from main.model.model_utils import MissingConfigException
from test.test_utils import read_payload_file

JSON_PAYLOADS_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_movement_post_error_payloads.json')
YARA_TRANSFORMS_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_msg_transforms.json')


def create_algo_instance(algorithm_name):
    algorithm_module = importlib.import_module("main.algorithms.algorithms")
    AlgoClass = getattr(algorithm_module, algorithm_name)
    algorithm_instance = AlgoClass()
    return algorithm_instance


class MockCirrusProxy:
    def get(self, url):
        if url == "http://mappings.f4f.com/prd/uk0000000037/ext-replacement.xsl":
            return read_payload_file(os.path.join(os.path.dirname(__file__), './resources/ext-replacement.xsl'))
        elif url == "http://mappings.f4f.com/prd/uk0000000037/ZESADV_F4Fv5Movement.xsl":
            return read_payload_file(os.path.join(os.path.dirname(__file__), './resources/ZESADV_F4Fv5Movement.xsl'))
        elif url == "http://mappings.f4f.com/prd/uk0000000036/F4Fv5Movement_JSONMovementPost.xsl":
            return read_payload_file(os.path.join(os.path.dirname(__file__), './resources/F4Fv5Movement_JSONMovementPost.xsl'))
        raise MissingConfigException("Failed to find requested xsl file in test resources")


class MockDataEnricher:
    def __init__(self, payload_structure, transform_structure=None, rule=None):
        self.message = Message()
        self.message.add_payloads(payload_structure)
        if rule:
            self.message.add_rule(rule)
        if transform_structure:
            self.message.add_transforms(transform_structure)
        self.cirrus_proxy = MockCirrusProxy()

    def add_rule(self, rule):
        self.message.add_rule(rule)


class AbstractAlgorithmTest(unittest.TestCase):
    def get_algorithm_name(self):
        return None

    def createSUT(self,):
        return create_algo_instance(self.get_algorithm_name())

    def mock_data_enricher(self):
        payloads_str = read_payload_file(JSON_PAYLOADS_FILE)
        payload_structure = json.loads(payloads_str)
        data_enricher = MockDataEnricher(payload_structure)
        return data_enricher


class HasEmptyFieldsForPayloadTest(AbstractAlgorithmTest):
    def get_algorithm_name(self):
        return "HasEmptyFieldsForPayload"

    def test_get_data_prerequistites(self):
        sut = self.createSUT()
        expected_set = frozenset([DataRequisites.payloads])
        self.assertEqual(expected_set, sut.get_data_prerequistites())

    def test_analysis_data(self):
        sut = self.createSUT()
        self.assertEqual(True, sut.has_analysis_data())

    def _create_algorithm_parameters(self):
        parameters_map = {
            "payload-tracking-point": "PAYLOAD [movement JSON POST request]",
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "type": "lines"
        }
        return parameters_map

    def test_algorithm_processing(self):
        sut = self.createSUT()
        sut.set_parameters(self._create_algorithm_parameters())
        sut.set_data_enricher(self.mock_data_enricher())
        bool_result = sut.analyse()
        results = sut.get_analysis_data()
        self.assertTrue(bool_result)
        self.assertIsNotNone(results)
        self.assertEqual(2, len(results))
        self.assertEqual(4, len(results[0]))
        self.assertEqual(4, len(results[1]))

        self.assertEqual(1, results[0][0])
        self.assertEqual('', results[0][1])
        self.assertIsNone(results[0][2])
        self.assertIsNone(results[0][3])

        self.assertEqual(1, results[1][0])
        self.assertIsNone(results[1][1])
        self.assertEqual(1, results[1][2])
        self.assertEqual('order_qty, order_uom', results[1][3])


class HasMandatoryFieldsForPayloadTest(AbstractAlgorithmTest):
    def get_algorithm_name(self):
        return "HasMandatoryFieldsForPayload"

    def test_get_data_prerequistites(self):
        sut = self.createSUT()
        expected_set = frozenset([DataRequisites.payloads])
        self.assertEqual(expected_set, sut.get_data_prerequistites())

    def test_analysis_data(self):
        sut = self.createSUT()
        self.assertEqual(True, sut.has_analysis_data())

    def _create_algorithm_parameters(self):
        parameters_map = {
            "payload-tracking-point": "PAYLOAD [movement JSON POST request]",
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_lines_mandatory_fields": ['order_qty', 'order_uom'],
            "type": "lines"
        }
        return parameters_map

    def test_algorithm_processing(self):
        sut = self.createSUT()
        sut.set_parameters(self._create_algorithm_parameters())
        sut.set_data_enricher(self.mock_data_enricher())
        bool_result = sut.analyse()
        results = sut.get_analysis_data()
        self.assertTrue(bool_result)
        self.assertIsNotNone(results)
        self.assertEqual(2, len(results))
        self.assertEqual(4, len(results[0]))
        self.assertEqual(4, len(results[1]))

        self.assertEqual(1, results[0][0])
        self.assertEqual('', results[0][1])
        self.assertIsNone(results[0][2])
        self.assertIsNone(results[0][3])

        self.assertEqual(1, results[1][0])
        self.assertIsNone(results[1][1])
        self.assertEqual(1, results[1][2])
        self.assertEqual('order_qty, order_uom', results[1][3])


class YaraMovementPostJsonTest(AbstractAlgorithmTest):
    def get_algorithm_name(self):
        return "YaraMovementPostJson"

    def test_get_data_prerequistites(self):
        sut = self.createSUT()
        expected_set = frozenset([DataRequisites.payloads, DataRequisites.transforms])
        self.assertEqual(expected_set, sut.get_data_prerequistites())

    def create_rule(self):
        rule_txt = """
          {
    "name": "YARA_MOVEMENTS_BASIC",
    "search_parameters": {
      "source": "uk0000000037",
      "destination": "uk0000000036",
      "type": "movement",
      "message-status": "FAILED"
    },
    "algorithms": ["YaraMovementPostJson"]
  }
        """
        return json.loads(rule_txt)

    def mock_data_enricher(self):
        payload_structure = json.loads(read_payload_file(JSON_PAYLOADS_FILE))
        transforms_structure = json.loads(read_payload_file(YARA_TRANSFORMS_FILE))
        data_enricher = MockDataEnricher(payload_structure, transforms_structure, self.create_rule())
        return data_enricher

    def test_analysis_data(self):
        sut = self.createSUT()
        self.assertEqual(True, sut.has_analysis_data())

    def test_algorithm_processing(self):
        sut = self.createSUT()
        sut.set_data_enricher(self.mock_data_enricher())
        bool_result = sut.analyse()
        results = sut.get_analysis_data()
        self.assertFalse(bool_result)
        self.assertIsNotNone(results)
        print(results)
        self.assertEqual(2, len(results))
        self.assertEqual(4, len(results[0]))

        self.assertEqual("order_qty", results[0][0])
        self.assertEqual('LineComponent/Product/Quantity[@Type=\'Ordered\']', results[0][1])
        self.assertEqual("Z1EDP00/WMENG", results[0][2])
        self.assertEqual("", results[0][3])

        self.assertEqual("order_uom", results[1][0])
        self.assertEqual('LineComponent/Product/Quantity[@Type=\'Ordered\']/@UnitOfMeasure', results[1][1])
        self.assertEqual("Z1EDP00/VRKME", results[1][2])
        self.assertEqual("", results[1][3])


class TransformBacktraceFieldsTest(AbstractAlgorithmTest):
    def get_algorithm_name(self):
        return "TransformBacktraceFields"

    def test_get_data_prerequistites(self):
        sut = self.createSUT()
        expected_set = frozenset([DataRequisites.payloads, DataRequisites.transforms])
        self.assertEqual(expected_set, sut.get_data_prerequistites())

    def create_rule(self):
        rule_txt = """
          {
        "name": "YARA_MOVEMENTS_BASIC",
        "search_parameters": {
          "source": "uk0000000037",
          "destination": "uk0000000036",
          "type": "movement",
          "message-status": "FAILED"
        },
        "algorithms": ["YaraMovementPostJson"]
      }
        """
        return json.loads(rule_txt)

    def mock_data_enricher(self):
        payload_structure = json.loads(read_payload_file(JSON_PAYLOADS_FILE))
        transforms_structure = json.loads(read_payload_file(YARA_TRANSFORMS_FILE))
        data_enricher = MockDataEnricher(payload_structure, transforms_structure, self.create_rule())
        return data_enricher

    def test_analysis_data(self):
        sut = self.createSUT()
        self.assertEqual(True, sut.has_analysis_data())

    def _create_algorithm_parameters(self):
        parameters_map = {
            "include_transforms": ["JSON Transform"],
            "exclude_transforms": ["Extension Replacement", "OUT"],
            "include_payloads": ["PAYLOAD [movement JSON POST request]"],
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "document_lines_mandatory_fields": ['order_qty', 'order_uom'],
            "type": "lines"
        }
        return parameters_map

    def test_algorithm_processing(self):
        sut = self.createSUT()
        sut.set_parameters(self._create_algorithm_parameters())
        sut.set_data_enricher(self.mock_data_enricher())
        print(sut.transform_analyser.transform_stages)
        transform_stage_names = [x[NAME] for x in sut.transform_analyser.transform_stages]
        expected_names = ["IN", "TRANSFORM - Movement - COP(IDOC to F4Fv5 XML)", "TRANSFORM - Movement - COP(Convert V5 To Movement JSON)", "TRANSFORM - Movement - COP(JSON Transform)", "PAYLOAD [movement JSON POST request]"]
        self.assertEqual(expected_names, transform_stage_names)

        bool_result = sut.analyse()
        results = sut.get_analysis_data()
        self.assertFalse(bool_result)
        self.assertIsNotNone(results)
        print(results)
        self.assertEqual(2, len(results))
        self.assertEqual(4, len(results[0]))

        self.assertEqual("order_qty", results[0][0])
        self.assertEqual('LineComponent/Product/Quantity[@Type=\'Ordered\']', results[0][1])
        self.assertEqual("Z1EDP00/WMENG", results[0][2])
        self.assertEqual("", results[0][3])

        self.assertEqual("order_uom", results[1][0])
        self.assertEqual('LineComponent/Product/Quantity[@Type=\'Ordered\']/@UnitOfMeasure', results[1][1])
        self.assertEqual("Z1EDP00/VRKME", results[1][2])
        self.assertEqual("", results[1][3])


if __name__ == '__main__':
    unittest.main()
