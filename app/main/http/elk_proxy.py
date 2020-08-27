import datetime
import json
import logging
import operator
import re
from collections import defaultdict
from functools import reduce
from logging.config import fileConfig

from elasticsearch import Elasticsearch

from main.algorithms.payload_operations import determine_message_playback_count_from_payloads, \
    get_final_message_processing_time_window
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE, get_configuration_dict
from main.config.constants import ELASTICSEARCH_CREDENTIALS, CREDENTIALS, \
    USERNAME, PASSWORD, ELASTICSEARCH_HOST, ELASTICSEARCH_SCHEME, ELASTICSEARCH_PORT, ELASTICSEARCH_INDEX, MESSAGE_ID, \
    HOST, LOGFILE, HOST_LOG_MAPPINGS, ELASTICSEARCH_SECONDS_MARGIN, \
    LOG_STATEMENT_FOUND, DataType, ELASTICSEARCH_EXCLUDE_LOG_FILES, HOST_LOG_CORRELATION_ID, LOG_LINE_STATS, \
    ELASTICSEARCH_RETAIN_SERVER_OUTPUT
from main.formatter.file_output import FileOutputFormatter
from main.utils.utils import parse_json_from_file, format_datetime_to_zulu, convert_timestamp_to_datetime_str, \
    convert_timestamp_to_datetime

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')

ES_QUERY_FILE = "resources/elastic_search_query.json"
# [JCoServerThread-6@T-2ccbcdb6] [PoolingWorkflow] start processing message [[com.adaptris.core.DefaultAdaptrisMessageImp] uniqueId [d3001b5a-ad37-4032-a91d-71d1ad5e4441] metadata [{jcoidoctyp=DELVRY07}]]
LOG_CORRELATION_REGEX = re.compile(r'^\[([^\[]+)\]\s+\[([^\]]+)\]\s+start processing m\w+.*')

# [managed-out-transform(3f2e83ee)] [com.adaptris.core.PoolingWorkflow] message [d3001b5a-ad37-4032-a91d-71d1ad5e4441] processed in [220] ms
LOG_CORRELATION_END_REGEX = re.compile(r'^\[([^\[]+)\]\s+\[([^\]]+)\]\s+message \[([^\]]+)\]\s+processed in \[([^\]]+)\]\s+ms.*')

PROCESS_START_LOG_MESSAGES = ["start processing msg", "start processing message"]
PROCESSED_LOG_MESSAGES = [" processed in "]


class ElasticsearchProxy:
    """This class performs a message id lookup on the ELK log server to determine which machine the msg was processed on"""

    def __init__(self):
        self.successfully_initialised = False
        self.configuration = ConfigSingleton()
        self.file_output_service = FileOutputFormatter()
        username = self.configuration.get(CREDENTIALS).get(ELASTICSEARCH_CREDENTIALS).get(USERNAME)
        password = self.configuration.get(CREDENTIALS).get(ELASTICSEARCH_CREDENTIALS).get(PASSWORD)
        host = self.configuration.get(ELASTICSEARCH_HOST)
        port = int(self.configuration.get(ELASTICSEARCH_PORT))
        scheme = self.configuration.get(ELASTICSEARCH_SCHEME)
        self.es = Elasticsearch(
            [host],
            http_auth=(username, password),
            scheme=scheme,
            port=port,
        )
        # Check status
        try:
            health_check_result = self.es.cluster.health()
            self.successfully_initialised = True
            logger.debug("Elastic search health check returned: {}".format(json.dumps(health_check_result)))
        except Exception as ex:
            logger.error("Failed to initialise connection to elasticsearch", ex)

    def _retain_es_server_output(self):
        if self.configuration.has_key(ELASTICSEARCH_RETAIN_SERVER_OUTPUT):
            return bool(self.configuration.get(ELASTICSEARCH_RETAIN_SERVER_OUTPUT))
        return True

    def _lookup_initial_message_results_grouped_by_host(self, message_uid, es_json_query):
        logger.info("Attempt search of message: {} on elasticsearch server".format(message_uid))
        elasticsearch_results = self._handle_paginated_results(es_json_query)
        if self._retain_es_server_output():
            self.file_output_service.output_json_data_to_file(message_uid, DataType.elastic_search_results_correlated, elasticsearch_results)
        # filter out the message correlation ids, hosts and logs files
        result_record = self._filter_by_exact_uid_and_group_by_host_and_logname(message_uid, elasticsearch_results)
        return result_record

    def _lookup_correlated_ids_for_message(self, message_uid, es_json_query, result_record):
        # do we have a correlation id, if so then rerun the search with it to get matching log statements
        statement_type_counts = {}
        if HOST_LOG_CORRELATION_ID in result_record and result_record[HOST_LOG_CORRELATION_ID]:
            for current_host in result_record[HOST_LOG_CORRELATION_ID]:
                for current_host_logfile in result_record[HOST_LOG_CORRELATION_ID][current_host]:
                    unique_correlation_ids = set(result_record[HOST_LOG_CORRELATION_ID][current_host][current_host_logfile])
                    # filelog_correlation_ids = result_record[HOST_LOG_CORRELATION_ID]
                    logger.info("Attempting to fetch correlated log statements from elasticsearch for host: {} and logfile: {}".format(current_host, current_host_logfile))
                    self._update_search_record_with_multiple_search_terms(unique_correlation_ids, es_json_query)
                    self._prepare_query_for_log_retrieval_sorting(es_json_query)
                    log_lines_result = self._handle_paginated_results(es_json_query)
                    # Dump out the raw results
                    if self._retain_es_server_output():
                        es_filename = self.file_output_service.generate_host_log_filename(message_uid, current_host, current_host_logfile, False)
                        self.file_output_service.output_json_data_to_given_file(message_uid, es_filename, log_lines_result, DataType.elastic_search_results_correlated)
                    # Write out the logs immediately to avoid large memory footprint
                    log_lines_dict = {current_host: {current_host_logfile: self._get_es_result_hits(log_lines_result)}}
                    self.file_output_service.generate_log_statements(message_uid, log_lines_dict, statement_type_counts)
                # end for logfiles
            # end for hosts
        result_record[LOG_LINE_STATS] = statement_type_counts
        return result_record

    def lookup_message_within_supplied_time_window(self, message_uid, start_time, end_time):
        if not self.successfully_initialised:
            logger.error("Elasticsearch connection not successfully initialised, aborting lookup request!")
            return None
        es_json_query = self._prepare_elastic_search_query(message_uid, start_time, end_time)
        result_record = self._lookup_initial_message_results_grouped_by_host(message_uid, es_json_query)
        return self._lookup_correlated_ids_for_message(message_uid, es_json_query, result_record)

    def lookup_message(self, message_uid, payloads_list):
        if not self.successfully_initialised:
            logger.error("Elasticsearch connection not successfully initialised, aborting lookup request!")
            return None
        # Initial search by msg unique id
        es_json_query = self._prepare_elastic_search_query_from_payloads(message_uid, payloads_list)
        result_record = self._lookup_initial_message_results_grouped_by_host(message_uid, es_json_query)
        return self._lookup_correlated_ids_for_message(message_uid, es_json_query, result_record)

    def _get_elasticsearch_results(self, search_index, es_json_query):
        """Issues elasticsearch query and returns results issuing standard logs statements"""
        logger.debug("Querying elastic search on index: {} with query: {}".format(search_index, json.dumps(es_json_query)))
        elasticsearch_results = self.es.search(index=search_index, body=es_json_query)
        if elasticsearch_results:
            logger.debug("Received %d Hits from elasticsearch query" % elasticsearch_results['hits']['total']['value'])
            return elasticsearch_results
        else:
            logger.debug("No results found for elastic search msg query")
        return None

    def _handle_paginated_results(self, es_json_query):
        elasticsearch_max_result_limit = self.configuration.get("elasticsearch_max_result_limit")
        elasticsearch_batch_size = self.configuration.get("elasticsearch_batch_size")
        search_index = self.configuration.get(ELASTICSEARCH_INDEX)
        logger.debug("Handling elastic search paginated request on index: {}".format(search_index))
        # Issue initial query
        es_json_query["size"] = elasticsearch_batch_size
        if "from" in es_json_query:
            del es_json_query["from"]
        intial_elasticsearch_results = self._get_elasticsearch_results(search_index, es_json_query)
        # capture result set size
        result_set_size = int(intial_elasticsearch_results['hits']['total']['value'])
        # Do we have more records to fetch?
        if result_set_size > elasticsearch_batch_size:
            logger.debug("{} elastic search results received from a total of: {}".format(elasticsearch_batch_size, result_set_size))
            cummulative_result_set = intial_elasticsearch_results
            upper_bound = min(elasticsearch_max_result_limit, result_set_size)
            for from_value in range(elasticsearch_batch_size, upper_bound, elasticsearch_batch_size):
                es_json_query["from"] = from_value
                es_json_query["size"] = elasticsearch_batch_size
                logger.debug("Fetching elastic search results from postiion: {}".format(from_value))
                intermediate_elasticsearch_results = self._get_elasticsearch_results(search_index, es_json_query)
                if intermediate_elasticsearch_results and intermediate_elasticsearch_results["hits"]["hits"]:
                    cummulative_result_set["hits"]["hits"].extend(intermediate_elasticsearch_results["hits"]["hits"])
            return cummulative_result_set
        else:
            return intial_elasticsearch_results

    def _prepare_search_term(self, search_key):
        temp_term = search_key.replace('-', ' ')
        temp_term = temp_term.replace('(', ' ')
        temp_term = temp_term.replace(')', ' ')
        return temp_term.strip()

    def _obtain_all_correlation_ids(self, filelog_correlation_ids):
        results = reduce(operator.concat, [list(filelog_correlation_ids[key]) for key in filelog_correlation_ids])
        return results

    def _update_search_record_with_multiple_search_terms(self, correlation_ids_list, query_json):
        # correlation_ids_list = self._obtain_all_correlation_ids(filelog_correlation_ids)
        correlation_query_list = [{"multi_match": {"query": self._prepare_search_term(cid), "fields": ["message"], "type": "phrase", "operator": "and"}} for cid in correlation_ids_list]
        if "must" in query_json['query']['bool']:
            del query_json['query']['bool']['must']
        query_json['query']['bool']['should'] = correlation_query_list

    def _update_search_record_with_search_term(self, search_key, query_json):
        search_message_id = self._prepare_search_term(search_key)
        query_json['query']['bool']['must'][0]['multi_match']['query'] = search_message_id

    def _get_time_window_dates_from_payloads(self, message_payloads):
        """Gets the elk logs search window from the payloads, taking into consideration how many times the msg has been processed"""
        search_from_date, search_to_date = (None, None)
        if message_payloads:
            # Determine how many times the message has been through the system
            message_repeat_count = determine_message_playback_count_from_payloads(message_payloads)
            logger.info("Message has gone through the system {} time(s), only considering final pass through time window".format(message_repeat_count))
            # Only get the logs for the last processing on the message:
            from_date, to_date = get_final_message_processing_time_window(message_payloads, message_repeat_count)
            logger.debug("search window from payloads is: from:    {}, to: {}".format(convert_timestamp_to_datetime_str(from_date), convert_timestamp_to_datetime_str(to_date)))
            search_from_date, search_to_date = self._prepare_search_time_window(from_date, to_date)
            logger.debug("Search window after adding margin: from: {}, to: {}".format(search_from_date, search_to_date))
        return search_from_date, search_to_date

    def _prepare_elastic_search_query_from_payloads(self, message_uid, message_payloads):
        # obtain and format values for search purposes
        search_from_date, search_to_date = self._get_time_window_dates_from_payloads(message_payloads)
        return self._prepare_elastic_search_query(message_uid, search_from_date, search_to_date)

    def _prepare_elastic_search_query(self, message_uid, search_from_date, search_to_date):
        # Read query string and update
        query_json = parse_json_from_file(ES_QUERY_FILE)
        self._update_search_record_with_search_term(message_uid, query_json)
        if search_from_date:
            query_json['query']['bool']['filter'][0]['range']['@timestamp']['gte'] = search_from_date
        if search_to_date:
            query_json['query']['bool']['filter'][0]['range']['@timestamp']['lte'] = search_to_date
        return query_json

    def _prepare_search_time_window(self, from_timestamp, to_timestamp):
        """Given the from and to Cirrus timestamps time window add a little margin either side"""
        from_date = convert_timestamp_to_datetime(from_timestamp)
        to_date = convert_timestamp_to_datetime(to_timestamp)
        # default to 10 if not specified
        seconds_delta = self.configuration.get(ELASTICSEARCH_SECONDS_MARGIN)
        if not seconds_delta:
            seconds_delta = 10
        time_delta = datetime.timedelta(seconds=seconds_delta)
        from_date = from_date - time_delta
        to_date = to_date + time_delta
        return format_datetime_to_zulu(from_date), format_datetime_to_zulu(to_date)

    @staticmethod
    def _prepare_query_for_timestamp_asc_sort(query_json):
        query_json['sort'].insert(0, {"@timestamp": { "order" : "asc" }})


    @staticmethod
    def _prepare_query_for_score_desc_sort(query_json):
        query_json['sort'].insert(0, {"_score": { "order" : "desc" }})

    @staticmethod
    def _prepare_query_for_log_retrieval_sorting(query_json):
        query_json['sort'] = [
            {"_score": { "order" : "desc" }},
            {"@timestamp" : "asc"}
        ]

    @staticmethod
    def _get_es_result_hits(es_log_lines_result):
        """Given the log statements from elasticsearch return a list of dicts with log level and log statement"""
        return es_log_lines_result['hits']['hits']

    def _filter_by_exact_uid_and_group_by_host_and_logname(self, message_uid, result):
        """Given the message uid elasticsearch results, verify the data is for the correct uid and pull out host details etc"""
        result_dict = {MESSAGE_ID: message_uid}
        has_matched_message_uid = False
        # host_location_lines = []
        host_log_dict = defaultdict(list)
        if result:
            if self._retain_es_server_output():
                self.file_output_service.output_json_data_to_file(message_uid, DataType.elastic_search_results, result)
            current_host = ""
            # Only consider results with our exact msg uid
            filtered_by_message_uid = [log_line for log_line in result['hits']['hits'] if '_source' in log_line and message_uid in log_line['_source']['message']]
            if filtered_by_message_uid:
                has_matched_message_uid = True

            # Obtain all host and logfile values
            for record in filtered_by_message_uid:
                if record['_source']['host']:
                    current_host = record['_source']['host']['name']
                if record['_source']['source']:
                    log_file_name = record['_source']['source']
                    if current_host and log_file_name:
                        host_log_dict[current_host].append(log_file_name)
            # End for

            # Now obtain correlation_ids
            correlation_results = self._parse_log_correlation_ids(message_uid, filtered_by_message_uid)
            result_dict[HOST_LOG_CORRELATION_ID] = correlation_results

        result_dict[LOG_STATEMENT_FOUND] = has_matched_message_uid
        result_dict[HOST_LOG_MAPPINGS] = self._prepare_host_to_logfile_records(host_log_dict)
        logger.debug("List of host/logs for msg: {}".format(json.dumps(result_dict[HOST_LOG_MAPPINGS])))
        return result_dict

    def _prepare_host_to_logfile_records(self, host_log_dict):
        if host_log_dict:
            return [{HOST: hostname, LOGFILE: logname} for hostname, logs_list in host_log_dict.items() for logname in set(logs_list)]
        return None

    def filter_log_statements(self, log_statement, filter_strings):
        for start_search_term in filter_strings:
            if start_search_term in log_statement["_source"]["message"]:
                return True
        return False

    def _parse_log_correlation_ids(self, message_uid, result):
        new_results_map = defaultdict(lambda: defaultdict(list))
        filter_strings = PROCESS_START_LOG_MESSAGES + PROCESSED_LOG_MESSAGES
        exclude_logs = self.configuration.get(ELASTICSEARCH_EXCLUDE_LOG_FILES)
        filtered_log_lines = [record2 for record2 in [record for record in result if '_source' in record and message_uid in record['_source']['message']] if self.filter_log_statements(record2, filter_strings)]
        for filtered_record in filtered_log_lines:
            match = LOG_CORRELATION_REGEX.match(filtered_record['_source']['message'])
            log_correlation_id = None
            if match and len(match.groups()) == 2:
                log_correlation_id = match.group(1)
            else:
                match = LOG_CORRELATION_END_REGEX.match(filtered_record['_source']['message'])
                if match and len(match.groups()) == 4:
                    log_correlation_id = match.group(1)
            if log_correlation_id:
                logfile = filtered_record['_source']['source']
                if not logfile in exclude_logs:
                    current_host = filtered_record['_source']['host']['name']
                    # logger.debug("Found log correlation id: {} within log: {}".format(log_correlation_id, logfile))
                    new_results_map[current_host][logfile].append(log_correlation_id)
        return new_results_map


def output_es_results(message_uid, results):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    with open(f'es-output-{message_uid}-{timestamp}.txt', 'w') as writer:
        writer.write(json.dumps(results))


def main():
    json_txt = """
{
  "/opt/logs/eu0000000002": [
    "managed-in-transform(47b3eac)", "managed-out-transform(3f2e83ee)", "managed-send-transform(5e8a5443)"
  ],
  "/opt/logs/fr0000001236": [
    "jcoserverthread-6@t-2ccbcdb6"
  ],
  "/opt/logs/uk0000000067": [
    "eu-cirrus-mdm-feed@eu-cirrus-mdm(14ddad3f)"
  ],
  "/opt/logs/uk0000000052": [
    "cirrus-fr0000001224-movement"
  ]
}

 
    """
    # sample_json = json.loads(json_txt)
    # # flat_list = [item for sublist in sample_json for item in sublist]
    # flat_list = [sample_json[key] for key in sample_json]
    # l = reduce(operator.concat, flat_list)
    # print(l)
    # return
    #
    config = ConfigSingleton(get_configuration_dict())
    es_proxy = ElasticsearchProxy()
    uid = "d3001b5a-ad37-4032-a91d-71d1ad5e4441"
    # # uid = "8a3d3300-9d51-43c2-819b-4ca95bba1126"
    es_result_file = "es-output-d3001b5a-ad37-4032-a91d-71d1ad5e4441-2020-07-31-15-19-55.txt"
    es_json = parse_json_from_file(es_result_file)
    result = es_proxy._parse_log_correlation_ids(uid, es_json['hits']['hits'])
    # result = es_proxy._prepare_log_correlation_ids(result)
    # # es_proxy._process_es_message_uid_search_results(uid, es_json
    # # result = es_proxy.lookup_message(uid, none)
    print(result)

    # es_json = parse_json_from_file("resources/elastic_search_query_generated.json")
    # # es_json = parse_json_from_file(es_query_file)
    # results = es_proxy._handle_paginated_results(es_json)
    # print(results)
    # formatter = FileOutputFormatter()
    # correlation_logs = {"/opt/logs/uk0000000052": "blah"}
    # stats = formatter.generate_log_statements("123456", correlation_logs, results['hits']['hits'], True)
    # print(stats)


if __name__ == '__main__':
    main()
