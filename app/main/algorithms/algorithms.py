from collections.abc import Set

from main.algorithms.transform_stages import TransformStagesAnalyser
from main.config.constants import DataRequisites
from main.model.model_utils import process_message_payloads


class AbstractAlgorithm:
    def get_data_prerequistites(self):
        """Return a Set of message data prerequisites to perform the analysis, ie must have events and status"""
        pass

    def set_parameters(self, parameters_dict):
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
        pass


class YaraMovementPostJson(AbstractAlgorithm):
    def get_data_prerequistites(self):
        return frozenset([DataRequisites.status, DataRequisites.payloads, DataRequisites.transforms])

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