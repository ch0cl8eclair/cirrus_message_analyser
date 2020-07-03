import logging
from logging.config import fileConfig
from enum import Enum
from lxml import etree
from lxml.etree import Element

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import PAYLOAD, FIELDS, INDEX, DOCUMENT_LINES, HEADER_FIELDS, DOCUMENTS, MESSAGE_ID
import json

from main.model.model_utils import MissingPayloadException

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('parser')


def is_empty(current_field):
    return current_field is None or len(current_field) == 0


def is_empty_node(current_field):
    return current_field is None or is_empty(current_field.text)


def is_empty_data(field):
    if isinstance(field, etree._Element):
        return is_empty_node(field)
    # elif isinstance(field, str):
    #     return is_empty(field)
    # elif field is None:
    #     return True
    elif not field:
        return True
    return False


class DocumentFieldsParser:
    def __init__(self, kwargs):
        self.document_header_root   = kwargs["document_header_root"] if "document_header_root" in kwargs else None
        self.document_lines_root    = kwargs["document_lines_root"] if "document_lines_root" in kwargs else None
        self.header_include_fields  = kwargs["header_include_fields"] if "header_include_fields" in kwargs else None
        self.header_exclude_fields  = kwargs["header_exclude_fields"] if "header_exclude_fields" in kwargs else None
        self.line_include_fields = kwargs["line_include_fields"] if "line_include_fields" in kwargs else None
        self.line_exclude_fields = kwargs["line_exclude_fields"] if "line_exclude_fields" in kwargs else None
        self.type = EmptyFieldParseType.from_str(kwargs["type"]) if "type" in kwargs else EmptyFieldParseType.all

    def parse(self, payload_obj):
        logger.debug("Parsing document for type: {}".format(self.type))
        if payload_obj:
            payload_str = payload_obj.get(PAYLOAD)
            try:
                json_payload = json.loads(payload_str)
                return self._parse_json_document(json_payload)
            except ValueError as error:
                return self._parse_xml_document(payload_str)
        else:
            raise MissingPayloadException()

    def _field_predicate(self, field_value):
        """Have the subclass override this to perform the required field test"""
        return True

    # ################################################
    # JSON functions
    # ################################################

    def _parse_json_document(self, payload_json):
        document_results_map = {}
        documents_list = []
        document_results_map[DOCUMENTS] = documents_list

        if payload_json and self.document_header_root and self.document_header_root in payload_json:
            document_root = payload_json.get(self.document_header_root)
            if isinstance(document_root, list):
                for document_index, document in enumerate(document_root, 1):
                    documents_list.append(self._parse_single_json_document(document, document_index))
            else:
                documents_list.append(self._parse_single_json_document(document_root, 1))
        else:
            logger.error("Failed to find document header root to parse from payload: {}".format(self.document_header_root))
        return document_results_map

    def _parse_single_json_document(self, document, document_index=1):
        result_document_object = {INDEX: document_index}
        # Parse document header fields
        empty_header_field_names = self._get_empty_json_header_fields(document)
        result_document_object[HEADER_FIELDS] = empty_header_field_names
        # Now parse document lines
        if self.document_lines_root and self._parse_lines() and self.document_lines_root in document.keys():
            lines_result_map = self._parse_json_document_lines(document[self.document_lines_root])
            result_document_object[DOCUMENT_LINES] = lines_result_map
        return result_document_object

    def _get_empty_json_header_fields(self, document):
        """pulls out all the empty (or whatever test) fields and ensure that the document lines field name is not present"""
        empty_header_field_names = []
        if self._parse_header():
            empty_header_field_names = [key for key in document.keys() if self._filter_header_fields(key) and self._field_predicate(document[key])]
            if self.document_lines_root and self.document_lines_root in empty_header_field_names:
                empty_header_field_names.remove(self.document_lines_root)
        return empty_header_field_names

    def _parse_json_document_lines(self, document_lines):
        result_line_list = []
        for line_index, line in enumerate(document_lines, 1):
            line_object = {}
            empty_line_field_names = []
            for current_line_key in [key for key in line.keys() if self._filter_line_fields(key)]:
                if self._field_predicate(line[current_line_key]):
                    empty_line_field_names.append(current_line_key)
            line_object[INDEX] = line_index
            line_object[FIELDS] = empty_line_field_names
            result_line_list.append(line_object)
        return result_line_list

    # ################################################
    # XML functions
    # ################################################
    def _parse_xml_document(self, payload_str):
        xml = bytes(bytearray(payload_str, encoding='utf-8'))
        tree = etree.XML(xml)
        document_results_map = {}
        documents_list = []
        document_results_map[DOCUMENTS] = documents_list

        if tree is not None and self.document_header_root:
            doc_root_node = tree.find(self.document_header_root)
            if doc_root_node is not None and doc_root_node.tag == "movements" and "class" in doc_root_node.attrib:
                if doc_root_node.attrib["class"] == "array":
                    for document_index, array_element in enumerate(doc_root_node, 1):
                        documents_list.append(self._parse_single_xml_document(array_element, document_index))
                elif doc_root_node.attrib["class"] == "object":
                    documents_list.append(self._parse_single_xml_document(doc_root_node, 1))
        else:
            logger.error("Failed to find document header root to parse from payload: {}".format(self.document_header_root))
        return document_results_map

    def _parse_single_xml_document(self, document_node, document_index=1):
        result_document_object = {INDEX: document_index}
        empty_header_field_names = []
        for child_node in document_node:
            if not self._filter_header_fields(child_node.tag):
                continue
            if self._parse_header() and self._field_predicate(child_node):
                empty_header_field_names.append(child_node.tag)
            if self.document_lines_root and self.document_lines_root == child_node.tag and self._parse_lines():
                lines_result_map = self._parse_xml_document_lines(child_node)
                result_document_object[DOCUMENT_LINES] = lines_result_map
        result_document_object[HEADER_FIELDS] = empty_header_field_names
        return result_document_object

    def _parse_xml_document_lines(self, document_lines_node):
        result_line_list = []
        for line_index, line_element in enumerate(document_lines_node, 1):
            line_object = {}
            empty_line_field_names = []
            for line_field in line_element:
                if not self._filter_line_fields(line_field.tag):
                    continue
                if self._field_predicate(line_field):
                    empty_line_field_names.append(line_field.tag)
            line_object[INDEX] = line_index
            line_object[FIELDS] = empty_line_field_names
            result_line_list.append(line_object)
        return result_line_list

    # ################################################
    # Misc functions
    # ################################################

    def _parse_header(self):
        result = self.type in (EmptyFieldParseType.header, EmptyFieldParseType.all)
        return result

    def _parse_lines(self):
        result = self.type in (EmptyFieldParseType.lines, EmptyFieldParseType.all)
        return result

    def _filter_header_fields(self, current_field):
        return self._filter_field(current_field, self.header_include_fields, self.header_exclude_fields)

    def _filter_line_fields(self, current_field):
        return self._filter_field(current_field, self.line_include_fields, self.line_exclude_fields)

    @staticmethod
    def _filter_field(current_field, include_list, exclude_list):
        if include_list and current_field not in include_list:
            return False
        if exclude_list and current_field in exclude_list:
            return False
        return True

    @staticmethod
    def format_as_csv(json_result):
        if json_result:
            return FlattenJsonOutputToCSV.convert(json_result)
        return None


class DocumentEmptyFieldsParser(DocumentFieldsParser):
    def __init__(self, kwargs):
        super().__init__(kwargs)

    def _field_predicate(self, field):
        return is_empty_data(field)


class DocumentMandatoryFieldsParser(DocumentFieldsParser):
    def __init__(self, kwargs):
        super().__init__(kwargs)
        self.document_header_mandatory_fields = kwargs["document_header_mandatory_fields"] if "document_header_mandatory_fields" in kwargs else None
        self.document_lines_mandatory_fields  = kwargs["document_lines_mandatory_fields"] if "document_lines_mandatory_fields" in kwargs else None

    def _field_predicate(self, field):
        return is_empty_data(field)

    def _parse_single_json_document(self, document, document_index=1):
        result_document_object = {INDEX: document_index}
        missing_mandatory_header_field_names = []
        if self._parse_header():
            filtered_header_fields = [key for key in document.keys() if self._filter_header_fields(key)]
            missing_mandatory_header_field_names = self.__get_missing_mandatory_fields(self.document_header_mandatory_fields, filtered_header_fields, document)
        result_document_object[HEADER_FIELDS] = missing_mandatory_header_field_names
        if self.document_lines_root and self._parse_lines() and self.document_lines_root in document.keys():
            lines_result_map = self._parse_json_document_lines(document[self.document_lines_root])
            result_document_object[DOCUMENT_LINES] = lines_result_map
        return result_document_object

    def _parse_json_document_lines(self, document_lines):
        result_line_list = []
        for line_index, line in enumerate(document_lines, 1):
            line_object = {}
            filtered_line_fields = [key for key in line.keys() if self._filter_line_fields(key)]
            missing_mandatory_line_field_names = self.__get_missing_mandatory_fields(self.document_lines_mandatory_fields, filtered_line_fields, line)
            if missing_mandatory_line_field_names:
                line_object[INDEX] = line_index
                line_object[FIELDS] = missing_mandatory_line_field_names
                result_line_list.append(line_object)
        return result_line_list

    def _parse_single_xml_document(self, document_node, document_index=1):
        result_document_object = {INDEX: document_index}
        missing_mandatory_header_field_names = []
        document_fields = [header_field.tag for header_field in document_node]
        if self._parse_header():
            filtered_header_fields = [header_field for header_field in document_fields if self._filter_header_fields(header_field)]
            missing_mandatory_header_field_names = self.__get_missing_mandatory_fields_for_xml(self.document_header_mandatory_fields, filtered_header_fields, document_node)
        result_document_object[HEADER_FIELDS] = missing_mandatory_header_field_names
        if self.document_lines_root and self._parse_lines() and self.document_lines_root in document_fields:
            lines_node = document_node.find(self.document_lines_root)
            lines_result_map = self._parse_xml_document_lines(lines_node)
            result_document_object[DOCUMENT_LINES] = lines_result_map
        return result_document_object

    def _parse_xml_document_lines(self, document_lines_node):
        result_line_list = []
        for line_index, line_element in enumerate(document_lines_node, 1):
            line_object = {}
            filtered_line_fields = [line_field.tag for line_field in line_element if self._filter_line_fields(line_field.tag)]
            missing_mandatory_line_field_names = self.__get_missing_mandatory_fields_for_xml(self.document_lines_mandatory_fields, filtered_line_fields, line_element)
            if missing_mandatory_line_field_names:
                line_object[INDEX] = line_index
                line_object[FIELDS] = missing_mandatory_line_field_names
                result_line_list.append(line_object)
        return result_line_list

    def __get_missing_mandatory_fields(self, mandatory_fields_list, filtered_document_fields_list, document):
        missing_mandatory_field_names = []
        if mandatory_fields_list:
            for mandatory_field in mandatory_fields_list:
                if not mandatory_field in filtered_document_fields_list:
                    missing_mandatory_field_names.append(mandatory_field)
                elif self._field_predicate(document[mandatory_field]):
                    missing_mandatory_field_names.append(mandatory_field)
        return missing_mandatory_field_names

    def __get_missing_mandatory_fields_for_xml(self, mandatory_fields_list, filtered_document_fields_list, document_line_node):
        missing_mandatory_field_names = []
        if mandatory_fields_list:
            for mandatory_field in mandatory_fields_list:
                line_field = document_line_node.find(mandatory_field)
                if not mandatory_field in filtered_document_fields_list:
                    missing_mandatory_field_names.append(mandatory_field)
                elif self._field_predicate(line_field.text):
                    missing_mandatory_field_names.append(mandatory_field)
        return missing_mandatory_field_names


class EmptyFieldParseType(Enum):
    header = 0
    lines = 1
    all = 2

    @staticmethod
    def from_str(label):
        clean_key = label.lower()
        if clean_key == 'header':
            return EmptyFieldParseType.header
        elif clean_key == 'lines':
            return EmptyFieldParseType.lines
        else:
            return EmptyFieldParseType.all


class FlattenJsonOutputToCSV:
    """Convert the generated JSON structure into a 2d array"""
    EMPTY_HEADINGS = [MESSAGE_ID, "document_index", "empty_header_fields", "line_index", "empty_line_fields"]
    MANDATORY_HEADINGS = [MESSAGE_ID, "document_index", "mandatory_header_fields", "line_index", "mandatory_line_fields"]

    @staticmethod
    def convert(json_output):
        output_lines = []
        if json_output and DOCUMENTS in json_output:
            for document in json_output[DOCUMENTS]:
                # add the header line to the output
                fields_str = ', '.join(document[HEADER_FIELDS]) if document[HEADER_FIELDS] else ""
                output_lines.append([document[INDEX], fields_str, None, None])
                # now add any document lines
                if DOCUMENT_LINES in document and len(document[DOCUMENT_LINES]):
                    for line in document[DOCUMENT_LINES]:
                        line_fields_str = ', '.join(line[FIELDS]) if line[FIELDS] else ""
                        output_lines.append([document[INDEX], None, line[INDEX], line_fields_str])
            return output_lines
        return None

    @staticmethod
    def to_set(json_output):
        output_fields_set = set()
        if json_output and DOCUMENTS in json_output:
            for document in json_output[DOCUMENTS]:
                # add the header line to the output
                if document[HEADER_FIELDS]:
                    output_fields_set.update(document[HEADER_FIELDS])
                # now add any document lines
                if DOCUMENT_LINES in document and len(document[DOCUMENT_LINES]):
                    for line in document[DOCUMENT_LINES]:
                        if line[FIELDS]:
                            output_fields_set.update(line[FIELDS])
        return output_fields_set