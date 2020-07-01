import os
import unittest
import importlib
import json
from main.cli.cli_parser import parse_command_line_statement
from main.config.constants import DataRequisites
from main.model.message_model import Message
from test.test_utils import read_payload_file

JSON_PAYLOADS_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_movement_post_error_payloads.json')


def create_algo_instance(algorithm_name):
    algorithm_module = importlib.import_module("main.algorithms.algorithms")
    AlgoClass = getattr(algorithm_module, algorithm_name)
    algorithm_instance = AlgoClass()
    return algorithm_instance


class MockDataEnricher:
    def __init__(self, payload_structure):
        self.message = Message()
        self.message.add_payloads(payload_structure)


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

    def create_algorithm_parameters(self):
        parameters_map = {
            "payload-tracking-point": "PAYLOAD [movement JSON POST request]",
            "document_header_root": "movements",
            "document_lines_root": "movement_lines",
            "type": "lines"
        }
        return parameters_map

    def test_algorithm_processing(self):
        sut = self.createSUT()
        sut.set_parameters(self.create_algorithm_parameters())
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

    def create_algorithm_parameters(self):
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
        sut.set_parameters(self.create_algorithm_parameters())
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


if __name__ == '__main__':
    unittest.main()
