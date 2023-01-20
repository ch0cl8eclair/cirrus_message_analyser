import datetime
import json
import time
import re
import sys
import os.path
import zipfile
from os import path
import yaml

from dateutil import parser
from dateutil.tz import gettz
from main.config.constants import *
from main.config.constants import APPLICATIONS, WILDCARD, CREDENTIALS, CACHE_REF, CACHED_COOKIE, MIN_30


DURATION_PATTERN = re.compile(r'(\d+)([dh])')
DATETIME_REGEX = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}')
TZ_FILE = 'resources/timezones_dict.json'


def parse_yaml_from_file(filename):
    """Reads the given yaml file and returns back a dict representation"""
    data = read_data_from_file(filename)
    try:
        return yaml.safe_load(data)
    except yaml.YAMLError as exc:
        error_and_exit("Failed to parse yaml config file {}".format(filename))


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


def parse_datetime_from_zulu(zulu_str) -> datetime:
    try:
        return datetime.datetime.strptime(zulu_str, "%Y-%m-%dT%H:%M:%S.%f%z")
    except ValueError:
        # Perhaps the datetime has a whole number of seconds with no decimal
        # point. In that case, this will work:
        return datetime.datetime.strptime(zulu_str, "%Y-%m-%dT%H:%M:%S%z")


def convert_datetime_to_unix(my_datetime):
    return int(time.mktime(my_datetime.timetuple()))


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
    app_cfg = get_configuration_for_app(configuration, MISC_CFG, "*", "*")
    output_folder_str = unpack_config(app_cfg, MISC_CFG, CONFIG, OUTPUT_FOLDER)
    zip_output_folder_str = unpack_config(app_cfg, MISC_CFG, CONFIG, ZIP_OUTPUT_FOLDER)
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


def get_configuration_for_app(configuration, app, env="PRD", region="EU"):
    # print(f"get_configuration_for_app for app: {app}, env: {env} & region: {region}")
    app_config = configuration.get(APPLICATIONS)
    filtered_apps = [x for x in app_config if x.get(NAME) == app]
    results = {}
    for single_app in filtered_apps:
        env_config_list = [ e for e in single_app.get(ENV) if e.get(NAME) in [env, WILDCARD] ]
        # obtain all regions
        configured_regions = [ x.get(REGION) for x in env_config_list ]
        # if we have a matching region then return it
        if region in configured_regions:
            results[single_app.get(NAME)] = { CONFIG: list(filter(lambda x: x.get(REGION) == region, env_config_list)) }
        # else return generic
        elif WILDCARD in configured_regions:
            results[single_app.get(NAME)] = { CONFIG: list(filter(lambda x: x.get(REGION) == WILDCARD, env_config_list)) }
        else:
            error_and_exit(f"Failed to find configuration for app: {app}, env: {env} and region: {region}")

    credentials_config = configuration.get(CREDENTIALS)
    filtered_credentials = [x for x in credentials_config.get(APPLICATIONS) if x.get(NAME) == app]
    for single_cred in filtered_credentials:
        configured_credentials = [e for e in single_cred.get(ENV) if e.get(NAME) in [env, WILDCARD]]
        configured_regions = [ x.get(REGION) for x in configured_credentials ]
        if region in configured_regions:
            results[single_cred.get(NAME)][CREDENTIALS] = list(filter(lambda x: x.get(REGION) == region, configured_credentials))
        elif WILDCARD in configured_regions:
            results[single_cred.get(NAME)][CREDENTIALS] = list(filter(lambda x: x.get(REGION) == WILDCARD, configured_credentials))
        else:
            error_and_exit(f"Failed to find credentials for app: {app}, env: {env} and region: {region}")

    # print(json.dumps(results))
    return results


def get_config_endpoint(configuration, app, endpoint_name):
    app_config = configuration.get(APPLICATIONS)
    filtered_apps = [x for x in app_config if x.get(NAME) == app]
    filtered_endpoints = [endpoint for endpoint in filtered_apps[0].get(ENDPOINTS) if endpoint.get(NAME) == endpoint_name]
    results = {NAME: app, ENDPOINTS: filtered_endpoints}
    return results


def unpack_endpoint_cfg(cfg):
    return cfg.get(ENDPOINTS)[0]


def unpack_config(app_cfg, app_name, cfg_type, cfg_key):
    cfg_subtype_result = app_cfg.get(app_name).get(cfg_type)
    if isinstance(cfg_subtype_result, list):
        # iterate through cfgs to get flag, starting with specific cfg & going to generic cfg
        for cfg in cfg_subtype_result:
            flag_res = cfg.get(cfg_key)
            if flag_res is not None:
                return flag_res
        return None
    elif isinstance(cfg_subtype_result, dict):
        return cfg_subtype_result.get(cfg_key)


def form_system_url(app_cfg, target_endpoint):
    # use basic str concat as we have placeholders
    if target_endpoint:
        url = app_cfg[0].get(BASE_URL) + "/" + target_endpoint.get(URL)
        return url.replace('///', '/')
    return app_cfg[0].get(BASE_URL)


def get_endpoint_url(configuration, merged_app_cfg, app_name, target_endpoint):
    submit_endpoint_cfg = get_config_endpoint(configuration, app_name, target_endpoint)
    submit_url = form_system_url(merged_app_cfg.get(app_name).get(CONFIG), unpack_endpoint_cfg(submit_endpoint_cfg))
    return submit_url


def get_merged_app_cfg(configuration, app_name, options):
    '''Main util method to get the required configuration'''
    app_cfg = get_configuration_for_app(configuration, app_name, options.get(ENV), options.get(REGION))
    app_cfg[app_name][OPTIONS] = {ENV: options.get(ENV), REGION: options.get(REGION)}
    return app_cfg


def switch_app_cfg(configuration, merged_app_cfg, app_name):
    current_app_name = merged_app_cfg.keys()[0]
    options = merged_app_cfg[current_app_name][OPTIONS]
    return get_merged_app_cfg(configuration, app_name, options)


def update_session_with_cookie(configuration, session, app_name, env, region):
    cookie = read_cookies_file(configuration, app_name, env, region)
    if cookie:
        session.cookies.update(cookie)


def read_cookies_file(config, system_name, environment, region):
    print(f"read_cookies_file with app: {system_name}, env: {environment}, region: {region}")
    cookie_key = generate_cookie_key(system_name, environment, region)
    cache = config.get(CACHE_REF)
    if cache and cookie_key in cache:
        print(f"Returning cookie for app: {system_name}, env: {environment}, region: {region} as: {cache[cookie_key]}")
        return cache[cookie_key]
    else:
        print("No cookies found in cache!!", file=sys.stderr)
    return ''


def cookies_file_exists(config, system_name, environment, region):
    cookie_key = generate_cookie_key(system_name, environment, region)
    # TODO investigate this
    if config.get(CACHE_REF):
        return cookie_key in config.get(CACHE_REF)
    return False


def write_cookies_to_file_cache(config, system_name, environment, region, cookies_str):
    cache = config.get(CACHE_REF)
    # if cache:
    cookie_key = generate_cookie_key(system_name, environment, region)
    cache.set(cookie_key, cookies_str, expire=MIN_30)
    # else:
    #     print("Failed to set cookies for site!", file=sys.stderr)


def generate_cookie_key(system_name, environment, region):
    return f"{CACHED_COOKIE}-{system_name}-{environment}-{region}"


def chromedriver_file_exists(folder):
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file == "chromedriver" or file == "chromedriver.exe":
                return True
    return False


def parser_datetime_by_system(given_system, given_datetime_str):
    if given_system == ICE.upper():
        ice_given_datetime = parse_timezone_datetime_str(given_datetime_str)
        return format_datetime_to_zulu(ice_given_datetime)
    else:
        return given_datetime_str
