import json

from main.algorithms.payload_predicates import payload_is_json_post_request
from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import PAYLOAD
from collections import Counter, defaultdict

from main.utils.utils import convert_timestamp_to_datetime
import logging
from logging.config import fileConfig
fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')


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


def determine_message_playback_count_from_payloads(payloads):
    """From the list of payloads for a message determines how many times a message has been through the system"""
    tracking_points_list = [item.get("tracking-point", "") for item in payloads if "tracking-point" in item]
    counts = Counter(tracking_points_list)
    occurances = Counter([v for k, v in counts.items()])
    repeated_count = occurances.most_common()[0][0]
    logging.info("The message appears to have been processed: {} time(s)".format(repeated_count))
    return repeated_count


def get_final_message_processing_time_window(payloads, message_repeat_count):
    """For a message that has been processed multiple time we get the final timewindow of when it last went through the system"""
    tracking_points_list = [item.get("tracking-point", "") for item in payloads if "tracking-point" in item]
    counts = Counter(tracking_points_list)
    single_tracking_group = {k: (int) (v / message_repeat_count) for k, v in counts.items() if v >= message_repeat_count}

    groups = []
    current_group = []
    parsed_tracking_item_count = defaultdict(int)
    for index, current_payload in enumerate(payloads):
        current_line = current_payload.get("tracking-point")
        if current_line in single_tracking_group.keys():
            max_count = single_tracking_group.get(current_line)
            parsed_tracking_item_count[current_line] = parsed_tracking_item_count[current_line] + 1
            if parsed_tracking_item_count[current_line] > max_count:
                # logger.debug("Encountered new repeat group")
                groups.append(current_group)
                current_group = [current_payload]
                parsed_tracking_item_count = defaultdict(int)
                continue
            pass
        else:
            # logger.warning("Unknown line encountered, appending to current group")
            pass
        current_group.append(current_payload)
    groups.append(current_group)

    initial_date = payloads[0].get("insertDate")
    final_date = payloads[-1].get("insertDate")
    if groups:
        current_group = groups[-1]
        start_date = current_group[0].get("insertDate", initial_date)
        end_date = current_group[-1].get("insertDate", final_date)
        return start_date, end_date
    else:
        return initial_date, final_date
