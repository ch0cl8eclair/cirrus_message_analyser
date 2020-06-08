import importlib
import unittest
# import main.algorithms.algorithms.AbstractAlgorithm
# import main.message_processor.DataRequisites


def instantiate_algorithm_class(algorithm_name):
    algorithm_module = importlib.import_module("main.algorithms.algorithms")
    AlgoClass = getattr(algorithm_module, algorithm_name)
    algorithm_instance = AlgoClass()
    return algorithm_instance


class MessageProcessorTest(unittest.TestCase):
    def test_instantiate_algorithm(self):
        algo_name = "AbstractAlgorithm"
        algo_instance = instantiate_algorithm_class(algo_name)
        self.assertEqual(algo_name, type(algo_instance).__name__)

        # Check that it is the correct class by checking the functions available
        object_methods = [method_name for method_name in dir(algo_instance) if callable(getattr(algo_instance, method_name))]
        self.assertTrue("get_data_prerequistites" in object_methods)
        self.assertTrue("set_parameters" in object_methods)
        self.assertTrue("set_data_enricher" in object_methods)
        self.assertTrue("analyse" in object_methods)
        self.assertTrue("has_analysis_data" in object_methods)
        self.assertTrue("get_analysis_data" in object_methods)


if __name__ == '__main__':
    unittest.main()
