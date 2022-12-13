import datetime
import json
import logging
import operator
import re
import hashlib
from collections import defaultdict
from logging.config import fileConfig
from functools import reduce
from elasticsearch import Elasticsearch

from main.algorithms.payload_operations import determine_message_playback_count_from_payloads, \
    get_final_message_processing_time_window
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE, get_configuration_dict
from main.config.constants import ELASTICSEARCH_CREDENTIALS, CREDENTIALS, \
    USERNAME, PASSWORD, ELASTICSEARCH_HOST, ELASTICSEARCH_SCHEME, ELASTICSEARCH_PORT, ELASTICSEARCH_INDEX, MESSAGE_ID, \
    HOST, LOGFILE, HOST_LOG_MAPPINGS, ELASTICSEARCH_SECONDS_MARGIN, \
    LOG_STATEMENT_FOUND, DataType, ELASTICSEARCH_EXCLUDE_LOG_FILES, HOST_LOG_CORRELATION_ID, LOG_LINE_STATS, \
    ELASTICSEARCH_RETAIN_SERVER_OUTPUT, ELASTICSEARCH_SECONDS_MARGIN_FOR_ICE, LogSearchDirection, WEEK, ELASTIC_CFG, \
    CONFIG
from main.formatter.dual_formatter import LogAndFileFormatter
from main.formatter.file_output import FileOutputFormatter
from main.formatter.formatter import Formatter
from main.model.model_utils import CacheMissException
from main.utils.utils import parse_json_from_file, format_datetime_to_zulu, convert_timestamp_to_datetime_str, \
    convert_timestamp_to_datetime, parse_timezone_datetime_str, parse_datetime_str, error_and_exit, unpack_config, \
    get_merged_app_cfg
from main.http.proxy_cache import ProxyCache, FailedToCommunicateWithSystem
from main.model.model_utils import CacheMissException


fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('requester')

ES_QUERY_FILE = "resources/elastic_search_query.json"
# [JCoServerThread-6@T-2ccbcdb6] [PoolingWorkflow] start processing message [[com.adaptris.core.DefaultAdaptrisMessageImp] uniqueId [d3001b5a-ad37-4032-a91d-71d1ad5e4441] metadata [{jcoidoctyp=DELVRY07}]]
LOG_CORRELATION_REGEX = re.compile(r'^\[([^\[]+)\]\s+\[([^\]]+)\]\s+start processing m\w+.*')

# [managed-out-transform(3f2e83ee)] [com.adaptris.core.PoolingWorkflow] message [d3001b5a-ad37-4032-a91d-71d1ad5e4441] processed in [220] ms
LOG_CORRELATION_END_REGEX = re.compile(r'^\[([^\[]+)\]\s+\[([^\]]+)\]\s+message \[([^\]]+)\]\s+processed in \[([^\]]+)\]\s+ms.*')

PROCESS_START_LOG_MESSAGES = ["start processing msg", "start processing message"]
PROCESSED_LOG_MESSAGES = [" processed in "]



def _print_filtered_msg_line(record):
    logger.info("{} {} {} {} {}".format(
            record['_source'].get('host', {}).get('name', ''),
            record['_source']['source'],
            record['_source'].get('level', ''),
            record['_source'].get('@timestamp', ''),
            record['_source'].get('message', '')
        )
    )


class ElasticsearchProxy:
    """This class performs a message id lookup on the ELK log server to determine which machine the msg was processed on"""

    def __init__(self, merged_app_cfg):
        self.successfully_initialised = False
        self.configuration = ConfigSingleton()
        self.file_output_service = FileOutputFormatter()
        self.merged_app_cfg = merged_app_cfg

        username = unpack_config(merged_app_cfg, ELASTIC_CFG, CREDENTIALS, USERNAME)
        password = unpack_config(merged_app_cfg, ELASTIC_CFG, CREDENTIALS, PASSWORD)
        host = unpack_config(merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_HOST)
        port = int(unpack_config(merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_PORT))
        scheme = unpack_config(merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_SCHEME)

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
            error_and_exit(str(ex))
        self.cache = ProxyCache()

    def _retain_es_server_output(self):
        retain_output = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_RETAIN_SERVER_OUTPUT)
        if retain_output is not None:
            return bool(retain_output)
        return True

    def _lookup_initial_message_results_grouped_by_host(self, message_uid, es_json_query):
        logger.info("Attempt search of message: {} on elasticsearch server".format(message_uid))
        elasticsearch_results = self._handle_paginated_results(es_json_query)
        if self._retain_es_server_output():
            self.file_output_service.output_json_data_to_file(message_uid, DataType.elastic_search_results_correlated, elasticsearch_results)
        # filter out the message correlation ids, hosts and logs files
        result_record = self._filter_by_exact_uid_and_group_by_host_and_logname(message_uid, elasticsearch_results)
        return result_record

    def _lookup_initial_message_results_stats(self, message_uid, es_json_query, hosts_data):
        logger.info("Attempt search of message: {} on elasticsearch server".format(message_uid))
        elasticsearch_results = self._handle_paginated_results(es_json_query)
        result_set_size = self._get_es_result_count(elasticsearch_results)
        if result_set_size:
            if self._retain_es_server_output():
                self.file_output_service.output_json_data_to_file(message_uid, DataType.elastic_search_results_correlated, elasticsearch_results)
            self._filter_by_exact_uid_and_obtain_start_end_processing_times(message_uid, elasticsearch_results, hosts_data)
        return result_set_size

    def _get_elasticsearch_cache_key(self, message_uid, es_json_query):
        query_hash = hashlib.sha1(json.dumps(es_json_query, sort_keys=True).encode()).hexdigest()
        return "{}-{}".format(message_uid, query_hash)

    def _lookup_correlated_ids_for_message(self, message_uid, es_json_query, result_record):
        cache_key = self._get_elasticsearch_cache_key(message_uid, es_json_query)
        try:
            return self.cache.get_cache_result_dict(cache_key)
        except CacheMissException as ce:
            pass

        # We need to filter out the exclude logs
        exclude_logs = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_EXCLUDE_LOG_FILES)

        # do we have a correlation id, if so then rerun the search with it to get matching log statements
        statement_type_counts = {}
        if HOST_LOG_CORRELATION_ID in result_record and result_record[HOST_LOG_CORRELATION_ID]:
            for current_host in result_record[HOST_LOG_CORRELATION_ID]:
                for current_host_logfile in result_record[HOST_LOG_CORRELATION_ID][current_host]:
                    if exclude_logs and current_host_logfile in exclude_logs:
                        logger.debug("Filtering out given log: {} as it is configured as excluded".format(current_host_logfile))
                        continue
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

        self.cache.store_cache_result_dict(cache_key, result_record, WEEK)
        return result_record

    def lookup_message_within_supplied_time_window(self, message_uid, start_time, end_time):
        if not self.successfully_initialised:
            logger.error("Elasticsearch connection not successfully initialised, aborting lookup request!")
            return None
        es_json_query = self._prepare_elastic_search_query(message_uid, start_time, end_time)
        result_record = self._lookup_initial_message_results_grouped_by_host(message_uid, es_json_query)
        return self._lookup_correlated_ids_for_message(message_uid, es_json_query, result_record)

    @staticmethod
    def get_index_element_or_default(date_collection, required_index, default_date):
        if date_collection:
            return date_collection[required_index]
        else:
            return default_date

    def _get_wider_search_window_from_dates(self, hosts_data, original_start_time, original_end_time):
        collected_start_times = ElasticsearchProxy.get_times_from_host_data("start_times", hosts_data)
        collected_end_times = ElasticsearchProxy.get_times_from_host_data("end_times", hosts_data)
        # collected_start_times.append(parse_datetime_str(original_start_time)).sort()
        # collected_end_times.append(parse_datetime_str(original_end_time)).sort()
        collected_start_times.sort()
        collected_end_times.sort()

        wider_start_time = ElasticsearchProxy.get_index_element_or_default(collected_start_times, 0, original_start_time)
        wider_end_time = ElasticsearchProxy.get_index_element_or_default(collected_end_times, -1, original_end_time)
        return wider_start_time, wider_end_time

    def lookup_message_around_supplied_time(self, message_uid, given_start_time):
        """Retrieves logs for an ice message uid where we just have a single date instead of a time window.
        Therefore we must obtain a time window by repeatedly querying ELK for the message id in varying
        timeframes either forward or backwards from the supplied time.
        """
        logger.info("lookup_message_around_supplied_time start")
        if not self.successfully_initialised:
            logger.error("Elasticsearch connection not successfully initialised, aborting lookup request!")
            return None
        original_start_time, original_end_time = self._prepare_search_time_window_from_ice_message_date(given_start_time)

        hosts_data = defaultdict(lambda: defaultdict(dict))

        self.find_messages_via_timeframes(message_uid, original_start_time, original_end_time, LogSearchDirection.both, hosts_data)
        # we now should have the data to form a valid log search time window
        wider_start_time, wider_end_time = self._get_wider_search_window_from_dates(hosts_data, original_start_time, original_end_time)

        result_record = self.convert_hosts_data_to_standard_results_dict(message_uid, hosts_data)
        logger.info("lookup_message_around_supplied_time end, now making call to retrieve individual logs")
        es_json_query = self._prepare_elastic_search_query(message_uid, wider_start_time, wider_end_time)
        return self._lookup_correlated_ids_for_message(message_uid, es_json_query, result_record)

    @staticmethod
    def get_times_from_host_data(field_name, hosts_data):
        collected_times = []
        for hostname, hostdata in hosts_data.items():
            for logfile_name, log_data in hostdata.items():
                if field_name in log_data:
                    collected_times.extend(log_data[field_name])
        return collected_times

    # define recursive func
    # search start date / end date, direction
    # get results, if zero return
    # if differences then
    # if forward then create new window and call recursive function
    # if backward then create new window and call recursive function
    # LogSearchDirection
    # TODO this method is unbounded and may cause stackoverflow based on ELK data, need to set maximum lookup limits
    def find_messages_via_timeframes(self, message_uid, start_time, end_time, direction, hosts_data):
        es_json_query = self._prepare_elastic_search_query(message_uid, start_time, end_time)
        found_records = self._lookup_initial_message_results_stats(message_uid, es_json_query, hosts_data)
        if found_records == 0:
            logger.debug("No records found, ending search in direction: {}".format(direction))
            return
        differences = self.get_start_end_msg_differences(hosts_data)
        start_count = reduce(lambda a, b: a if (a > b) else b, differences)
        end_count = reduce(lambda a, b: a if (a < b) else b, differences)

        if start_count > 0 and direction in [LogSearchDirection.forward, LogSearchDirection.both]:
            logger.info("Need to extend time window forward")
            dates = self._prepare_search_time_window_in_given_direction(parse_datetime_str(end_time), True)
            start_time, end_time = dates
            self.find_messages_via_timeframes(message_uid, start_time, end_time, LogSearchDirection.forward, hosts_data)
        elif end_count < 0 and direction in [LogSearchDirection.backward, LogSearchDirection.both]:
            logger.info("Need to extend time window backward")
            dates = self._prepare_search_time_window_in_given_direction(parse_datetime_str(start_time), False)
            start_time, end_time = dates
            self.find_messages_via_timeframes(message_uid, start_time, end_time, LogSearchDirection.backward, hosts_data)
        else:
            logger.debug("Start and end messages match up")
        return

    def get_start_end_msg_differences(self, results):
        diff_list = []
        for hostname, hostdata in results.items():
            for logfile_name, log_data in hostdata.items():
                start_count = 0
                end_count = 0
                if "start_times" in log_data:
                    start_count = len(log_data["start_times"])
                if "end_times" in log_data:
                    end_count = len(log_data["end_times"])
                logger.debug("Logfile: {}, start count: {}, end count: {}".format(logfile_name, start_count, end_count))
                diff_list.append(start_count - end_count)
        return diff_list

    def convert_hosts_data_to_standard_results_dict(self, message_uid, hosts_data):
        has_matched_message_uid = False
        correlation_results = defaultdict(lambda: defaultdict(dict))
        host_log_mappings = []
        for hostname, hostdata in hosts_data.items():
            for logfile_name, log_data in hostdata.items():
                host_log_mappings.append({HOST: hostname, LOGFILE: logfile_name})
                if len(log_data.get("correlation_ids", [])) > 0:
                    has_matched_message_uid = True
                if not logfile_name in correlation_results[hostname]:
                    correlation_results[hostname][logfile_name] = []
                correlation_results[hostname][logfile_name].extend(log_data.get("correlation_ids", []))

        result_dict = {MESSAGE_ID: message_uid}
        result_dict[HOST_LOG_CORRELATION_ID] = correlation_results
        result_dict[LOG_STATEMENT_FOUND] = has_matched_message_uid
        result_dict[HOST_LOG_MAPPINGS] = host_log_mappings

        return result_dict

    # TODO implement caching check
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
            logger.debug("Received %d hits from elasticsearch query" % elasticsearch_results['hits']['total']['value'])
            return elasticsearch_results
        else:
            logger.debug("No results found for elastic search msg query")
        return None

    def _handle_paginated_results(self, es_json_query):
        # update this
        elasticsearch_max_result_limit = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, "elasticsearch_max_result_limit")
        elasticsearch_batch_size = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, "elasticsearch_batch_size")
        search_index = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_INDEX)

        logger.debug("Handling elastic search paginated request on index: {}".format(search_index))
        # Issue initial query
        es_json_query["size"] = elasticsearch_batch_size
        if "from" in es_json_query:
            del es_json_query["from"]
        intial_elasticsearch_results = self._get_elasticsearch_results(search_index, es_json_query)
        # capture result set size
        result_set_size = self._get_es_result_count(intial_elasticsearch_results)
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

    @staticmethod
    def _prepare_search_term(search_key):
        temp_term = search_key.replace('-', ' ')
        temp_term = temp_term.replace('(', ' ')
        temp_term = temp_term.replace(')', ' ')
        return temp_term.strip()

    @staticmethod
    def _obtain_all_correlation_ids(filelog_correlation_ids):
        results = reduce(operator.concat, [list(filelog_correlation_ids[key]) for key in filelog_correlation_ids])
        return results

    @staticmethod
    def _update_search_record_with_multiple_search_terms(correlation_ids_list, query_json):
        # correlation_ids_list = self._obtain_all_correlation_ids(filelog_correlation_ids)
        correlation_query_list = [{"multi_match": {"query": ElasticsearchProxy._prepare_search_term(cid), "fields": ["message"], "type": "phrase", "operator": "and"}} for cid in correlation_ids_list]
        if "must" in query_json['query']['bool']:
            del query_json['query']['bool']['must']
        query_json['query']['bool']['should'] = correlation_query_list

    @staticmethod
    def _update_search_record_with_search_term(search_key, query_json):
        search_message_id = ElasticsearchProxy._prepare_search_term(search_key)
        query_json['query']['bool']['must'][0]['multi_match']['query'] = search_message_id

    @staticmethod
    def _get_time_window_dates_from_payloads(message_payloads):
        """Gets the elk logs search window from the payloads, taking into consideration how many times the msg has been processed"""
        search_from_date, search_to_date = (None, None)
        if message_payloads:
            # Determine how many times the message has been through the system
            message_repeat_count = determine_message_playback_count_from_payloads(message_payloads)
            logger.info("Message has gone through the system {} time(s), only considering final pass through time window".format(message_repeat_count))
            # Only get the logs for the last processing on the message:
            from_date, to_date = get_final_message_processing_time_window(message_payloads, message_repeat_count)
            logger.debug("search window from payloads is: from:    {}, to: {}".format(convert_timestamp_to_datetime_str(from_date), convert_timestamp_to_datetime_str(to_date)))
            search_from_date, search_to_date = ElasticsearchProxy._prepare_search_time_window(from_date, to_date)
            logger.debug("Search window after adding margin: from: {}, to: {}".format(search_from_date, search_to_date))
        return search_from_date, search_to_date

    @staticmethod
    def _prepare_elastic_search_query_from_payloads(message_uid, message_payloads):
        # obtain and format values for search purposes
        search_from_date, search_to_date = ElasticsearchProxy._get_time_window_dates_from_payloads(message_payloads)
        return ElasticsearchProxy._prepare_elastic_search_query(message_uid, search_from_date, search_to_date)

    @staticmethod
    def _prepare_elastic_search_query(message_uid, search_from_date, search_to_date):
        # Read query string and update
        query_json = parse_json_from_file(ES_QUERY_FILE)
        ElasticsearchProxy._update_search_record_with_search_term(message_uid, query_json)
        if search_from_date:
            query_json['query']['bool']['filter'][0]['range']['@timestamp']['gte'] = search_from_date
        if search_to_date:
            query_json['query']['bool']['filter'][0]['range']['@timestamp']['lte'] = search_to_date
        return query_json

    def _prepare_search_time_window(self, from_timestamp, to_timestamp):
        """Given the from and to Cirrus timestamps time window add a little margin either side"""
        from_date = convert_timestamp_to_datetime(from_timestamp)
        to_date = convert_timestamp_to_datetime(to_timestamp)
        time_delta = self.self._get_seconds_time_delta(False)
        from_date = from_date - time_delta
        to_date = to_date + time_delta
        return format_datetime_to_zulu(from_date), format_datetime_to_zulu(to_date)

    # parse_timezone_datetime_str parses ice datetime to utc datetime
    def _prepare_search_time_window_from_ice_message_date(self, given_date_time):
        """Given the from and to Cirrus timestamps time window add a little margin either side"""
        # default to 10 if not specified
        time_delta = self._get_seconds_time_delta(True)
        from_date = given_date_time - time_delta
        to_date = given_date_time + time_delta
        return format_datetime_to_zulu(from_date), format_datetime_to_zulu(to_date)

    def _get_seconds_time_delta(self, is_ice=False):
        config_variable = ELASTICSEARCH_SECONDS_MARGIN_FOR_ICE if is_ice else ELASTICSEARCH_SECONDS_MARGIN
        seconds_delta = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, config_variable)

        if not seconds_delta:
            seconds_delta = 10
        return datetime.timedelta(seconds=seconds_delta)

    def _prepare_search_time_window_in_given_direction(self, given_date_time, forward=True):
        """Given the from and to Cirrus timestamps time window add a little margin either side"""
        logger.debug("_prepare_search_time_window_in_given_direction: {}".format(given_date_time))
        # default to 10 if not specified
        seconds_delta = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_SECONDS_MARGIN_FOR_ICE)
        if not seconds_delta:
            seconds_delta = 10
        time_delta = datetime.timedelta(seconds=seconds_delta)
        if forward:
            from_date = given_date_time
            to_date = given_date_time + time_delta
        else:
            from_date = given_date_time - time_delta
            to_date = given_date_time
        return format_datetime_to_zulu(from_date), format_datetime_to_zulu(to_date)

    @staticmethod
    def _prepare_query_for_timestamp_asc_sort(query_json):
        query_json['sort'].insert(0, {"@timestamp": {"order": "asc"}})


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

    @staticmethod
    def _get_es_result_count(data):
        if data and 'hits' in data:
            return int(data['hits']['total']['value'])
        return 0

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
                # self._print_filtered_msg_line(record)
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

    def _filter_by_exact_uid_and_obtain_start_end_processing_times(self, message_uid, result, hosts_data):
        """Given the message uid elasticsearch results, verify the data is for the correct uid and pull out host details etc"""
        filter_strings = PROCESS_START_LOG_MESSAGES + PROCESSED_LOG_MESSAGES
        if result:
            if self._retain_es_server_output():
                self.file_output_service.output_json_data_to_file(message_uid, DataType.elastic_search_results, result)
            current_host = ""
            # Only consider results with our exact msg uid
            filtered_by_message_uid = [log_line for log_line in result['hits']['hits'] if '_source' in log_line and message_uid in log_line['_source']['message']]

            # Obtain all host and logfile values
            for record in filtered_by_message_uid:
                if record['_source']['host']:
                    current_host = record['_source']['host']['name']
                    hosts_data[current_host]
                if record['_source']['source']:
                    log_file_name = record['_source']['source']
                    if current_host and log_file_name:
                        hosts_data[current_host][log_file_name]
                if self.filter_log_statements(record, filter_strings):
                    log_correlation_id = None
                    match = LOG_CORRELATION_REGEX.match(record['_source']['message'])
                    current_host = record['_source']['host']['name']
                    log_file_name = record['_source']['source']
                    list_keys = ["correlation_ids", "start_times", "end_times"]
                    for key in list_keys:
                        if not key in hosts_data[current_host][log_file_name]:
                            hosts_data[current_host][log_file_name][key] = []

                    if match and len(match.groups()) == 2:
                        start_time = record['_source'].get('@timestamp', None)
                        log_correlation_id = match.group(1)
                        hosts_data[current_host][log_file_name]["correlation_ids"].append(log_correlation_id)
                        hosts_data[current_host][log_file_name]["start_times"].append(start_time)
                    else:
                        match = LOG_CORRELATION_END_REGEX.match(record['_source']['message'])
                        if match and len(match.groups()) == 4:
                            log_correlation_id = match.group(1)
                            end_time = record['_source'].get('@timestamp', None)
                            hosts_data[current_host][log_file_name]["correlation_ids"].append(log_correlation_id)
                            hosts_data[current_host][log_file_name]["start_times"].append(end_time)
            # End for
        return hosts_data

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
        logger.debug("Obtaining log correlation ids from elk results")
        new_results_map = defaultdict(lambda: defaultdict(list))
        filter_strings = PROCESS_START_LOG_MESSAGES + PROCESSED_LOG_MESSAGES
        exclude_logs = unpack_config(self.merged_app_cfg, ELASTIC_CFG, CONFIG, ELASTICSEARCH_EXCLUDE_LOG_FILES)
        filtered_log_lines = [record2 for record2 in [record for record in result if '_source' in record and message_uid in record['_source']['message']] if self.filter_log_statements(record2, filter_strings)]
        for filtered_record in filtered_log_lines:
            # self._print_filtered_msg_line(filtered_record)
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
    options = {'output': 'table', 'quiet': False, 'verbose': False, 'env': 'PRD', 'region': 'EU'}
    merged_app_cfg = get_merged_app_cfg(config, ELASTIC_CFG, options)
    es_proxy = ElasticsearchProxy(merged_app_cfg)
    file_generator = FileOutputFormatter()
    formatter = Formatter()
    details_formatter = LogAndFileFormatter(formatter, file_generator, None)

    # uid = "b4ff64a9-b4e8-457f-b332-f794700b3e28"
    # date_str = "2020-09-01 11:21:47 BST"
    # uid = "b96ba3c6-c113-47ac-accb-b5d01019b46e"
    # date_str = "2020-09-02 10:35:30 BST"
    uid = "7775989e-0e64-4e9d-971b-0ce0b9605006"
    date_str = "2020-09-04 13:59:58 BST"
    # uid = "8861fd66-41f1-437e-9b4f-5abcd33dea3a"
    # date_str = "2020-08-11 15:37:50 BST"

    # date_str = "2020-08-11 15:37:44 BST"
    dt = parse_timezone_datetime_str(date_str)
    result = es_proxy.lookup_message_around_supplied_time(uid, dt)
    print(json.dumps(result))
    details_formatter.format_server_log_details(uid, result, options)

    # uid = "d3001b5a-ad37-4032-a91d-71d1ad5e4441"
    # # uid = "8a3d3300-9d51-43c2-819b-4ca95bba1126"
    # es_result_file = "es-output-d3001b5a-ad37-4032-a91d-71d1ad5e4441-2020-07-31-15-19-55.txt"
    # es_json = parse_json_from_file(es_result_file)
    # result = es_proxy._parse_log_correlation_ids(uid, es_json['hits']['hits'])
    # result = es_proxy._prepare_log_correlation_ids(result)
    # # es_proxy._process_es_message_uid_search_results(uid, es_json
    # # result = es_proxy.lookup_message(uid, none)
    # print(result)

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
