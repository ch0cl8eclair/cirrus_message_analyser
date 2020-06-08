import json
import os
import unittest

from main.algorithms.payload_predicates import payload_has_json_post_error, payload_is_json_post_request, \
    payload_is_http_error, payload_has_json_mismatch_message

PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_movement_post_error_payloads.json')


class PayloadPredicatesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(PAYLOAD_FILE, 'r') as myfile:
            data = myfile.read()
        cls.payloads_list = json.loads(data)
        
    def test_payload_has_json_post_error(self):
        self.assertTrue(payload_has_json_post_error(self.payloads_list[-1]))
        self.assertFalse(payload_has_json_post_error(self.payloads_list[0]))

    def test_payload_is_http_error(self):
        self.assertTrue(payload_is_http_error(self.payloads_list[-1]))
        self.assertFalse(payload_is_http_error(self.payloads_list[0]))

    def test_payload_has_json_mismatch_message(self):
        self.assertTrue(payload_has_json_mismatch_message(self.payloads_list[-1]))
        self.assertFalse(payload_has_json_mismatch_message(self.payloads_list[0]))

    def test_payload_is_json_post_request(self):
        self.assertTrue(payload_is_json_post_request(self.payloads_list[-2]))
        self.assertFalse(payload_is_json_post_request(self.payloads_list[-1]))


if __name__ == '__main__':
    unittest.main()