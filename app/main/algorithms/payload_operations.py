import json

from main.algorithms.payload_predicates import payload_is_json_post_request
from main.config.constants import PAYLOAD


def get_missing_movement_line_fields_for_payload(payload):
    if payload_is_json_post_request(payload):
        json_payload_str = payload.get(PAYLOAD)
        json_movement = json.loads(json_payload_str)
        line_fields_map = {}
        try:
            for line_number, movement_line in enumerate(json_movement.get("movements")[0].get("movement_lines"), 1):
                line_fields_map[line_number] = []
                for key in movement_line.keys():
                    if movement_line[key] is None or len(movement_line[key]) == 0:
                        line_fields_map[line_number].append(key)
        except IndexError:
            return None
        return line_fields_map
    return None

