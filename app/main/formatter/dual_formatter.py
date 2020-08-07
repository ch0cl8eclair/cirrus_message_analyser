import logging
from logging.config import fileConfig
from urllib.parse import urlparse

from main.config.configuration import LOGGING_CONFIG_FILE
from main.config.constants import DataType, OUTPUT, OutputFormat, MESSAGE_ID, HOST_LOG_CORRELATION_ID, \
    LOG_STATEMENT_FOUND, LOG_LINE_STATS, HOST_LOG_MAPPINGS, FILE, CSV, JSON
from main.utils.utils import convert_output_option_to_enum

fileConfig(LOGGING_CONFIG_FILE)
logger = logging.getLogger('main')
message_logger = logging.getLogger('message')


def make_safe_for_filename(tracking_point):
    return tracking_point.replace(' ', '_')


class LogAndFileFormatter:
    def __init__(self, formatter, file_generator, proxy):
        self.formatter = formatter
        self.file_generator = file_generator
        self.cirrus_proxy = proxy

    def _format_to_log_and_file(self, message_uid, data_type, data, options):
        if data:
            self.formatter.format(data_type, data, options)
            data_records_for_output = self.formatter.get_processed_data_for_file_output(data, data_type, options)
            output_format = convert_output_option_to_enum(options)
            self.file_generator.output_logging_to_file(message_uid, data_type, data_records_for_output, output_format)
        
    def format_message_model(self, message_model, options):
        if message_model:
            message_uid = message_model.message_uid
            if message_model.has_status:
                self._add_log_message_heading("\nMessage summary:", options)
                data = [message_model.status_dict]
                data_type = DataType.cirrus_messages
                self._format_to_log_and_file(message_uid, data_type, data, options)

            if message_model.has_message_details:
                self._add_log_message_heading("\nMessage summary:", options)
                data = [message_model.message_details]
                data_type = DataType.cirrus_messages
                self._format_to_log_and_file(message_uid, data_type, data, options)
                
            if message_model.has_events:
                self._add_log_message_heading("\nMessage events:", options)
                data = message_model.events_list
                data_type = DataType.cirrus_events
                self._format_to_log_and_file(message_uid, data_type, data, options)

            if message_model.has_payloads:
                self._add_log_message_heading("\nMessage payloads:", options)
                data = message_model.payloads_list
                data_type = DataType.cirrus_payloads
                self._format_to_log_and_file(message_uid, data_type, data, options)
                # Write the payloads out to individual files
                self.download_payload_files(message_uid, data)

            if message_model.has_metadata:
                self._add_log_message_heading("\nMessage metadata:", options)
                data = message_model.metadata_list
                data_type = DataType.cirrus_metadata
                self._format_to_log_and_file(message_uid, data_type, data, options)
                
            if message_model.has_transforms:
                self._add_log_message_heading("\nMessage transforms:", options)
                data = message_model.transforms_list
                data_type = DataType.cirrus_transforms
                self._format_to_log_and_file(message_uid, data_type, data, options)
                
                self._add_log_message_heading("\nMessage transform steps:", options)
                data = self.format_transform_sub_lists(message_model.transforms_list, options)
                data_type = DataType.cirrus_transforms_steps
                self._format_to_log_and_file(message_uid, data_type, data, options)

            if message_model.has_rule:
                self._add_log_message_heading("\nMessage rule:", options)
                data = [message_model.rule]
                data_type = DataType.config_rule
                self._format_to_log_and_file(message_uid, data_type, data, options)
                
            if message_model.has_search_criteria:
                pass
            
            if message_model.has_payload_transform_mappings:
                self._add_log_message_heading("\nMessage payload to transform mappings:", options)
                data = message_model.payload_transform_mappings
                data_type = DataType.payload_transform_mappings
                self._format_to_log_and_file(message_uid, data_type, data, options)

                # Obtain xsl urls from data and have each downloaded and save to file
                xsl_urls_list = [item ["url"] for item in data if "url" in item]
                self._download_xsl_files(message_uid, xsl_urls_list)
                
            if message_model.has_server_location:
                if message_model.server_location_dict:
                    server_data_uid = message_model.server_location_dict.get(MESSAGE_ID, '')
                    if message_uid != server_data_uid:
                        logger.error("We have a message uid mismatch between: {} & {}".format(message_uid, server_data_uid))
                    host_log_correlation_ids = message_model.server_location_dict.get(HOST_LOG_CORRELATION_ID, '')
                    has_log_uid_statements = bool(message_model.server_location_dict.get(LOG_STATEMENT_FOUND, 'False'))
                    if has_log_uid_statements:
                        log_level_counts = message_model.server_location_dict[LOG_LINE_STATS]
                        if HOST_LOG_MAPPINGS in message_model.server_location_dict:
                            self._add_log_message_heading("\nServer location(s) found on elasticsearch server for message uid: {}:".format(message_uid), options)
                            enriched_log_summary_data = self.file_generator.enrich_log_summary_data(host_log_correlation_ids, message_model.server_location_dict[HOST_LOG_MAPPINGS], log_level_counts)
                            self._format_to_log_and_file(message_uid, DataType.host_log_mappings, enriched_log_summary_data, options)
                    else:
                        message_logger.info("\nNo server logs found on elasticsearch server")

    def _add_log_message_heading(self, message, options):
        if options.get(OUTPUT, CSV) != FILE:
            message_logger.info(message)

    def format_transform_sub_lists(self, transform_data, options):
        # We don't need to do this for JSON output
        if options.get(OUTPUT) == JSON:
            return None
        all_records = []
        for current_transform in transform_data:
            parent_prefix_dict = { parent_key: current_transform.get(parent_key) for parent_key in ["transform-name", "transform-channel"] }
            if "transform-steps" in current_transform and current_transform["transform-steps"]:
                updates_transform_data = [ dict(parent_prefix_dict, **record) for record in current_transform["transform-steps"] ]
                all_records.extend(updates_transform_data)
        return all_records

    def _download_xsl_files(self, message_uid, xsl_urls_list):
        """Downloads each xsl file from the given list to the output folder"""
        for url in xsl_urls_list:
            logger.debug("Fetching xsl file: {}".format(url))
            # Check for invalid characters
            if self.has_invalid_url_character(url):
                continue
            xsl_data = self.cirrus_proxy.get(url)
            # generate filename within output folder
            parsed_link = urlparse(url)
            base_filename = parsed_link.path.split('/')[-1]
            if base_filename and base_filename.endswith(".xsl"):
                self.file_generator.output_text_to_file(message_uid, base_filename, xsl_data)
            else:
                logger.error("Unable to download url to file as file name is invalid: [{}]".format(base_filename))

    def download_payload_files(self, message_uid, data):
        """Writes each of the payload data items to file"""
        for payload_item in data:
            tracking_point = payload_item["tracking-point"]
            payload_id = payload_item["id"]
            payload_data = payload_item["payload"]
            filtered_tracking_point = make_safe_for_filename(tracking_point)
            filename = f"payload-{filtered_tracking_point}-{payload_id}.dat"
            self.file_generator.output_text_to_file(message_uid, filename, payload_data)

    def has_invalid_url_character(self, url):
        for invalid_char in ["{", "}"]:
            if invalid_char in url:
                logger.error("Warning the following url contains invalid characters, unable to download: {}".format(url))
                return True
        return False
