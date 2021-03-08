"""
  [Microsoft Kusto Lab Project]

  1. This code is based on Azure Functions Python Runtime.
  2. It will be triggered by Azure Storage Queue
  3. It will parse the trigger information, get the event time and metadata file path.
  4. Get the metadata blob file content.
  5. Enqueue sucecessful processed blob file path for downstream processing 
  6. Shrink Spark checkpoint compact files size to prevent it keeps growing and impact system performace 
"""
from contextlib import contextmanager
from typing import Tuple
from typing import List
import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
import tempfile

import azure.functions as func
from applicationinsights import TelemetryClient
from azure.storage.queue.aio import QueueClient
from azure.storage.blob import BlobServiceClient, BlobClient

# Required func app configuration
APPINSIGHTS_INSTRUMENTATIONKEY = None
DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL = None
DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN = None
ADX_INGEST_QUEUE_URL_LIST = ''
ADX_INGEST_QUEUE_SAS_TOKEN = None
METADATA_HANDLE_EVENT_NAME = 'METADATA_HANDLE'
CONCURRENT_ENQUEUE_TASKS = '20'
MAX_COMPACT_FILE_RECORDS = 0  # The max file records number in compact file

# CONFIG FOR LOG MESSAGE
HEADER = "[Databricks Meatadata Handler]"
PROCESS_PROGRAM_NAME = "KUSTO_LAB_METADATA_HANDLER_SAMPLE"

BLOB_SERVICE_CLIENT = None

INGEST_QUEUE_MSG_TEMPLATE = """
{{
    "data": {{
        "api": "PutBlockList",
        "contentLength": {blob_size},
        "url": "{blob_url}"
    }},
    "eventTime": "{event_time}",
    "modificationTime": "{modification_time}"
}}
"""

def is_json(json_str: str) -> bool:
    """ Check whether the input string is a valid JSON """
    try:
        json.loads(json_str)
    except ValueError:
        return False
    return True

def init_config_values():
    """
    Get Config setting from predefined variables or environment parameters.
    :return: None
    """
    global HEADER, PROCESS_PROGRAM_NAME, METADATA_HANDLE_EVENT_NAME
    global APPINSIGHTS_INSTRUMENTATIONKEY
    global DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL, DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN
    global ADX_INGEST_QUEUE_URL_LIST, ADX_INGEST_QUEUE_SAS_TOKEN
    global CONCURRENT_ENQUEUE_TASKS
    global MAX_COMPACT_FILE_RECORDS
    APPINSIGHTS_INSTRUMENTATIONKEY = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY",
                                               APPINSIGHTS_INSTRUMENTATIONKEY)
    DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL = os.getenv("DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL",
                                                      DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL)
    DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN = os.getenv("DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN",
                                                    DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN)
    ADX_INGEST_QUEUE_URL_LIST = os.getenv("ADX_INGEST_QUEUE_URL_LIST", ADX_INGEST_QUEUE_URL_LIST)
    ADX_INGEST_QUEUE_SAS_TOKEN = os.getenv("ADX_INGEST_QUEUE_SAS_TOKEN", ADX_INGEST_QUEUE_SAS_TOKEN)
    CONCURRENT_ENQUEUE_TASKS = int(os.getenv("CONCURRENT_ENQUEUE_TASKS", CONCURRENT_ENQUEUE_TASKS))
    ADX_INGEST_QUEUE_URL_LIST = ADX_INGEST_QUEUE_URL_LIST.replace(' ', '').split(',')
    logging.info(f"ADX_INGEST_QUEUE_URL_LIST: {ADX_INGEST_QUEUE_URL_LIST}")


    HEADER = os.getenv("LOG_MESSAGE_HEADER", HEADER)
    PROCESS_PROGRAM_NAME = os.getenv("PROCESS_PROGRAM_NAME", PROCESS_PROGRAM_NAME)
    METADATA_HANDLE_EVENT_NAME = os.getenv("METADATA_HANDLE_EVENT_NAME", METADATA_HANDLE_EVENT_NAME)
    MAX_COMPACT_FILE_RECORDS = int(os.getenv("MAX_COMPACT_FILE_RECORDS", str(MAX_COMPACT_FILE_RECORDS)))

def get_blob_content(container_name: str, blob_path: str) -> str:
    """ download blob file content as string
    """
    global BLOB_SERVICE_CLIENT
    # TODO: Should add retry policy here
    if not BLOB_SERVICE_CLIENT:
        logging.info(
            f"{HEADER} Initialize blob service client for {DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL}")
        BLOB_SERVICE_CLIENT = BlobServiceClient(DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL,
                                                credential=DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN)
    blob_client = BLOB_SERVICE_CLIENT.get_blob_client(container=container_name, blob=blob_path)
    content = blob_client.download_blob().content_as_text()
    return content

def get_shrinked_checkpoint_content(content, lines_to_keep)->str:
    """Shrink (reduce size) checkpoint files size"""
    i = 0
    original_lines = content.splitlines()
    newlines = []
    for line in reversed(original_lines):
        if i < lines_to_keep:
            newlines.append(line)
            i += 1
        else:
            break   #reached max lines to keep

    if len(newlines) < len(original_lines):
        newlines.append(original_lines[0]) # Add header line

    new_content = "\n".join(reversed(newlines))
    return new_content

def update_blob_content(container_name: str, blob_path: str, content: str):
    """ update blob file by replace existing file     """

    global BLOB_SERVICE_CLIENT

    if not BLOB_SERVICE_CLIENT:
        logging.info(
            f"{HEADER} Initialize blob service client for {DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL}")
        BLOB_SERVICE_CLIENT = BlobServiceClient(DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL,
                                                credential=DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN)
    blob_client = BLOB_SERVICE_CLIENT.get_blob_client(container=container_name, blob=blob_path)

    local_path = tempfile.gettempdir()
    local_file_name = "temp_checkpoint_" + str(uuid.uuid4()) + ".txt"
    upload_file_path = os.path.join(local_path, local_file_name)

    # Write text to the file
    file = open(upload_file_path, 'w')
    file.write(content)
    file.close()

    # Upload the created file
    with open(upload_file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)


def get_queue_client(url: str) -> QueueClient:
    """ Initialize queue client
    """
    queue_client_dict = dict()
    if not queue_client_dict.get(url):
        client = QueueClient.from_queue_url(url, credential=ADX_INGEST_QUEUE_SAS_TOKEN)
        queue_client_dict[url] = client
        logging.info(f"{HEADER} Initialize Queue Client for {url}")
    return queue_client_dict[url]

def convert_abfss_path_to_https(abfss_path: str) -> str:
    """ Convert the abfss path to https path style """
    pattern = r'abfss:\/\/([^@]+)@([^.]+)[^\/]+\/(.+)'
    regex = re.compile(pattern)
    match = regex.search(abfss_path)
    if not match:
        raise ValueError(f"Invalid abfss path {abfss_path}")
    container = match.group(1)
    storage_account = match.group(2)
    filepath = match.group(3)
    https_path = f"https://{storage_account}.blob.core.windows.net/{container}/{filepath}"
    return https_path


def get_part_number(content) ->int:
    """Find part number"""
    pindex = content.find('part-')
    pnum = -1
    if pindex > 0:
        pnum = int(content[pindex+5:pindex+10])
    return pnum


def generate_metadata_queue_messages(event_time: str, metadata_file_content: str) -> List[str]:
    """ Generate queue messages from Databricks ouutput metadata file content """
    ingest_queue_msg_list = []
    current_part_num = 100000 #Max part number
    global MAX_COMPACT_FILE_RECORDS

    for line in reversed(metadata_file_content.splitlines()):
        logging.info(f"{HEADER} Processing metadata line content: {line}")
        if not is_json(line):
            logging.info(f"{HEADER} Skip non JSON line content: {line}")
            continue

        pnum = get_part_number(line)

        if pnum > current_part_num:
            break   # Reached files in previous batch, stop parsing

        current_part_num = pnum

        split_output_file_json = json.loads(line)
        output_abfss_path = split_output_file_json["path"]
        output_file_size = split_output_file_json["size"]
        output_file_modification_time = split_output_file_json["modificationTime"]

        try:
            https_url = convert_abfss_path_to_https(output_abfss_path)
        except Exception: # pylint: disable=bare-except
            logging.warning(f"{HEADER} Skip invalid abfss path {output_abfss_path}", exc_info=True)
            continue

        queue_msg = INGEST_QUEUE_MSG_TEMPLATE.format(blob_size=output_file_size,
                                                     blob_url=https_url,
                                                     event_time=event_time,
                                                     modification_time=output_file_modification_time)
        minify_msg = json.dumps(json.loads(queue_msg))
        ingest_queue_msg_list.append(minify_msg)

    MAX_COMPACT_FILE_RECORDS = max(len(ingest_queue_msg_list), MAX_COMPACT_FILE_RECORDS)
    return ingest_queue_msg_list



async def send_queue_messages(queue_client, base64_message, queue_msg):
    """ Async to send messages to storage queue """
    try:
        await queue_client.send_message(base64_message)
    except Exception: # pylint: disable=bare-except
        logging.exception(f"{HEADER} Failed to send message {queue_msg} to queue")
        # Raise exception to let azure function retry whole batch again
        raise

def gen_metadata_msg_enqueue_tasks(queue_msg_list: List[str],
                                   queue_client_list: List[QueueClient],
                                   tc: TelemetryClient) -> None:
    """ Send queue messages to target queues """

    tasks = []
    for idx, queue_msg in enumerate(queue_msg_list):
        output_obj = json.loads(queue_msg)

        queue_index = idx % len(queue_client_list)
        logging.debug(
            f"{HEADER} Try to send message to ingest queue {queue_index}, queue_msg: {queue_msg}")

        base64_message = base64.b64encode(queue_msg.encode('ascii')).decode('ascii')

        file_url = output_obj['data']['url']
        size = int(output_obj['data']['contentLength'])

        tc.track_event(METADATA_HANDLE_EVENT_NAME,
                       {'FILE_URL': file_url},
                       {METADATA_HANDLE_EVENT_NAME + '_SIZE': size,
                        METADATA_HANDLE_EVENT_NAME + '_COUNT': 1})

        # round robin to enqueue message
        task = asyncio.ensure_future(send_queue_messages(
            queue_client_list[queue_index], base64_message, queue_msg))
        tasks.append(task)
    tc.flush()
    return tasks

async def gather_with_concurrency(n, tasks):
    """ limit the concurrent tasks with semaphore """
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            await task
    await asyncio.gather(*(sem_task(task) for task in tasks))

def close_queue_clients(queue_client_list: List[QueueClient], loop: asyncio.AbstractEventLoop):
    """ Close queue clients connection """
    client_close_tasks = []
    for client in queue_client_list:
        close_task = asyncio.ensure_future(client.close())
        client_close_tasks.append(close_task)
    loop.run_until_complete(gather_with_concurrency(1, client_close_tasks))

def main(msg: func.QueueMessage) -> None:
    """
    Main function, triggered by Azure Storage Queue, parsed queue content and
    try to download the databricks output metadata file to get each succefully processed file location.
    Then enqueue to ingest queue for ingestion to ADX on later Azure function.
    If the file is checkpoint compact file, the code will shrink the file size.
    :param msg: func.QueueMessage
    :return: None
    """
    code_start_time = time.time()
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    # modify the log level of azure sdk requests
    logging.getLogger('azure').setLevel(logging.WARNING)
    init_config_values()

    tc = TelemetryClient(APPINSIGHTS_INSTRUMENTATIONKEY)
    tc.context.application.ver = '1.0'
    tc.context.properties["PROCESS_PROGRAM"] = PROCESS_PROGRAM_NAME
    tc.context.properties["PROCESS_START"] = time.time()

    # 1. Get trigger file content (rename event)
    content_json = json.loads(msg.get_body().decode('utf-8'))

    logging.info("meta-data event content: {}".format(msg.get_body().decode('utf-8')))
    file_url = content_json['data']['destinationUrl']
    logging.info(f"file_url: {file_url}")
    event_time = content_json['eventTime']

    # 2. Download metadata blob content
    logging.info(f"{HEADER} Download blob file from {file_url}")
    temp_blob_client = BlobClient.from_blob_url(blob_url=file_url, logging_enable=False)
    blob_path = temp_blob_client.blob_name
    container_name = temp_blob_client.container_name

    try:
        metadata_file_content = get_blob_content(container_name, blob_path)
    except Exception:
        logging.exception(f"Failed to download blob from url {file_url}")
        raise

    # 3. Parse split output file from the metadata
    queue_msg_list = generate_metadata_queue_messages(event_time, metadata_file_content)
    logging.info(
        f"{HEADER} Generate metadata queue_messages from {file_url}, {len(queue_msg_list)} messages")

    # 4. Loop to enqueue msg to ADX ingest queue
    queue_client_list = []
    for q_url in ADX_INGEST_QUEUE_URL_LIST:
        queue_client = get_queue_client(q_url)
        queue_client_list.append(queue_client)

    asyncio.set_event_loop(asyncio.new_event_loop())
    loop = asyncio.get_event_loop()
    tasks = gen_metadata_msg_enqueue_tasks(queue_msg_list, queue_client_list, tc)
    loop.run_until_complete(gather_with_concurrency(CONCURRENT_ENQUEUE_TASKS, tasks))
    close_queue_clients(queue_client_list, loop)
    loop.close()

    logging.info(f"{HEADER} Done queuing up messages to Ingestion queue")

    if file_url.endswith(".compact"): # reduce compact file size
        update_blob_content(container_name,
                            blob_path,
                            get_shrinked_checkpoint_content(
                                metadata_file_content, MAX_COMPACT_FILE_RECORDS))
        logging.info(f"{HEADER} Reduced checkpoint files {file_url}, max lines is {MAX_COMPACT_FILE_RECORDS}")

    code_duration = time.time() - code_start_time
    tc.track_event(METADATA_HANDLE_EVENT_NAME,
                   {'FILE_URL': file_url},
                   {METADATA_HANDLE_EVENT_NAME + '_DURATION_SEC': code_duration})
    tc.flush()
