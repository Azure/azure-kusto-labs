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

from .validation import (
    ValidationError,
    is_compact_checkpoint,
    parse_allow_list,
    redact_url,
    split_blob_url,
    storage_hosts_from_account_url,
    validate_blob_url_host,
    validate_checkpoint_path,
    validate_container_name,
    validate_output_path,
)

# Required func app configuration
APPINSIGHTS_INSTRUMENTATIONKEY = None
DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL = None
DATABRICKS_OUTPUT_STORAGE_SAS_TOKEN = None
ADX_INGEST_QUEUE_URL_LIST = ''
ADX_INGEST_QUEUE_SAS_TOKEN = None
METADATA_HANDLE_EVENT_NAME = 'METADATA_HANDLE'
CONCURRENT_ENQUEUE_TASKS = '20'
MAX_COMPACT_FILE_RECORDS = 0  # The max file records number in compact file

# The blobs this function is entitled to read and rewrite. A queue message names
# the checkpoint file to process, so the account, container, Databricks output
# directory and file name grammar are all pinned to what this deployment writes.
ALLOWED_STORAGE_HOSTS = set()
ALLOWED_METADATA_CONTAINERS = set()
METADATA_PATH_ROOT = ''
# Spark's structured streaming file sink always writes its checkpoint log to a
# directory of this name, so it is a safe default rather than a lab specific one.
METADATA_REQUIRED_SEGMENT = '_spark_metadata'

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
    global ALLOWED_STORAGE_HOSTS, ALLOWED_METADATA_CONTAINERS, METADATA_REQUIRED_SEGMENT
    global METADATA_PATH_ROOT
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
    logging.info("ADX_INGEST_QUEUE_URL_LIST: %s",
                 [redact_url(url) for url in ADX_INGEST_QUEUE_URL_LIST])


    HEADER = os.getenv("LOG_MESSAGE_HEADER", HEADER)
    PROCESS_PROGRAM_NAME = os.getenv("PROCESS_PROGRAM_NAME", PROCESS_PROGRAM_NAME)
    METADATA_HANDLE_EVENT_NAME = os.getenv("METADATA_HANDLE_EVENT_NAME", METADATA_HANDLE_EVENT_NAME)
    MAX_COMPACT_FILE_RECORDS = int(os.getenv("MAX_COMPACT_FILE_RECORDS", str(MAX_COMPACT_FILE_RECORDS)))

    # Bind this function to the storage account it is already configured against.
    # ALLOWED_STORAGE_HOSTS is an escape hatch for a custom domain in front of that
    # same account; the rest of this lab targets global Azure endpoints throughout.
    ALLOWED_STORAGE_HOSTS = storage_hosts_from_account_url(DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL)
    ALLOWED_STORAGE_HOSTS |= {host.lower() for host in parse_allow_list(os.getenv("ALLOWED_STORAGE_HOSTS"))}
    # The container and directory the Databricks job writes its output to. Naming
    # the account alone is not enough: without these, a queue message could still
    # select any other blob in the same account.
    ALLOWED_METADATA_CONTAINERS = parse_allow_list(os.getenv("ALLOWED_METADATA_CONTAINERS"))
    METADATA_PATH_ROOT = os.getenv("METADATA_PATH_ROOT", METADATA_PATH_ROOT)
    METADATA_REQUIRED_SEGMENT = os.getenv("METADATA_REQUIRED_SEGMENT", METADATA_REQUIRED_SEGMENT)

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
        logging.info(f"{HEADER} Initialize Queue Client for {redact_url(url)}")
    return queue_client_dict[url]

def convert_abfss_path_to_https(abfss_path: str) -> str:
    """ Convert the abfss path to https path style """
    # Anchored at both ends, so a crafted value cannot carry an accepted abfss
    # reference in the middle of some longer string.
    pattern = r'^abfss://([^@/]+)@([^./]+)\.dfs\.core\.windows\.net/(.+)$'
    regex = re.compile(pattern)
    match = regex.match(abfss_path)
    if not match:
        # !r escapes control characters, so a newline in this untrusted value
        # cannot forge extra records wherever this message is logged.
        raise ValueError('Invalid abfss path {!r}'.format(abfss_path))
    container = match.group(1)
    storage_account = match.group(2)
    filepath = match.group(3)
    https_path = f"https://{storage_account}.blob.core.windows.net/{container}/{filepath}"
    return https_path


def get_part_number(content) ->int:
    """Find part number"""
    pindex = content.find('part-')
    pnum = -1
    if pindex >= 0:
        try:
            pnum = int(content[pindex+5:pindex+10])
        except ValueError:
            # The checkpoint file is written upstream, so the characters after the
            # marker are not guaranteed to be digits. Report the same "no part
            # number" result as a name without the marker, and let the caller decide
            # what to do about it.
            pnum = -1
    return pnum


def generate_metadata_queue_messages(event_time: str, metadata_file_content: str) -> List[str]:
    """ Generate queue messages from Databricks ouutput metadata file content """
    ingest_queue_msg_list = []
    current_part_num = 100000 #Max part number
    global MAX_COMPACT_FILE_RECORDS

    lines = list(reversed(metadata_file_content.splitlines()))
    # How far into the file this batch reached. A line can be scanned without
    # producing a message, so counting messages here would let a skipped line take
    # the place of an accepted one when the compact file is later trimmed.
    batch_line_count = len(lines)
    for line_number, line in enumerate(lines):
        # The checkpoint file is produced upstream and is not trusted here, so its
        # content is identified by position rather than copied into the logs.
        logging.debug(f"{HEADER} Processing metadata line {line_number}")
        if not is_json(line):
            logging.debug(f"{HEADER} Skip non JSON metadata line {line_number}")
            continue

        try:
            split_output_file_json = json.loads(line)
            output_abfss_path = split_output_file_json["path"]
            output_file_size = split_output_file_json["size"]
            output_file_modification_time = split_output_file_json["modificationTime"]

            https_url = convert_abfss_path_to_https(output_abfss_path)
            # The metadata file content also selects a destination, for the ingest
            # function downstream. Confine those urls to the same account, container
            # and output directory rather than forwarding whatever the file contains.
            validate_blob_url_host(https_url, ALLOWED_STORAGE_HOSTS)
            referenced_container, referenced_path = split_blob_url(https_url)
            validate_container_name(referenced_container, ALLOWED_METADATA_CONTAINERS)
            validate_output_path(referenced_path, METADATA_PATH_ROOT)
        except Exception as exc: # pylint: disable=broad-except
            # The rejection messages quote the offending value with !r, so control
            # characters in this untrusted path arrive escaped rather than as real
            # line breaks. Keeping the reason makes a skipped file diagnosable.
            logging.warning("%s Skip metadata line %d: %s", HEADER, line_number, exc)
            continue

        # Batch order comes from the validated path, and only after the entry has
        # been accepted. An entry this function skips therefore cannot move the
        # ceiling below the batch and cut the scan short.
        pnum = get_part_number(referenced_path)

        if pnum > current_part_num:
            batch_line_count = line_number
            break   # Reached files in previous batch, stop parsing

        if pnum >= 0:
            # A name that carries no part number says nothing about batch order, so
            # it is forwarded on its own merit and leaves the ceiling where it is.
            current_part_num = pnum

        queue_msg = INGEST_QUEUE_MSG_TEMPLATE.format(blob_size=output_file_size,
                                                     blob_url=https_url,
                                                     event_time=event_time,
                                                     modification_time=output_file_modification_time)
        minify_msg = json.dumps(json.loads(queue_msg))
        ingest_queue_msg_list.append(minify_msg)

    MAX_COMPACT_FILE_RECORDS = max(batch_line_count, MAX_COMPACT_FILE_RECORDS)
    return ingest_queue_msg_list



async def send_queue_messages(queue_client, base64_message, queue_msg):
    """ Async to send messages to storage queue """
    try:
        await queue_client.send_message(base64_message)
    except Exception: # pylint: disable=bare-except
        # The message body embeds a blob url, which can carry a SAS token, so the
        # blob is identified by path only.
        failed_url = json.loads(queue_msg).get('data', {}).get('url')
        logging.exception(f"{HEADER} Failed to send message for {redact_url(failed_url)} to queue")
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
            f"{HEADER} Try to send message to ingest queue {queue_index}, "
            f"blob: {redact_url(output_obj['data']['url'])}")

        base64_message = base64.b64encode(queue_msg.encode('ascii')).decode('ascii')

        file_url = output_obj['data']['url']
        size = int(output_obj['data']['contentLength'])

        tc.track_event(METADATA_HANDLE_EVENT_NAME,
                       {'FILE_URL': redact_url(file_url)},
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
    # The queue body carries the blob url, which can include a SAS token, so the
    # message is identified rather than echoed into the logs.
    logging.info('Python queue trigger function processed a queue item: %s', msg.id)
    # modify the log level of azure sdk requests
    logging.getLogger('azure').setLevel(logging.WARNING)
    init_config_values()

    tc = TelemetryClient(APPINSIGHTS_INSTRUMENTATIONKEY)
    tc.context.application.ver = '1.0'
    tc.context.properties["PROCESS_PROGRAM"] = PROCESS_PROGRAM_NAME
    tc.context.properties["PROCESS_START"] = time.time()

    # 1. Get trigger file content (rename event)
    content_json = json.loads(msg.get_body().decode('utf-8'))

    file_url = content_json['data']['destinationUrl']
    logging.info(f"file_url: {redact_url(file_url)}")
    event_time = content_json['eventTime']

    # 2. Download metadata blob content
    logging.info(f"{HEADER} Download blob file from {redact_url(file_url)}")
    try:
        # Authorise the raw url before the sdk parses it, then validate what the
        # sdk resolved, since those resolved values are what reach the privileged
        # blob client built from DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL.
        validate_blob_url_host(file_url, ALLOWED_STORAGE_HOSTS)
        temp_blob_client = BlobClient.from_blob_url(blob_url=file_url, logging_enable=False)
        blob_path = validate_checkpoint_path(temp_blob_client.blob_name, METADATA_PATH_ROOT,
                                             METADATA_REQUIRED_SEGMENT)
        container_name = validate_container_name(temp_blob_client.container_name,
                                                 ALLOWED_METADATA_CONTAINERS)
    except ValidationError:
        # Surface the rejection explicitly. A message that fails validation is
        # worth its own log entry rather than being lost in a generic trace.
        logging.error("%s Rejected untrusted metadata blob url from queue message: %s",
                      HEADER, redact_url(file_url))
        raise

    try:
        metadata_file_content = get_blob_content(container_name, blob_path)
    except Exception:
        logging.exception(f"Failed to download blob from url {redact_url(file_url)}")
        raise

    # 3. Parse split output file from the metadata
    queue_msg_list = generate_metadata_queue_messages(event_time, metadata_file_content)
    logging.info(
        f"{HEADER} Generate metadata queue_messages from {redact_url(file_url)}, {len(queue_msg_list)} messages")

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

    if is_compact_checkpoint(blob_path): # reduce compact file size
        update_blob_content(container_name,
                            blob_path,
                            get_shrinked_checkpoint_content(
                                metadata_file_content, MAX_COMPACT_FILE_RECORDS))
        logging.info(f"{HEADER} Reduced checkpoint files {redact_url(file_url)}, max lines is {MAX_COMPACT_FILE_RECORDS}")

    code_duration = time.time() - code_start_time
    tc.track_event(METADATA_HANDLE_EVENT_NAME,
                   {'FILE_URL': redact_url(file_url)},
                   {METADATA_HANDLE_EVENT_NAME + '_DURATION_SEC': code_duration})
    tc.flush()
