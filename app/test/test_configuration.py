import unittest

import json

from main.config.configuration import get_configuration_dict, ConfigSingleton
from main.utils.utils import get_configuration_for_app, CIRRUS_CFG, CONFIG, get_config_endpoint, NAME, ENDPOINTS, \
    MISC_CFG, ICE_CFG, get_merged_app_cfg, REGION, ENV, OPTIONS
from main.config.constants import CREDENTIALS, APPLICATIONS, RULES, CIRRUS


class TestConfiguration(unittest.TestCase):
    def setUp(self):
        self.config = ConfigSingleton(get_configuration_dict())

    def test_applications(self):
        self.assertTrue(self.config.has_key(APPLICATIONS))
        self.assertTrue(self.config.has_key(CREDENTIALS))
        self.assertTrue(self.config.has_key(RULES))

        x = self.config
        self.assertEqual(6, len(self.config.get(APPLICATIONS)))
        self.assertEqual(5, len(self.config.get(CREDENTIALS).get(APPLICATIONS)))

    def test_get_configuration_for_app(self):
        result = get_configuration_for_app(self.config, CIRRUS_CFG)
        self.assertEqual(1, len(result.keys()))
        self.assertTrue(CIRRUS_CFG in result)
        cirrus_cfg = result.get(CIRRUS_CFG)
        self.assertTrue(CONFIG in cirrus_cfg)
        self.assertEqual(1, len(cirrus_cfg.get(CONFIG)))

        config_keys = cirrus_cfg.get(CONFIG)[0].keys()
        self.assertTrue("name" in config_keys)
        self.assertTrue("region" in config_keys)
        self.assertTrue("base_url" in config_keys)

        self.assertTrue(CREDENTIALS in cirrus_cfg)
        self.assertEqual(1, len(cirrus_cfg.get(CREDENTIALS)))

        credential_keys = cirrus_cfg.get(CREDENTIALS)[0].keys()
        self.assertTrue("name" in credential_keys)
        self.assertTrue("region" in credential_keys)
        self.assertTrue("username" in credential_keys)
        self.assertTrue("password" in credential_keys)
        print(json.dumps(result))

    def test_get_configuration_for_app2(self):
        result = get_configuration_for_app(self.config, MISC_CFG, "*", "*")
        self.assertEqual(1, len(result.keys()))
        misc_cfg = result.get(MISC_CFG)
        self.assertTrue(CONFIG in misc_cfg)
        config_keys = misc_cfg.get(CONFIG)[0].keys()
        self.assertTrue("name" in config_keys)
        self.assertTrue("region" in config_keys)
        self.assertTrue("chrome-driver-folder" in config_keys)
        print(json.dumps(result))

    def test_get_config_endpoint(self):
        result = get_config_endpoint(self.config, CIRRUS_CFG, "SEARCH_MESSAGES")
        self.assertTrue(isinstance(result, dict))
        self.assertEqual("CIRRUS", result.get(NAME))
        self.assertEqual(1, len(result.get(ENDPOINTS)))
        endpoint_keys = result.get(ENDPOINTS)[0].keys()
        self.assertTrue("name" in endpoint_keys)
        self.assertTrue("type" in endpoint_keys)
        self.assertTrue("url" in endpoint_keys)
        self.assertTrue("data_dict" in endpoint_keys)
        print(json.dumps(result))

    def test_test_get_configuration_for_ice(self):
        result = get_configuration_for_app(self.config, ICE_CFG)
        self.assertEqual(1, len(result.keys()))
        self.assertTrue(ICE_CFG in result)
        ice_cfg = result.get(ICE_CFG)
        self.assertTrue(CONFIG in ice_cfg)
        self.assertEqual(1, len(ice_cfg.get(CONFIG)))

        config_keys = ice_cfg.get(CONFIG)[0].keys()
        self.assertTrue("name" in config_keys)
        self.assertTrue("region" in config_keys)
        self.assertTrue("base_url" in config_keys)

        self.assertTrue(CREDENTIALS in ice_cfg)
        self.assertEqual(1, len(ice_cfg.get(CREDENTIALS)))

        credential_keys = ice_cfg.get(CREDENTIALS)[0].keys()
        self.assertTrue("name" in credential_keys)
        self.assertTrue("region" in credential_keys)
        self.assertTrue("username" in credential_keys)
        self.assertTrue("password" in credential_keys)
        print(json.dumps(result))

    def test_get_merged_app_cfg(self):
        options = {ENV: "OAT", REGION: "US"}
        result = get_merged_app_cfg(self.config, CIRRUS_CFG, options)
        self.assertEqual(1, len(result.keys()))
        self.assertTrue(CIRRUS_CFG in result)
        cirrus_cfg = result.get(CIRRUS_CFG)
        self.assertIsNotNone(cirrus_cfg.get(CONFIG))
        self.assertIsNotNone(cirrus_cfg.get(CREDENTIALS))
        options_cfg = cirrus_cfg.get(OPTIONS)
        self.assertEqual("OAT", options_cfg.get(ENV))
        self.assertEqual("US", options_cfg.get(REGION))
