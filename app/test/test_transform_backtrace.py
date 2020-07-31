import os
import unittest


class TransformStagesAnalyser(unittest.TestCase):

    def get_position(self, original_payload_position, transform_stage_payload_indexes):
        insert_position = 0
        while insert_position < len(transform_stage_payload_indexes):
            if original_payload_position > transform_stage_payload_indexes[insert_position]:
                pass
            else:
                break
            insert_position = insert_position + 1
        return insert_position

    def get_previous_stage_results_by_index(self, index):
        current_keys = list(self.results_map.keys())
        current_keys.sort()
        current_pos = 0
        last_value = current_keys[0]
        while current_pos < len(current_keys):
            if current_keys[current_pos] < index:
                pass
            elif index >= current_keys[current_pos]:
                return None if current_pos == 0 else last_value
            last_value = current_keys[current_pos]
            current_pos = current_pos + 1
        return last_value

    def test_function_max(self):
        original_payload_position = 9
        transform_stage_payload_indexes = [0, 2, 3, 4, 7]
        insert_position = self.get_position(original_payload_position, transform_stage_payload_indexes)
        self.assertEqual(5, insert_position)

    def test_function_min(self):
        original_payload_position = 0
        transform_stage_payload_indexes = [1, 2, 3, 4, 7]
        insert_position = self.get_position(original_payload_position, transform_stage_payload_indexes)
        self.assertEqual(0, insert_position)

    def test_function_med(self):
        original_payload_position = 3
        transform_stage_payload_indexes = [1, 2,  4, 7, 9]
        insert_position = self.get_position(original_payload_position, transform_stage_payload_indexes)
        self.assertEqual(2, insert_position)

    def test_get_previous_stage_results_by_index_1(self):
        self.results_map = {0: "a", 2: "b", 4: "c", 5: "d", 7: "e"}
        result = self.get_previous_stage_results_by_index(4)
        self.assertEqual(2, result)
        result = self.get_previous_stage_results_by_index(7)
        self.assertEqual(5, result)
        result = self.get_previous_stage_results_by_index(2)
        self.assertEqual(0, result)
        result = self.get_previous_stage_results_by_index(0)
        self.assertIsNone(result)

    def test_get_previous_stage_results_by_index_2(self):
        self.results_map = {0: "a", 2: "b"}
        result = self.get_previous_stage_results_by_index(3)
        self.assertEqual(2, result)

    def test_get_previous_stage_results_by_index_3(self):
        self.results_map = {0: "a"}
        result = self.get_previous_stage_results_by_index(2)
        self.assertEqual(0, result)


if __name__ == '__main__':
    unittest.main()