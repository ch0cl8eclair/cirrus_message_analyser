import unittest

from main.cli.cli_parser import parse_command_line_statement


class CommandLineParserTest(unittest.TestCase):

    def call_sut_func(self, cli_statement):
        return parse_command_line_statement(cli_statement.split())

    def test_list_messages(self):
        cli_cmd = """cmc.py list messages --rule YARA_MOVEMENTS_BASIC --time 1d"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': '1d', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_as_csv(self):
        cli_cmd = """cmc.py list messages --rule SYNGENTA_1 --time 2d --output csv"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_messages', 'rule': 'SYNGENTA_1', 'time': '2d', 'options': {'output': 'csv', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_as_table(self):
        cli_cmd = """cmc.py list messages --rule YARA_MOVEMENTS_COMPLEX --time 3d --output table"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_COMPLEX', 'time': '3d', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_verbose(self):
        cli_cmd = """cmc.py -v list messages --rule YARA_MOVEMENTS_BASIC --time 1d"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': '1d', 'options': {'output': 'table', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_messages_quiet(self):
        cli_cmd = """cmc.py -q list messages --rule YARA_MOVEMENTS_BASIC --time 1d"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_messages', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': '1d', 'options': {'output': 'table', 'quiet': True, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_payloads(self):
        cli_cmd = """cmc.py list message-payloads --uid 324324-23434-3423423"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_message_payloads', 'uid': '324324-23434-3423423', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_events(self):
        cli_cmd = """cmc.py list message-events --uid 324324-23434-3423423"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_message_events', 'uid': '324324-23434-3423423', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_metadata(self):
        cli_cmd = """cmc.py list message-metadata --uid 324324-23434-3423424"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_message_metadata', 'uid': '324324-23434-3423424', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_message_transforms(self):
        cli_cmd = """cmc.py list message-transforms --uid 324324-23434-3423422"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_message_transforms', 'uid': '324324-23434-3423422', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_analyse_message(self):
        cli_cmd = """cmc.py analyse --uid 324324-23434-3423423"""
        expected = {'cli-type': 'COMMAND', 'function': 'analyse', 'uid': '324324-23434-3423423', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_analyse_messages(self):
        cli_cmd = """cmc.py analyse --rule YARA_MOVEMENTS_BASIC --time yesterday"""
        expected = {'cli-type': 'COMMAND', 'function': 'analyse', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': 'yesterday', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_analyse_messages_with_limit(self):
        cli_cmd = """cmc.py analyse --rule YARA_MOVEMENTS_BASIC --time yesterday --limit 1"""
        expected = {'cli-type': 'COMMAND', 'function': 'analyse', 'rule': 'YARA_MOVEMENTS_BASIC', 'time': 'yesterday', 'limit': 1, 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_detail_message(self):
        cli_cmd = """cmc.py detail --uid 324324-23434-3423423"""
        expected = {'cli-type': 'COMMAND', 'function': 'detail', 'uid': '324324-23434-3423423', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_detail_message_file_output(self):
        cli_cmd = """cmc.py detail --uid 324324-23434-3423423 --output file"""
        expected = {'cli-type': 'COMMAND', 'function': 'detail', 'uid': '324324-23434-3423423', 'options': {'output': 'file', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_list_rules(self):
        cli_cmd = """cmc.py list rules"""
        expected = {'cli-type': 'COMMAND', 'function': 'list_rules', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_clear_cache(self):
        cli_cmd = """cmc.py clear-cache"""
        expected = {'cli-type': 'COMMAND', 'function': 'clear-cache', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_get_logs(self):
        cli_cmd = """cmc.py get-logs --uid 324324-23434-3423423 --start-datetime 2020-08-19T10:05:16.000Z --end-datetime 2020-08-19T10:05:19.000Z"""
        expected = {'cli-type': 'COMMAND', 'function': 'get-logs', 'uid': '324324-23434-3423423', 'start-datetime': '2020-08-19T10:05:16.000Z', 'end-datetime': '2020-08-19T10:05:19.000Z', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_locations_project(self):
        cli_cmd = """cmc.py adm locations --project eu00000001"""
        expected = {'cli-type': 'ADM', 'function': 'locations', 'project': 'eu00000001', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_locations_group(self):
        cli_cmd = """cmc.py adm -v locations --group uk-adapters --output csv"""
        expected = {'cli-type': 'ADM', 'function': 'locations', 'group': 'uk-adapters', 'options': {'output': 'csv', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_configs_project(self):
        cli_cmd = """cmc.py adm configs --project eu00000001"""
        expected = {'cli-type': 'ADM', 'function': 'configs', 'project': 'eu00000001', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_configs_group(self):
        cli_cmd = """cmc.py adm -v configs --group uk-adapters --output csv"""
        expected = {'cli-type': 'ADM', 'function': 'configs', 'group': 'uk-adapters', 'options': {'output': 'csv', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_versions_project(self):
        cli_cmd = """cmc.py adm versions --project eu00000001"""
        expected = {'cli-type': 'ADM', 'function': 'versions', 'project': 'eu00000001', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_versions_group(self):
        cli_cmd = """cmc.py adm -v versions --group uk-adapters --output csv"""
        expected = {'cli-type': 'ADM', 'function': 'versions', 'group': 'uk-adapters', 'options': {'output': 'csv', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_scripts_project(self):
        cli_cmd = """cmc.py adm scripts --project eu00000001"""
        expected = {'cli-type': 'ADM', 'function': 'scripts', 'project': 'eu00000001', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_scripts_group(self):
        cli_cmd = """cmc.py adm -v scripts --group uk-adapters --output csv"""
        expected = {'cli-type': 'ADM', 'function': 'scripts', 'group': 'uk-adapters', 'options': {'output': 'csv', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_artifacts_project(self):
        cli_cmd = """cmc.py adm artifacts --project eu00000001"""
        expected = {'cli-type': 'ADM', 'function': 'artifacts', 'project': 'eu00000001', 'options': {'output': 'table', 'quiet': False, 'verbose': False}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))

    def test_adm_artifacts_group(self):
        cli_cmd = """cmc.py adm -v artifacts --group uk-adapters --output csv"""
        expected = {'cli-type': 'ADM', 'function': 'artifacts', 'group': 'uk-adapters', 'options': {'output': 'csv', 'quiet': False, 'verbose': True}}
        self.assertEqual(expected, self.call_sut_func(cli_cmd))


if __name__ == '__main__':
    unittest.main()
