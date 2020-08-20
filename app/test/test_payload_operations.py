import unittest
import json
import os
from json import JSONDecoder

from main.algorithms.payload_operations import get_missing_movement_line_fields_for_payload, \
    determine_message_playback_count_from_payloads
from test.test_utils import read_json_data_file

JSON_MOVEMENT_POST = """
  {
    "insertDate": 1590763134000,
    "source": "uk0000000037",
    "destination": "uk0000000036",
    "type": "movement",
    "subType": "Not Available",
    "id": 113040943,
    "unique-id": "07e74747-f58a-49a0-ac77-1a006b748194",
    "tracking-point": "PAYLOAD [movement JSON POST request]",
    "sub-source": "Not Available",
    "sub-destination": "Not Available",
    "sequence-number": 52,
    "compressed": true,
    "content-type": "text/xml",
    "content-encoding": "UTF-8",
    "exception": null,
    "payload": "{\\"movements\\":[{\\"supplier_code\\":\\"HAZ2\\",\\"account_code\\":\\"0000105883\\",\\"account_name\\":\\"HERMOUET\\",\\"movement_type_code\\":\\"D\\",\\"shipto_code\\":\\"0000752752\\",\\"shipto_name\\":\\"M.MARTIN Gérard\\",\\"shipto_address_1\\":\\"LASCOUX\\",\\"shipto_address_2\\":\\"R\\",\\"shipto_address_3\\":\\"FIEF-SAUVIN\\",\\"shipto_address_4\\":null,\\"shipto_postcode\\":\\"49600\\",\\"shipto_country\\":\\"FR\\",\\"shipfrom_name\\":\\"Yara Ambes\\",\\"order_number\\":\\"5503087\\",\\"order_date\\":null,\\"supplier_movement_reference\\":\\"0692169118\\",\\"movement_date\\":\\"2020-05-14\\",\\"requested_delivery_date\\":\\"2020-05-14\\",\\"order_code\\":\\"5503087\\",\\"status_code\\":\\"DS10\\",\\"movement_lines\\":[{\\"order_line_number\\":\\"10\\",\\"product_code\\":\\"PA102G78A\\",\\"product_description\\":\\"EXTRAN 33,5 00 00 / BB 600 kg (AMB)\\",\\"order_qty\\":null,\\"shipto_code\\":\\"0000752752\\",\\"shipfrom_code\\":\\"HAZ2\\",\\"status_code\\":\\"DL10\\",\\"despatched_qty\\":\\"28.200\\",\\"order_uom\\":[],\\"despatched_uom\\":\\"TNE\\",\\"line_number\\":\\"1\\"}]}],\\"transaction_options\\":{\\"continue_on_fail\\":false,\\"rollback_on_error\\":true}}",
    "displayPayload": "{\\"movements\\":[{\\"supplier_code\\":\\"HAZ2\\",\\"account_code\\":\\"0000105883\\",\\"account_name\\":\\"HERMOUET\\",\\"movement_type_code\\":\\"D\\",\\"shipto_code\\":\\"0000752752\\",\\"shipto_name\\":\\"M.MARTIN Gérard\\",\\"shipto_address_1\\":\\"LASCOUX\\",\\"shipto_address_2\\":\\"R\\",\\"shipto_address_3\\":\\"FIEF-SAUVIN\\",\\"shipto_address_4\\":null,\\"shipto_postcode\\":\\"49600\\",\\"shipto_country\\":\\"FR\\",\\"shipfrom_name\\":\\"Yara Ambes\\",\\"order_number\\":\\"5503087\\",\\"order_date\\":null,\\"supplier_movement_reference\\":\\"0692169118\\",\\"movement_date\\":\\"2020-05-14\\",\\"requested_delivery_date\\":\\"2020-05-14\\",\\"order_code\\":\\"5503087\\",\\"status_code\\":\\"DS10\\",\\"movement_lines\\":[{\\"order_line_number\\":\\"10\\",\\"product_code\\":\\"PA102G78A\\",\\"product_description\\":\\"EXTRAN 33,5 00 00 / BB 600 kg (AMB)\\",\\"order_qty\\":null,\\"shipto_code\\":\\"0000752752\\",\\"shipfrom_code\\":\\"HAZ2\\",\\"status_code\\":\\"DL10\\",\\"despatched_qty\\":\\"28.200\\",\\"order_uom\\":[],\\"despatched_uom\\":\\"TNE\\",\\"line_number\\":\\"1\\"}]}],\\"transaction_options\\":{\\"continue_on_fail\\":false,\\"rollback_on_error\\":true}}"
  }
"""

REPEATED_PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/cirrus_message_payloads-repeated.json')
SINGLE_RUN_PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_movement_post_error_payloads.json')


class PayloadOperationsTest(unittest.TestCase):

    def test_get_missing_movement_line_fields_for_payload(self):
        payload = json.loads(JSON_MOVEMENT_POST)
        result = get_missing_movement_line_fields_for_payload(payload)
        self.assertEqual(1, len(result.keys()))
        self.assertTrue(1 in result.keys())
        self.assertEqual(["order_qty", "order_uom"], result[1])

    def test_determine_message_playback_count_from_payloads_multiple(self):
        payloads_list = read_json_data_file(REPEATED_PAYLOAD_FILE)
        result = determine_message_playback_count_from_payloads(payloads_list)
        self.assertEqual(2, result)

    def test_determine_message_playback_count_from_payloads_single(self):
        payloads_list = read_json_data_file(SINGLE_RUN_PAYLOAD_FILE)
        result = determine_message_playback_count_from_payloads(payloads_list)
        self.assertEqual(1, result)


if __name__ == '__main__':
    unittest.main()