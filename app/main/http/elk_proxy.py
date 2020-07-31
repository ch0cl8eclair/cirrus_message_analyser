import json
import datetime
from elasticsearch import Elasticsearch
import re
from main.config.configuration import ConfigSingleton, LOGGING_CONFIG_FILE, get_configuration_dict
import logging
from logging.config import fileConfig

from main.config.constants import LEVEL, LINE, ELASTICSEARCH_CREDENTIALS, CREDENTIALS, \
    USERNAME, PASSWORD, ELASTICSEARCH_HOST, ELASTICSEARCH_SCHEME, ELASTICSEARCH_PORT, ELASTICSEARCH_INDEX, MESSAGE_ID, \
    HOST, LOGFILE, LOG_MESSAGE, HOST_LOG_MAPPINGS, LOG_CORRELATION_ID, LOG_LINES, ELASTICSEARCH_SECONDS_MARGIN, \
    LOG_STATEMENT_FOUND, TIME
from main.utils.utils import parse_json_from_file, format_datetime_to_zulu, convert_timestamp_to_datetime_str, convert_timestamp_to_datetime

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')

ES_QUERY_FILE = "resources/elastic_search_query.json"
LOG_CORRELATION_REGEX = re.compile(r'^\[([^\[]+)\]\s+\[([^\]]+)\]\s+start processing msg.*')


class ElasticsearchProxy:
    """This class performs a message id lookup on the ELK log server to determine which machine the msg was processed on"""

    def __init__(self):
        self.successfully_initialised = False
        self.configuration = ConfigSingleton()
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

    def lookup_message(self, message_uid, payloads_list):
        if not self.successfully_initialised:
            logger.error("Elasticsearch connection not successfully initialised, aborting lookup request!")
            return None
        logger.info("Attempt search of message: {} on elasticsearch server".format(message_uid))
        es_json_query = self._prepare_elastic_search_query(message_uid, payloads_list)
        elasticsearch_results = self._get_elasticsearch_results(es_json_query)
        result_record = self._process_es_message_uid_search_results(message_uid, elasticsearch_results)

        # do we have a correlation id, if so then rerun the search with it to get matching log statements
        if LOG_CORRELATION_ID in result_record and result_record[LOG_CORRELATION_ID]:
            log_correlation_id = result_record[LOG_CORRELATION_ID]
            logger.info("Attempting to fetch correlated log statements from elasticsearch")
            self._update_search_record_with_search_term(log_correlation_id, es_json_query)
            self._prepare_query_for_timestamp_desc_sort(es_json_query)
            log_lines_result = self._get_elasticsearch_results(es_json_query)
            if log_lines_result:
                log_lines = self._process_log_statments(log_lines_result)
                if log_lines:
                    result_record[LOG_LINES] = log_lines
        return result_record

    def _get_elasticsearch_results(self, es_json_query):
        """Issues elasticsearch query and returns results issuing standard logs statements"""
        search_index = self.configuration.get(ELASTICSEARCH_INDEX)
        logger.info("Querying elastic search on index: {} with query: {}".format(search_index, json.dumps(es_json_query)))
        elasticsearch_results = self.es.search(index=search_index, body=es_json_query)
        if elasticsearch_results:
            logger.debug("Received %d Hits from elasticsearch query" % elasticsearch_results['hits']['total']['value'])
            return elasticsearch_results
        else:
            logger.debug("No results found for elastic search msg query")
        return None

    def _prepare_search_term(self, search_key):
        return search_key.replace('-', ' ')

    def _update_search_record_with_search_term(self, search_key, query_json):
        search_message_id = self._prepare_search_term(search_key)
        query_json['query']['bool']['must'][0]['multi_match']['query'] = search_message_id

    def _prepare_elastic_search_query(self, message_uid, message_payloads):
        # format values for search purposes
        if message_payloads:
            from_date = message_payloads[0].get('insertDate')
            to_date = message_payloads[-1].get('insertDate')
            # logger.debug("search window from payloads is: from:    {}, to: {}".format(convert_timestamp_to_datetime_str(from_date), convert_timestamp_to_datetime_str(to_date)))
            search_from_date, search_to_date = self._prepare_search_time_window(from_date, to_date)
            logger.debug("Search window after adding margin: from: {}, to: {}".format(search_from_date, search_to_date))

        # Read query string and update
        query_json = parse_json_from_file(ES_QUERY_FILE)
        self._update_search_record_with_search_term(message_uid, query_json)
        if message_payloads:
            query_json['query']['bool']['filter'][0]['range']['@timestamp']['gte'] = search_from_date
            query_json['query']['bool']['filter'][0]['range']['@timestamp']['lte'] = search_to_date
        return query_json

    def _prepare_search_time_window(self, from_timestamp, to_timestamp):
        """Given the from and to Cirrus timestamps time window add a little margin either side"""
        from_date = convert_timestamp_to_datetime(from_timestamp)
        to_date = convert_timestamp_to_datetime(to_timestamp)
        # default to 45 if not specified
        seconds_delta = self.configuration.get(ELASTICSEARCH_SECONDS_MARGIN)
        if not seconds_delta:
            seconds_delta = 45
        time_delta = datetime.timedelta(seconds=seconds_delta)
        from_date = from_date - time_delta
        to_date = to_date + time_delta
        return format_datetime_to_zulu(from_date), format_datetime_to_zulu(to_date)

    @staticmethod
    def _prepare_query_for_timestamp_desc_sort(query_json):
        query_json['sort'] = [{ "@timestamp" : "asc" }]

    @staticmethod
    def _process_log_statments(es_log_lines_result):
        """Given the log statements from elasticsearch return a list of dicts with log level and log statement"""
        log_lines = []
        if es_log_lines_result:
            for record in es_log_lines_result['hits']['hits']:
                log_lines_dict = {}
                if '_source' in record and record['_source']['message']:
                    log_lines_dict[TIME] = record['_source'].get('@timestamp', '')
                    log_lines_dict[LEVEL] = record['_source'].get('level', '')
                    log_lines_dict[LINE] = record['_source'].get('message', '')
                    log_lines.append(log_lines_dict)
        return log_lines

    @staticmethod
    def _process_es_message_uid_search_results(message_uid, result):
        """Given the message uid elasticsearch results, verify the data is for the correct uid and pull out host details etc"""
        result_dict = {MESSAGE_ID: message_uid}
        has_matched_message_uid = False
        host_location_lines = []
        host_log_dict = {}
        if result:
            output_es_results(message_uid, result)
            current_host = ""
            # Pull out host and logfile names
            for record in result['hits']['hits']:
                if record['_source']['host']:
                    current_host = record['_source']['host']['name']
                if record['_source']['source']:
                    log_file_name = record['_source']['source']
                    if current_host and log_file_name:
                        host_log_dict[current_host] = log_file_name
                if '_source' in record and message_uid in record['_source']['message']:
                    has_matched_message_uid = True
                    # Attempt to find correlation id, we attempt to look for this start processing msg
                    if "start processing msg" in record['_source']['message']:
                        match = LOG_CORRELATION_REGEX.match(record['_source']['message'])
                        if match and len(match.groups()) == 2:
                            log_correlation_id = match.group(1)
                            logger.info("Found log correlation id: {}".format(log_correlation_id))
                            result_dict[LOG_CORRELATION_ID] = log_correlation_id
            # End for
        result_dict[LOG_STATEMENT_FOUND] = has_matched_message_uid
        # reformat the host and log data so that it can be formatted
        if host_log_dict:
            for k, v in host_log_dict.items():
                host_location_lines.append({HOST: k, LOGFILE: v})
            result_dict[HOST_LOG_MAPPINGS] = host_location_lines
        logger.debug("List of host/logs for msg: {}".format(json.dumps(host_log_dict)))
        return result_dict


def output_es_results(message_uid, results):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    with open(f'es-output-{message_uid}-{timestamp}.txt', 'w') as writer:
        writer.write(json.dumps(results))


def main():
    config = ConfigSingleton(get_configuration_dict())
    es_proxy = ElasticsearchProxy()
    # uid = "d3001b5a-ad37-4032-a91d-71d1ad5e4441"
    uid = "8a3d3300-9d51-43c2-819b-4ca95bba1126"
    result = es_proxy.lookup_message(uid, None)
    print(result)


if __name__ == '__main__':
    main()
