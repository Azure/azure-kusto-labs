"""
  [Microsoft Kusto Lab Project]

  1. This code is based on Azure Functions Python Runtime.
  2. It will be triggered by Azure Storage Queue
  3. When it been triggered, it will parse the trigger information
"""
import json
import logging
import time
import os
import re

import azure.functions as func
from applicationinsights import TelemetryClient
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

AZURE_STORAGE_CONNECTION_STRING = 'AZURE_STORAGE_CONNECTION_STRING'
APPINSIGHTS_INSTRUMENTATIONKEY = 'APPINSIGHTS_INSTRUMENTATIONKEY'
RETRY_ERROR_EVENT_NAME = 'DATABRICKS_SPLIT_RETRY_ERROR'
RETRY_END_IN_FAIL_EVENT_NAME = 'DATABRICKS_SPLIT_RETRY_END_IN_FAIL'
RETRY_EVENT_NAME = 'DATABRICKS_SPLIT_RETRY'

Key_Word_bad_records = ['bad_records']
RetryFail_Container_Name = 'final-retry-failed'
MAX_INGEST_RETRIES_TIMES = 3
CONNECT_STR = ''
APP_INSIGHT_KEY = ''


def get_config_values() -> None:
    """ Get Config setting from predefined varialbes or environment parameters. """
    global RETRY_END_IN_FAIL_EVENT_NAME, APPINSIGHTS_INSTRUMENTATIONKEY, AZURE_STORAGE_CONNECTION_STRING
    global RETRY_ERROR_EVENT_NAME, RETRY_EVENT_NAME, Key_Word_bad_records, RetryFail_Container_Name
    global MAX_INGEST_RETRIES_TIMES, CONNECT_STR, APP_INSIGHT_KEY

    # Get blob file content
    CONNECT_STR = os.getenv(AZURE_STORAGE_CONNECTION_STRING)
    APP_INSIGHT_KEY = os.getenv(APPINSIGHTS_INSTRUMENTATIONKEY)


def get_blob_retry_times(blob_path: str) -> int:
    """ Get the ingest trial count for a given blob path """
    retry_times = 0
    pattern = r'retry(\d+)'
    match = re.compile(pattern).search(blob_path)
    retry_times = int(match.group(1)) if match else retry_times
    return retry_times


def get_new_blob_move_file_path(blob_file_path: str, no_retry: bool = False):
    """ Get the new blob move path depends on current trigger blob path """
    retry_times = get_blob_retry_times(blob_file_path)
    patharray = blob_file_path.split("/")
    filename = patharray[len(patharray)-1].split(".")[0]
    if no_retry:
        return blob_file_path
    if retry_times == 0 or "retry" not in blob_file_path:
        # case retry: <folder path>/<filename> -> <folder
        # path>/retryx/<filename>
        blob_file_path = "/".join(patharray[:-1]) + \
            "/" + filename + "/" + get_new_file_name()
        return '/retry1/'.join(blob_file_path.rsplit('/', 1))
    if retry_times >= MAX_INGEST_RETRIES_TIMES:
        # case retry-end-fail: <folder path>/retryX/<filename> ->
        # retryEndInFail/<folder path>/<filename>
        new_path = blob_file_path.replace('/retry{}/'.format(retry_times), '/')
        return new_path

    blob_file_path = "/".join(blob_file_path.split("/")
                              [:-1]) + "/" + get_new_file_name()
    # case keep-retry: update the retry<retry_times> to
    # retry<retry_times+1>
    return blob_file_path.replace(
        '/retry{}/'.format(retry_times), '/retry{}/'.format(retry_times + 1))


def get_new_file_name() -> str:
    """ get a file name by timestamp """
    timestamp = time.time()
    return str(timestamp).replace('.', '_') + ".json.gz"


def retry_blob_databireck_split(
        connect_str: str,
        source_container: str,
        target_container: str,
        source_path: str,
        target_path: str) -> None:
    """ Move blob from source to destination container """
    # TODO: Should add try catch here
    # TODO: Should add retry here, upload may failed occasionaly
    # TODO: Blob file may be absent, should handle this case
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_source_client = blob_service_client.get_blob_client(
        container=source_container, blob=source_path)
    blob_target_client = blob_service_client.get_blob_client(
        container=target_container, blob=target_path)
    blob_target_client.start_copy_from_url(blob_source_client.url)
    blob_source_client.delete_blob()


def download_logfile(
        container_name: str,
        local_file_name: str) -> str:
    """ download data bricks log file as string """
    blob_service_client = BlobServiceClient.from_connection_string(CONNECT_STR)
    blob_client = blob_service_client.get_blob_client(
        container=container_name, blob=local_file_name)
    log_file_str = blob_client.download_blob().content_as_text()
    return log_file_str


def check_retry_necessary(
        file_path: str) -> bool:
    """ Decide whether to retry based on the contents of the array list """
    for bad_record in Key_Word_bad_records:
        if file_path.find(bad_record) >= 0:
            return False
    return True


def main(msg: func.QueueMessage) -> None:
    """
    Main function, triggered by Azure Storage Queue, parsed queue content
    :param msg: func.QueueMessage
    :return: None
    """
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    # Get blob file content
    file_path = json.loads(msg.get_body().decode('utf-8'))['data']['url']

    # Parsing rows to get blob location and failure reason
    temp_blob_client = BlobClient.from_blob_url(blob_url=file_path)
    local_file_name = temp_blob_client.blob_name
    container_name = temp_blob_client.container_name

    get_config_values()

    log_file_str = download_logfile(
        container_name=container_name, local_file_name=local_file_name)

    for line in log_file_str.splitlines():
        log_file_json = json.loads(line)
        path = log_file_json["path"]
        reason = log_file_json["reason"]

        tc = TelemetryClient(APP_INSIGHT_KEY)
        tc.context.application.ver = '1.0'
        tc.context.properties["PROCESS_PROGRAM"] = "XDR_SDL_INGESTION_ERR_HANDLER_V01A"
        tc.context.properties["PROCESS_START"] = time.time()

        try:
            patharray = path.replace('abfss://', '').split('/')
            container = patharray[0].split('@')[0]
            patharray.remove(patharray[0])
            filepath = ''
            for item in patharray:
                filepath += '/'+item
            filepath = filepath[1:]
        except:  # pylint: disable=bare-except
            logging.error(
                "Retry blob Databricks split error handling log file format error, FilePath: %s",
                file_path)
            tc.track_event(RETRY_ERROR_EVENT_NAME,
                           {'FILE_PATH': file_path},
                           {RETRY_ERROR_EVENT_NAME + '_COUNT': 0})
            tc.flush()
            continue

        retry_times = get_blob_retry_times(filepath)

        # check retry is necessary or not
        if not check_retry_necessary(file_path=file_path):
            new_blob_file_path = get_new_blob_move_file_path(filepath, True)
            retry_blob_databireck_split(
                connect_str=CONNECT_STR,
                source_container=container,
                target_container=RetryFail_Container_Name,
                source_path=filepath,
                target_path=new_blob_file_path)
            logging.error(
                "Retry blob Databricks split hit the no need to retry, blob_path: %s, failure reason: %s",
                filepath,
                reason)
            tc.track_event(RETRY_END_IN_FAIL_EVENT_NAME,
                           {'FILE_PATH': filepath},
                           {RETRY_END_IN_FAIL_EVENT_NAME + '_COUNT': 0})
            tc.flush()
            continue

        if retry_times >= MAX_INGEST_RETRIES_TIMES:
            new_blob_file_path = get_new_blob_move_file_path(filepath)
            retry_blob_databireck_split(
                connect_str=CONNECT_STR,
                source_container=container,
                target_container=RetryFail_Container_Name,
                source_path=filepath,
                target_path=new_blob_file_path)
            logging.error(
                "Retry blob Databricks split hit the retries limit %s, blob_path: %s, failure reason: %s",
                MAX_INGEST_RETRIES_TIMES,
                filepath,
                reason)
            tc.track_event(
                RETRY_END_IN_FAIL_EVENT_NAME, {'FILE_PATH': filepath}, {
                    RETRY_END_IN_FAIL_EVENT_NAME + '_COUNT': 1})
            tc.flush()
            continue

        new_blob_file_path = get_new_blob_move_file_path(filepath)
        retry_blob_databireck_split(
            connect_str=CONNECT_STR,
            source_container=container,
            target_container=container,
            source_path=filepath,
            target_path=new_blob_file_path)

        logging.info(
            "Retry the Databricks split, blob_path: %s, failure reason: %s",
            path,
            reason)
        tc.track_event(RETRY_EVENT_NAME,
                       {'FILE_PATH': file_path},
                       {RETRY_EVENT_NAME + '_COUNT': 1})
        tc.flush()
        retry_times += 1
        logging.info(
            "Databricks error handler execution succeed, blob path: %s, trial count: %s",
            path,
            retry_times)
