from collections.abc import Set

from main.algorithms.empty_fields import DocumentEmptyFieldsParser, DocumentMandatoryFieldsParser
from main.algorithms.transform_stages import TransformStagesAnalyser, get_payload_object, MissingPayloadException, \
    ConfigurableTransformStagesAnalyser
from main.config.constants import DataRequisites, PAYLOAD_TRACKING_POINT, VERBOSE, QUIET
from main.model.model_utils import process_message_payloads


class AbstractAlgorithm:
    def get_data_prerequistites(self):
        """Return a Set of message data prerequisites to perform the analysis, ie must have events and status"""
        pass

    def set_parameters(self, parameters_dict, format_options=None):
        """Optional functionality to set algorithm parameters to customise analysis"""
        pass

    def set_data_enricher(self, data_enricher):
        """Given the data enricher we can obtain the msg_model and cirrus_proxy"""
        pass

    def analyse(self):
        """method to initiate the analysis of the algorithm instance, should return a bool status success"""
        pass

    def has_analysis_data(self):
        """Indicates if the analysis produces any data or report"""
        return False

    def get_analysis_data(self):
        """Returns the algorithm generated data for output"""
        return None


class TransformBacktraceFields(AbstractAlgorithm):
    def get_data_prerequistites(self):
        return frozenset([DataRequisites.payloads, DataRequisites.transforms])

    def set_parameters(self, parameters_dict, format_options=None):
        self.configuration_parameters = parameters_dict
        self.configuration_parameters[VERBOSE] = format_options.get(VERBOSE) if format_options else True
        self.configuration_parameters[QUIET] = format_options.get(QUIET) if format_options else False

    def set_data_enricher(self, data_enricher):
        self.transform_analyser = ConfigurableTransformStagesAnalyser(data_enricher.message.payloads_list, data_enricher.message.transforms_list, data_enricher.cirrus_proxy,
                                                          self.configuration_parameters)

    def analyse(self):
        return self.transform_analyser.analyse()

    def has_analysis_data(self):
        return True

    def get_analysis_data(self):
        return self.transform_analyser.get_results_records()


class YaraMovementPostJson(AbstractAlgorithm):
    def get_data_prerequistites(self):
        return frozenset([DataRequisites.payloads, DataRequisites.transforms])

    def set_data_enricher(self, data_enricher):
        self.transform_analyser = TransformStagesAnalyser(data_enricher.message.payloads_list, data_enricher.message.transforms_list, data_enricher.cirrus_proxy)

    def analyse(self):
        return self.transform_analyser.analyse()

    def has_analysis_data(self):
        return True

    def get_analysis_data(self):
        return self.transform_analyser.get_results_records()


class HasJsonPostErrorPayload(AbstractAlgorithm):
    def get_data_prerequistites(self):
        return frozenset([DataRequisites.payloads])

    def set_data_enricher(self, data_enricher):
        self.payloads = data_enricher.message.payloads_list

    def analyse(self):
        return process_message_payloads(self.payloads, "payload_is_http_error")

    def has_analysis_data(self):
        return False


class HasEmptyFieldsForPayload(AbstractAlgorithm):
    def get_data_prerequistites(self):
        return frozenset([DataRequisites.payloads])

    def set_parameters(self, parameters_dict, format_options=None):
        self.empty_fields_algo = DocumentEmptyFieldsParser(parameters_dict)
        if PAYLOAD_TRACKING_POINT in parameters_dict:
            self.payload_stage_to_fetch = parameters_dict[PAYLOAD_TRACKING_POINT]
        else:
            self.payload_stage_to_fetch = None

    def set_data_enricher(self, data_enricher):
        if self.payload_stage_to_fetch:
            self.payload_to_process = get_payload_object(self.payload_stage_to_fetch, data_enricher.message.payloads_list)
        else:
            self.payload_to_process = data_enricher.message.payloads_list[0]

    def analyse(self):
        try:
            self.json_result = self.empty_fields_algo.parse(self.payload_to_process)
        except MissingPayloadException as err:
            self.json_result = None
            return False
        return True

    def has_analysis_data(self):
        return True

    def get_analysis_data(self):
        return DocumentEmptyFieldsParser.format_as_csv(self.json_result)


class HasMandatoryFieldsForPayload(AbstractAlgorithm):
    def get_data_prerequistites(self):
        return frozenset([DataRequisites.payloads])

    def set_parameters(self, parameters_dict, format_options=None):
        self.mandatory_fields_algo = DocumentMandatoryFieldsParser(parameters_dict)
        if PAYLOAD_TRACKING_POINT in parameters_dict:
            self.payload_stage_to_fetch = parameters_dict[PAYLOAD_TRACKING_POINT]
        else:
            self.payload_stage_to_fetch = None

    def set_data_enricher(self, data_enricher):
        if self.payload_stage_to_fetch:
            self.payload_to_process = get_payload_object(self.payload_stage_to_fetch, data_enricher.message.payloads_list)
        else:
            self.payload_to_process = data_enricher.message.payloads_list[0]

    def analyse(self):
        try:
            self.json_result = self.mandatory_fields_algo.parse(self.payload_to_process)
        except MissingPayloadException as err:
            self.json_result = None
            return False
        return True

    def has_analysis_data(self):
        return True

    def get_analysis_data(self):
        return DocumentEmptyFieldsParser.format_as_csv(self.json_result)
