import unittest
import unittest.mock
from unittest import mock

from main.config.configuration import get_configuration_dict, ConfigSingleton
from main.config.constants import ICE_CREDENTIALS
from main.http.webpage_proxy import ICEProxy, ICE_LOGIN, ICE_SUBMIT


class AbstractWebPageTest(unittest.TestCase):
    pass


# TODO implement this proxy test
class ICEProxyTest(AbstractWebPageTest):
    SAMPLE_DASHBOARD_DATA = [{"Community": "EU", "In Progress Messages": "1", "Failed Event Messages": "1", "Heartbeat Failures": "6", "CALM Alerts": "7"}, {"Community": "US", "In Progress Messages": "22", "Failed Event Messages": "69", "Heartbeat Failures": "0", "CALM Alerts": "11"}, {"Community": "AU", "In Progress Messages": "0", "Failed Event Messages": "0", "Heartbeat Failures": "0", "CALM Alerts": "10"}, {"Community": "ZA", "In Progress Messages": "0", "Failed Event Messages": "0", "Heartbeat Failures": "0", "CALM Alerts": "4"}]

    # @classmethod
    # def setUpClass(cls):
    #     cls.config = ConfigSingleton(get_configuration_dict())
    #     cls.sut = ICEProxy()
    #
    # def test_init(self):
    #     self.assertEqual("ICE", self.sut.config_site_code)
    #     self.assertEqual(ICE_CREDENTIALS, self.sut.credentials_section_name)
    #     self.assertEqual(ICE_LOGIN, self.sut.login_url)
    #     self.assertEqual(ICE_SUBMIT, self.sut.submit_url)
    #     self.assertFalse(self.sut.initialised)
    #
    # def test_initialise(self):
    #     pass
    #
    # @mock.patch('webpage_proxy.get_calm_dashboard_data')
    # def test_get_calm_dashboard_data(self, mocked):
    #     mocked.return_value = self.SAMPLE_DASHBOARD_DATA
    #     self.sut.get_calm_dashboard_data()
    #     self.assertTrue(True)
    #
    # def test_list_messages(self):
    #     self.assertTrue(True)
    #
    # def test_get_failed_messages_data(self):
    #     self.assertTrue(True)
    #
    # def test_get_failure_count_for_region(self):
    #     self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
