import os
import unittest

from main.algorithms.xpath_lookup import lookup_xpath_get_node
from main.algorithms.xsl_parser import XSLParser
from main.config.configuration import ConfigSingleton, get_configuration_dict
from main.http.cirrus_proxy import CirrusProxy

JSON_MOVEMENT_XSL_FILE = os.path.join(os.path.dirname(__file__), '../resources/F4Fv5Movement_JSONMovementPost.xsl')
XSL_FILE = os.path.join(os.path.dirname(__file__), '../../test/resources/ZESADV_F4Fv5Movement.xsl')

class XSLParserTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Load in config
        ConfigSingleton(get_configuration_dict())
        cls.cirrus_proxy = CirrusProxy()

    @classmethod
    def tearDownClass(cls):
        cls.cirrus_proxy = None

    def setUp(self):
        self.sut = XSLParser(XSLParserTest.cirrus_proxy)

    def test_parser_1(self):
        url = "http://mappings.f4f.com/prd/uk0000000036/F4Fv5Movement_JSONMovementPost.xsl"
        result = self.sut.parse(url, ["order_qty", "order_uom"])
        self.assertEquals(2, len(result.keys()))
        self.assertEquals("LineComponent/Product/Quantity[@Type='Ordered']", result["order_qty"])
        self.assertEquals("LineComponent/Product/Quantity[@Type='Ordered']/@UnitOfMeasure", result["order_uom"])

    def test_parser_2(self):
        url = "http://mappings.f4f.com/prd/uk0000000037/ZESADV_F4Fv5Movement.xsl"
        result = self.sut.parse(url, ["Quantity"])
        self.assertEquals(1, len(result.keys()))
        self.assertEquals("E1EDP09/LFIMG", result["Quantity"])

    def test_parser_xpath_from_xsl_1(self):
        with open(XSL_FILE) as f:
            xsl_str = f.read()
            result = self.sut.find_xsl_element(xsl_str, "LineComponent/Product/Quantity[@Type='Ordered']")
            self.assertIsNotNone(result)
            self.assertEquals("Z1EDP00/WMENG", result)

    def test_parser_xpath_from_xsl_2(self):
        with open(XSL_FILE) as f:
            xsl_str = f.read()
            result = self.sut.find_xsl_element(xsl_str, "LineComponent/Product/Quantity[@Type='Ordered']/@UnitOfMeasure")
            self.assertIsNotNone(result)
            self.assertEquals("Z1EDP00/VRKME", result)


if __name__ == '__main__':
    unittest.main()