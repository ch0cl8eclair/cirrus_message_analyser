import unittest
import datetime

from main.config.constants import YESTERDAY, TODAY, DAYS, HOURS
from main.utils.utils import validate_duration_string, calculate_start_and_end_times_from_duration, parse_datetime_str, \
    convert_timestamp_to_datetime_str


class UtilsDateTimeTest(unittest.TestCase):
    def test_calculate_start_and_end_times_from_duration_1d(self):
        cli_cmd = "1d"
        result = calculate_start_and_end_times_from_duration(cli_cmd)
        now = datetime.datetime.utcnow()
        yesterday = now + datetime.timedelta(days=-1)

        # Date comparison
        self.__compare_datetime_with_delta(yesterday, result["start-date"])
        self.__compare_datetime_with_delta(now, result["end-date"])

    def test_calculate_start_and_end_times_from_duration_1h(self):
        cli_cmd = "1h"
        result = calculate_start_and_end_times_from_duration(cli_cmd)
        now = datetime.datetime.utcnow()
        hour_ago = now + datetime.timedelta(hours=-1)

        # Date comparison
        self.__compare_datetime_with_delta(hour_ago, result["start-date"])
        self.__compare_datetime_with_delta(now, result["end-date"])

    def test_calculate_start_and_end_times_from_duration_today(self):
        cli_cmd = "today"
        result = calculate_start_and_end_times_from_duration(cli_cmd)
        now = datetime.datetime.utcnow()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Date comparison
        self.__compare_datetime_with_delta(midnight, result["start-date"])
        self.__compare_datetime_with_delta(now, result["end-date"])
        # String comparison because we can
        self.assertEquals(midnight.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z', result["start-date"])

    def test_calculate_start_and_end_times_from_duration_yesterday(self):
        cli_cmd = "yesterday"
        result = calculate_start_and_end_times_from_duration(cli_cmd)
        now = datetime.datetime.utcnow()
        midnight_yesterday = now + datetime.timedelta(days=-1)
        midnight_yesterday = midnight_yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        midnight_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # Date comparison
        self.__compare_datetime_with_delta(midnight_yesterday, result["start-date"])
        self.__compare_datetime_with_delta(midnight_today, result["end-date"])
        # String comparison
        self.assertEquals(midnight_yesterday.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z', result["start-date"])
        self.assertEquals(midnight_today.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z', result["end-date"])

    def test_validate_duration_string_errors(self):
        with self.assertRaises(Exception) as context:
            validate_duration_string(None)
        self.assertTrue('Invalid value for duration string given: [None]' in str(context.exception))

        with self.assertRaises(Exception) as context:
            validate_duration_string("")
        self.assertTrue('Invalid value for duration string given: []' in str(context.exception))

        with self.assertRaises(Exception) as context:
            validate_duration_string("week")
        self.assertTrue('Invalid value for duration string given: [week]' in str(context.exception))

        with self.assertRaises(Exception) as context:
            validate_duration_string("2m")
        self.assertTrue('Invalid value for duration string given: [2m]' in str(context.exception))

        with self.assertRaises(Exception) as context:
            self.assertEqual({"is_valid": True, "type": DAYS, "value": "3"}, validate_duration_string("3D"))
        self.assertTrue('Invalid value for duration string given: [3D]' in str(context.exception))

        with self.assertRaises(Exception) as context:
            self.assertEqual({"is_valid": True, "type": HOURS, "value": "4"}, validate_duration_string("4H"))
        self.assertTrue('Invalid value for duration string given: [4H]' in str(context.exception))

    def test_validate_duration_string_valid(self):
        self.assertEqual({"is_valid": True, "type": YESTERDAY}, validate_duration_string(YESTERDAY))
        self.assertEqual({"is_valid": True, "type": TODAY}, validate_duration_string(TODAY))
        self.assertEqual({"is_valid": True, "type": DAYS, "value": "1"}, validate_duration_string("1d"))
        self.assertEqual({"is_valid": True, "type": HOURS, "value": "1"}, validate_duration_string("1h"))
        self.assertEqual({"is_valid": True, "type": DAYS, "value": "10"}, validate_duration_string("10d"))

    def test_parse_datetime_str_full_format(self):
        actual_date_time = parse_datetime_str("2020-05-17T10:30:08.877Z")
        expected = datetime.datetime(2020, 5, 17)
        expected = expected.replace(hour=10, minute=30, second=8, microsecond=877)
        print(datetime.timedelta(seconds=1))
        self.assertAlmostEqual(expected, actual_date_time, delta=datetime.timedelta(seconds=1))

    def test_parse_datetime_str_missing_microseconds(self):
        actual_date_time = parse_datetime_str("2020-05-17T10:30:08")
        expected = datetime.datetime(2020, 5, 17)
        expected = expected.replace(hour=10, minute=30, second=8, microsecond=0)
        self.assertAlmostEqual(expected, actual_date_time, delta=datetime.timedelta(seconds=1))

    def test_parse_datetime_str_missing_microseconds_with_zulu(self):
        actual_date_time = parse_datetime_str("2020-05-17T10:30:08Z")
        expected = datetime.datetime(2020, 5, 17)
        expected = expected.replace(hour=10, minute=30, second=8, microsecond=0)
        self.assertAlmostEqual(expected, actual_date_time, delta=datetime.timedelta(seconds=1))

    def __compare_datetime_with_delta(self, expected_date, actual_string_datetime_str):
        actual_datetime = datetime.datetime.strptime(actual_string_datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        self.assertAlmostEqual(expected_date, actual_datetime, delta=datetime.timedelta(seconds=1))

    def test_convert_timestamp_to_datetime_str(self):
        timestamp = 1591270622000
        actual = convert_timestamp_to_datetime_str(timestamp)
        self.assertEquals("2020-06-04T11:37:02.000Z", actual)


if __name__ == '__main__':
    unittest.main()
