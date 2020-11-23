from datetime import datetime as dt
import os
import pytz

from dateutil.tz import gettz
from pytz import utc
from dateutil import parser

from main.utils.utils import write_json_to_file, parse_json_from_file, format_datetime_to_zulu, \
    convert_timestamp_to_datetime
from datetime import timezone

TZ_FILE = 'resources/timezones_dict.json'


def generate_tz_dict():
    for zone in pytz.common_timezones:
        try:
            tzdate = pytz.timezone(zone).localize(dt.utcnow(), is_dst=None)
        except pytz.NonExistentTimeError:
            pass
        else:
            tzinfo = gettz(zone)
            if tzinfo:
                yield tzdate.tzname(), zone

def read_tz_from_file(filename):
    tz_data = parse_json_from_file(filename)
    for k, v in tz_data.items():
        yield k, gettz(v)

def gen_tzinfos():
    for zone in pytz.common_timezones:
        try:
            tzdate = pytz.timezone(zone).localize(dt.utcnow(), is_dst=None)
        except pytz.NonExistentTimeError:
            pass
        else:
            tzinfo = gettz(zone)

            if tzinfo:
                yield tzdate.tzname(), tzinfo


if __name__ == '__main__':
    # tz_dict = dict(generate_tz_dict())
    # filename = "timezones_dict.json"
    # write_json_to_file(filename, tz_dict)
    NEW_TZINFOS = dict(read_tz_from_file(TZ_FILE))
    print(NEW_TZINFOS)
    # TZINFOS = dict(gen_tzinfos())
    # print(TZINFOS)
    # write_json_to_file("timezones_dict.json", TZINFOS)
    date_str = "2020-08-11 15:37:44 BST"
    # print(type(TZINFOS['GMT']))
    # print(dir(TZINFOS['GMT']))
    tzdate = parser.parse(date_str, tzinfos=NEW_TZINFOS)
    print(type(tzdate))
    print(tzdate)
    res = tzdate.astimezone(NEW_TZINFOS['UTC'])
    # timestamp = tzdate.replace(tzinfo=timezone.utc).timestamp()

    # res = convert_timestamp_to_datetime(timestamp)
    # res = format_datetime_to_zulu(tzdate)
    # res = tzdate.astimezone(utc)
    print(res)
