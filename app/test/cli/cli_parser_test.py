import unittest

from cli.cli_parser import parse_command_line_statement


class CommandLineParserTest(unittest.TestCase):

    def call_sut_func(self, cli_statement):
        return parse_command_line_statement(cli_statement.split())

    def test_list_messages(self):
        cli_cmd = """cmc.py list messages --rule YARA_MOVEMENTS_BASIC --time 1d"""
        expected = {'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': '1d', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_as_csv(self):
        cli_cmd = """cmc.py list messages --rule SYNGENTA_1 --time 2d --output csv"""
        expected = {'function': 'list_messages', 'rule': 'SYNGENTA_1', 'time': '2d', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_as_table(self):
        cli_cmd = """cmc.py list messages --rule YARA_MOVEMENTS_COMPLEX --time 3d --output table"""
        expected = {'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_COMPLEX', 'time': '3d', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_verbose(self):
        cli_cmd = """cmc.py -v list messages --rule YARA_MOVEMENTS_BASIC --time 1d"""
        expected = {'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': '1d', 'options': {'output': 'csv', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_quiet(self):
        cli_cmd = """cmc.py -q list messages --rule YARA_MOVEMENTS_BASIC --time 1d"""
        expected = {'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': '1d', 'options': {'output': 'csv', 'quiet': True, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_payloads(self):
        cli_cmd = """cmc.py list message-payloads --uid 324324-23434-3423423"""
        expected = {'function': 'list_message_payloads', 'uid': '324324-23434-3423423', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_events(self):
        cli_cmd = """cmc.py list message-events --uid 324324-23434-3423423"""
        expected = {'function': 'list_message_events', 'uid': '324324-23434-3423423', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_metadata(self):
        cli_cmd = """cmc.py list message-metadata --uid 324324-23434-3423424"""
        expected = {'function': 'list_message_metadata', 'uid': '324324-23434-3423424', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_transforms(self):
        cli_cmd = """cmc.py list message-transforms --uid 324324-23434-3423422"""
        expected = {'function': 'list_message_transforms', 'uid': '324324-23434-3423422', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_analyse_message(self):
        cli_cmd = """cmc.py analyse --uid 324324-23434-3423423"""
        expected = {'function': 'analyse', 'uid': '324324-23434-3423423', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_analyse_messages(self):
        cli_cmd = """cmc.py analyse --rule YARA_MOVEMENTS_BASIC --time yesterday"""
        expected = {'function': 'analyse', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': 'yesterday', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_rules(self):
        cli_cmd = """cmc.py list rules"""
        expected = {'function': 'list_rules', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_clear_cache(self):
        cli_cmd = """cmc.py clear-cache"""
        expected = {'function': 'clear-cache', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))


if __name__ == '__main__':
    unittest.main()
