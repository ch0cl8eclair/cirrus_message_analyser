import os
import unittest

from main.algorithms.xpath_lookup import get_final_tag_from_xpath, lookup_xpath, lookup_xpath_get_node, get_xpath_text

PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_payload_5.xml')
XSL_FILE = os.path.join(os.path.dirname(__file__), './resources/ZESADV_F4Fv5Movement.xsl')
IDOC_PAYLOAD_FILE = os.path.join(os.path.dirname(__file__), './resources/yara_payload_1.xml')


class XPathTest(unittest.TestCase):
    def test_get_final_tag_from_xpath_simple(self):
        expression = "LineComponent/Product/Quantity"
        self.assertEquals("Quantity", get_final_tag_from_xpath(expression))

    def test_get_final_tag_from_xpath_underscore(self):
        expression = "LineComponent/Product/Quantity_UOM1"
        self.assertEquals("Quantity_UOM1", get_final_tag_from_xpath(expression))

    def test_get_final_tag_from_xpath_with_attr(self):
        expression = "LineComponent/Product/Quantity[@Type='Ordered']"
        self.assertEquals("Quantity", get_final_tag_from_xpath(expression))

    def test_get_final_tag_from_xpath_with_attr_leaf(self):
        expression = "LineComponent/Product/Quantity[@Type='Ordered']/@UnitOfMeasure"
        self.assertEquals("Quantity", get_final_tag_from_xpath(expression))

    def test_lookup_xpath(self):
        with open(PAYLOAD_FILE) as f:
            payload_str = f.read()
        lookup = lookup_xpath(payload_str, "LineComponent/Product/Quantity[@Type='Ordered']")
        self.assertIsNone(lookup)
        lookup = lookup_xpath(payload_str, "LineComponent/Product/Quantity")
        self.assertIsNotNone(lookup)
        self.assertEquals("Quantity", lookup)

    def test_xsl_xpath_lookup(self):
        with open(XSL_FILE) as f:
            xsl_str = f.read()
        lookup = lookup_xpath_get_node(xsl_str, "LineComponent/Product/Quantity")
        self.assertIsNotNone(lookup)
        # print(lookup)

    def test_idoc_xpath_lookup(self):
        with open(IDOC_PAYLOAD_FILE) as f:
            xml_str = f.read()
        lookup = get_xpath_text(xml_str, "Z1EDP00/WMENG")
        self.assertIsNotNone(lookup)
        self.assertEquals(0, len(lookup))

        lookup = get_xpath_text(xml_str, "E1EDK07/VBELN")
        self.assertIsNotNone(lookup)
        self.assertEquals("0692169118", lookup)


if __name__ == '__main__':
    unittest.main()
