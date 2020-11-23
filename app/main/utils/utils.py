import datetime
import json
import re
import sys
import os.path
import zipfile
from os import path

from dateutil import parser
from dateutil.tz import gettz
from main.config.constants import *

DURATION_PATTERN = re.compile(r'(\d+)([dh])')
DATETIME_REGEX = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
TZ_FILE = 'resources/timezones_dict.json'


def parse_json_from_file(filename):
    """Reads the given json file and returns back a dict representation"""
    data = read_data_from_file(filename)
    return json.loads(data)


def read_data_from_file(filename):
    """Reads the filecontents and returns it back as a string"""
    file_name = '../../%s' % filename
    # print("Is valid file: %i" % os.path.isfile(file_name))
    config_file = os.path.join(os.path.dirname(__file__), file_name)
    with open(config_file, 'r') as myfile:
        data = myfile.read()
    return data


def write_json_to_file(filepath, json_data, pretty=False):
    with open(filepath, 'w') as outfile:
        if not pretty:
            json.dump(json_data, outfile)
        else:
            json.dump(json_data, outfile, indent=4)
            # , sort_keys=True


def write_text_to_file(filepath, lines_list):
    with open(filepath, 'w') as file_handler:
        for item in lines_list:
            file_handler.write(f"{item}\n")


def write_single_text_to_file(filepath, text, force=False):
    if not path.exists(filepath) or force:
        with open(filepath, 'w', encoding="utf-8") as file_handler:
            file_handler.write(text)


def convert_package_str_to_path_notation(package_dot_name):
    """converts com.adaptris.core to com/adaptris/core"""
    if package_dot_name:
        return package_dot_name.replace(".", "/")
    return None


def error_and_exit(error_msg):
    print(error_msg, file=sys.stderr)
    sys.exit(1)


def get_now_utc_string():
    return datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def validate_duration_string(duration_string):
    # TODO we can remove the is_valid dict entry as it serves no purpose
    if duration_string:
        if duration_string == TODAY:
            return {"is_valid": True, "type": TODAY}
        elif duration_string == YESTERDAY:
            return {"is_valid": True, "type": YESTERDAY}
        else:
            match = DURATION_PATTERN.match(duration_string)
            if match:
                result_map = {"is_valid": True, "type": HOURS if match.group(2) == "h" else DAYS,
                              "value": match.group(1)}
                return result_map
    raise ValueError("Invalid value for duration string given: [{}]".format(duration_string))


def calculate_start_and_end_times_from_duration(duration_string):
    """Given a time duration string ie 1d, 1h etc, generate corresponding start and end times for search"""
    validation_map = validate_duration_string(duration_string)
    if validation_map["is_valid"]:
        # Using latter datetime instead of now to handle yesterday
        latter_datetime = datetime.datetime.utcnow()
        if validation_map["type"] == TODAY:
            earlier_datetime = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        elif validation_map["type"] == YESTERDAY:
            earlier_datetime = latter_datetime + datetime.timedelta(days=-1)
            earlier_datetime = earlier_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
            latter_datetime = latter_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
        elif validation_map["type"] == HOURS:
            hour_value = int(validation_map["value"]) * -1
            earlier_datetime = latter_datetime + datetime.timedelta(hours=hour_value)
        elif validation_map["type"] == DAYS:
            day_value = int(validation_map["value"]) * -1
            earlier_datetime = latter_datetime + datetime.timedelta(days=day_value)
        else:
            raise ValueError("Provided duration value: [{}] is not handled".format(duration_string))
        return {START_DATE: format_datetime_to_zulu(earlier_datetime), END_DATE: format_datetime_to_zulu(latter_datetime)}
    raise ValueError("Provided duration value: [{}] is not handled".format(duration_string))


def validate_start_and_end_times(start_datetime_str, end_datetime_str):
    # Note the key names here are the Cirrus api ones
    result_dict = {START_DATE: format_datetime_to_zulu(parse_datetime_str(start_datetime_str))}
    if end_datetime_str:
        result_dict[END_DATE] = format_datetime_to_zulu(parse_datetime_str(end_datetime_str))
    return result_dict


def parse_datetime_str(datetime_str):
    match = DATETIME_REGEX.match(datetime_str)
    if match:
        matched_datetime_str = match.group()
        return datetime.datetime.strptime(matched_datetime_str, "%Y-%m-%dT%H:%M:%S")
    raise ValueError("Invalid datetime supplied: [{}]".format(datetime_str))


def _read_tz_from_file(filename):
    tz_data = parse_json_from_file(filename)
    for k, v in tz_data.items():
        yield k, gettz(v)


NEW_TZINFOS = dict(_read_tz_from_file(TZ_FILE))


def parse_timezone_datetime_str(datetime_str):
    tzdate = parser.parse(datetime_str, tzinfos=NEW_TZINFOS)
    res = tzdate.astimezone(NEW_TZINFOS['UTC'])
    return res


def format_datetime_to_zulu(provided_datetime):
    return provided_datetime.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def get_datetime_now_as_zulu():
    return format_datetime_to_zulu(datetime.datetime.utcnow())


def convert_timestamp_to_datetime_str(timestamp):
    return format_datetime_to_zulu(convert_timestamp_to_datetime(timestamp))


def convert_timestamp_to_datetime(timestamp):
    return datetime.datetime.utcfromtimestamp(timestamp/1e3)


def clear_quotes(given_str):
    return given_str.replace("'", "").replace('"', '')


def convert_output_option_to_enum(options):
    options.get(OUTPUT)
    requested_output = OutputFormat[options.get(OUTPUT)]
    return requested_output


def get_config_for_website(configuration, url_name):
    sites_cfg = configuration.get(URLS)
    for site in sites_cfg:
        if site["name"] == url_name:
            return site
    return None


def generate_webpack(configuration, message_uid):
    output_folder_str = configuration.get(OUTPUT_FOLDER)
    zip_output_folder_str = configuration.get(ZIP_OUTPUT_FOLDER)
    message_output_folder = os.path.join(output_folder_str, message_uid)
    zip_output_folder = os.path.join(zip_output_folder_str)
    message_uid,  message_output_folder, zip_output_folder
    generated_file = zip_message_files(message_uid,  message_output_folder, zip_output_folder)
    return generated_file


def zip_message_files(message_uid, message_output_folder, zip_output_folder):
    '''
    Zips the message output folder into a single zip to be used by the support team
    :param message_uid: message uid to search for
    :param message_output_folder: the folder were the message search files reside
    :param zip_output_folder: the folder where the zip is to be created
    :return: path to the created zip file
    '''
    target_zip_file = os.path.join(zip_output_folder, f"{message_uid}.zip")
    if not path.exists(target_zip_file):
        with zipfile.ZipFile(target_zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(message_output_folder):
                for file in files:
                    if file.endswith(".log") or file.endswith(".txt"):
                        zipf.write(os.path.join(root, file), file)
    return os.path.abspath(target_zip_file)
