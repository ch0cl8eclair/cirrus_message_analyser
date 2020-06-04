import unittest
import json
import os

from algorithms.payload_operations_test import JSON_MOVEMENT_POST
from main.algorithms.payload_predicates import payloads_match_single_yara_movement_case

MOVEMENT_ERROR_FILE = os.path.join(os.path.dirname(__file__), '../resources/yara_movement_post_error_payloads.json')


class PayloadPredicatesTest(unittest.TestCase):

    def test_payloads_match_single_yara_movement_case(self):
        with open(MOVEMENT_ERROR_FILE) as f:
            payloads_list = json.load(f)
        transform_stages = ["IN",
                            "TRANSFORM - Movement - COP(Extension Replacement)",
                            "TRANSFORM - Movement - COP(IDOC to F4Fv5 XML)",
                            "VALIDATE - Movement - COP(F4F XML Validation)",
                            "ROUTE",
                            "OUT",
                            "TRANSFORM - Movement - COP(Convert V5 To Movement JSON)",
                            "TRANSFORM - Movement - COP(JSON Transform)",
                            "SEND"]
        # ,
        # "PAYLOAD [movement JSON POST request]",
        # "PAYLOAD [Error: HTTP Response: 400]"
        self.assertTrue(payloads_match_single_yara_movement_case(payloads_list, transform_stages))


if __name__ == '__main__':
    unittest.main()
