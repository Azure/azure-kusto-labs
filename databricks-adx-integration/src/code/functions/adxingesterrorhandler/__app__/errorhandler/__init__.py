"""
  [Microsoft Kusto Lab Project]

  1. This code is based on Azure Functions Python Runtime.
  2. It will be triggered by Azure Storage Queue.
  3. When it been triggered, it will parse the trigger information and try to re-ingest to ADX
     by moving file to retry folder for re-triggering processing pipelines.
"""

from datetime import date
from typing import Tuple
import json
import logging
import os
import re
import sys
import time
import requests

from applicationinsights import TelemetryClient
from azure.storage.blob import BlobClient, BlobServiceClient
from tenacity import wait_exponential, stop_after_attempt, wait_random, Retrying
import azure.functions as func

# Required func app configuration
AZURE_STORAGE_CONNECTION_STRING = ''
APP_INSIGHT_KEY = ''
APP_INSIGHT_APP_ID = ''
APP_INSIGHT_APP_KEY = ''

RETRY_EVENT_NAME = 'ADX_INGEST_RETRY'
RETRY_END_IN_FAIL_EVENT_NAME = 'ADX_INGEST_RETRY_END_IN_FAIL'
MAX_INGEST_RETRIES_TIMES = 3
RETRY_END_IN_FAIL_CONTAINER_NAME = 'adx-ingest-retry-end-in-fail'
BLOB_REQ_MAX_ATTEMPT = 3
BLOB_REQ_MAX_RETRY_DELAY_SEC = 60
APP_INSIGHT_QUERY_URL = 'https://api.applicationinsights.io/v1/apps/{app_id}/query'

# # uncomment this for local debugging
# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s",
#     handlers=[
#         logging.StreamHandler()
#     ]
# )

def get_config_values() -> None:
    """ Get Config setting from predefined varialbes or environment parameters. """
    global APP_INSIGHT_KEY, RETRY_EVENT_NAME, RETRY_END_IN_FAIL_EVENT_NAME, AZURE_STORAGE_CONNECTION_STRING
    global MAX_INGEST_RETRIES_TIMES, RETRY_END_IN_FAIL_CONTAINER_NAME
    global BLOB_REQ_MAX_ATTEMPT, BLOB_REQ_MAX_RETRY_DELAY_SEC
    global APP_INSIGHT_APP_ID, APP_INSIGHT_APP_KEY, APP_INSIGHT_QUERY_URL

    RETRY_END_IN_FAIL_EVENT_NAME = os.getenv("RETRY_END_IN_FAIL_EVENT_NAME", RETRY_END_IN_FAIL_EVENT_NAME)
    RETRY_EVENT_NAME = os.getenv("RETRY_EVENT_NAME", RETRY_EVENT_NAME)
    MAX_INGEST_RETRIES_TIMES = int(os.getenv("MAX_INGEST_RETRIES_TIMES", str(MAX_INGEST_RETRIES_TIMES)))
    APP_INSIGHT_KEY = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", APP_INSIGHT_KEY)
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", AZURE_STORAGE_CONNECTION_STRING)
    RETRY_END_IN_FAIL_CONTAINER_NAME = os.getenv("RETRY_END_IN_FAIL_CONTAINER_NAME", RETRY_END_IN_FAIL_CONTAINER_NAME)
    BLOB_REQ_MAX_ATTEMPT = int(os.getenv("BLOB_REQ_MAX_ATTEMPT", str(BLOB_REQ_MAX_ATTEMPT)))
    BLOB_REQ_MAX_RETRY_DELAY_SEC = int(os.getenv("BLOB_REQ_MAX_RETRY_DELAY_SEC", str(BLOB_REQ_MAX_RETRY_DELAY_SEC)))
    APP_INSIGHT_APP_ID = os.environ.get('APP_INSIGHT_APP_ID', APP_INSIGHT_APP_ID)
    APP_INSIGHT_APP_KEY = os.environ.get('APP_INSIGHT_APP_KEY', APP_INSIGHT_APP_KEY)
    APP_INSIGHT_QUERY_URL = os.environ.get('APP_INSIGHT_QUERY_URL', APP_INSIGHT_QUERY_URL)

def get_blob_retry_times(blob_path: str) -> int:
    """ Get the ingest trial count for a given blob path """
    retry_times = 0
    pattern = r'retry(\d+)'
    match = re.compile(pattern).search(blob_path)
    retry_times = int(match.group(1)) if match else retry_times
    return retry_times

def move_blob_file(connect_str: str, source_container: str, target_container: str,
                   source_path: str, target_path: str) -> None:
    """ Move blob from source to destination container """
    logging.info('Move blob from %s/%s to %s/%s',
                 source_container, source_path, target_container, target_path)
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_source_client = blob_service_client.get_blob_client(container=source_container, blob=source_path)
    blob_target_client = blob_service_client.get_blob_client(container=target_container, blob=target_path)
    blob_target_client.start_copy_from_url(blob_source_client.url)
    blob_source_client.delete_blob()

def retry_blob_ingest_to_adx(container_name: str, blob_file_path: str,
                             new_container_name: str, new_blob_file_path: str) -> None:
    """ Re-trigger the ingest pipeline by moving blob to retry folder """

    # Add a random retry delay plus exponential backoff to mitigate the concurrent access to Azure
    retryer = Retrying(stop=stop_after_attempt(BLOB_REQ_MAX_ATTEMPT),
                       wait=wait_random(0, 5) + wait_exponential(multiplier=1, min=2,
                                                                 max=BLOB_REQ_MAX_RETRY_DELAY_SEC),
                       reraise=True)
    retryer(move_blob_file, AZURE_STORAGE_CONNECTION_STRING, container_name, new_container_name,
            blob_file_path, new_blob_file_path)

def get_new_blob_move_file_path(blob_container: str, blob_file_path: str, no_retry: bool = False) -> Tuple[str, str]:
    """ Get the new blob move container and path depends on current trigger blob path """
    retry_times = get_blob_retry_times(blob_file_path)
    retry_folder_pattern = 'retry{}/'
    new_blob_move_tuple = ()
    if no_retry:
        # case no-retry: <folder path>/<filename> -> <folder path>/<filename> in retryEndInFail container
        new_blob_move_tuple = RETRY_END_IN_FAIL_CONTAINER_NAME, blob_file_path
    elif retry_times == 0 or "retry" not in blob_file_path:
        # case retry: <folder path>/<filename> -> <folder path>/retryx/<filename> in same container
        split_path = blob_file_path.rsplit('/', 1)
        new_path = '/retry1/'.join(split_path) if len(split_path) > 1 else 'retry1/' + blob_file_path
        new_blob_move_tuple = blob_container, new_path
    elif retry_times >= MAX_INGEST_RETRIES_TIMES:
        # case retry-end-fail: <folder path>/retryX/<filename> -> <folder path>/<filename>
        # in retryEndInFail container
        new_path = blob_file_path.replace(retry_folder_pattern.format(retry_times), '')
        new_blob_move_tuple = RETRY_END_IN_FAIL_CONTAINER_NAME, new_path
    else:
        # case keep-retry: update the retry<retry_times> to retry<retry_times+1> in same container
        new_path = blob_file_path.replace(retry_folder_pattern.format(retry_times),
                                          retry_folder_pattern.format(retry_times + 1))
        new_blob_move_tuple = blob_container, new_path

    return new_blob_move_tuple

def get_blob_info_from_url(url: str) -> Tuple[str, str]:
    """ Get blob info from blob url string """
    temp_blob_client = BlobClient.from_blob_url(blob_url=url)
    return temp_blob_client.container_name, temp_blob_client.blob_name

def main(msg: func.QueueMessage) -> None:
    """
    Main function, triggered by Azure Storage Queue, parsed queue content
    :param msg: func.QueueMessage
    :return: None
    """
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    get_config_values()

    # Get blob file content
    content = json.loads(msg.get_body().decode('utf-8'))
    filepath = content['data']['url']

    container_name, blob_file_path = get_blob_info_from_url(filepath)
    dest_container_name, dest_blob_file_path = get_new_blob_move_file_path(container_name, blob_file_path)
    retry_times = get_blob_retry_times(filepath)
    retry_times += 1

    # Initialize Track Event/Metrics to App insight
    tc = TelemetryClient(APP_INSIGHT_KEY)
    tc.context.application.ver = '1.0'
    tc.context.properties["PROCESS_PROGRAM"] = "XDR_SDL_INGESTION_ERR_HANDLER_V01A"
    tc.context.properties["PROCESS_START"] = time.time()

    # Do retry (move file to retry folder)
    # TODO: Should filter out the non-retry case
    logging.info("Retry the blob ingest to ADX, blob_path: %s", filepath)
    retry_blob_ingest_to_adx(container_name, blob_file_path, dest_container_name, dest_blob_file_path)

    if retry_times > MAX_INGEST_RETRIES_TIMES:
        logging.error("Retry blob ingest to ADX hit the retries limit %s, blob_path: %s",
                      MAX_INGEST_RETRIES_TIMES, filepath)
        tc.track_event(RETRY_END_IN_FAIL_EVENT_NAME,
                       {'FILE_PATH': filepath},
                       {RETRY_END_IN_FAIL_EVENT_NAME + '_COUNT': 1})
        tc.flush()
        return

    tc.track_event(RETRY_EVENT_NAME,
                   {'FILE_PATH': filepath},
                   {RETRY_EVENT_NAME + '_COUNT': 1})
    tc.flush()

    logging.info("ADX error handler execution succeeded, blob path: %s, trial count: %s",
                 filepath, retry_times)
