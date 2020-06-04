from main.algorithms.payload_predicates import payloads_match_single_yara_movement_case


class PredicateAlgorithm:
    def test(self, message):
        pass


class YaraMovementPostJsonPredicate(PredicateAlgorithm):
    def test(self, message):
        return payloads_match_single_yara_movement_case(message.payloads_list, message.get_transform_stage_names())
