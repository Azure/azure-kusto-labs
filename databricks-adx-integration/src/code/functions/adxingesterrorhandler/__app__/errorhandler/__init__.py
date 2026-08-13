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
from urllib.parse import unquote, urlparse

from applicationinsights import TelemetryClient
from azure.storage.blob import BlobServiceClient
from tenacity import wait_exponential, stop_after_attempt, wait_random, Retrying
import azure.functions as func

# Required func app configuration
AZURE_STORAGE_CONNECTION_STRING = ''
INGESTION_STORAGE_ACCOUNT_URL = ''
INGESTION_CONTAINER_NAME = ''
INGESTION_ROOT_PATH = ''
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
STORAGE_SERVICE_NAMES = ("blob", "dfs")
CONTAINER_NAME_REGEX = re.compile(
    r"^(?!.*--)[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")
CONTROL_CHARACTER_REGEX = re.compile(r"[\x00-\x1f\x7f]")
ENCODED_PATH_SEPARATOR_REGEX = re.compile(r"%(?:2f|5c)", re.IGNORECASE)
INGESTION_FILE_NAME_REGEX = re.compile(r"^.+\.c000\.json$")
RETRY_FOLDER_REGEX = re.compile(r"^retry([1-9][0-9]*)$")

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
    global INGESTION_STORAGE_ACCOUNT_URL, INGESTION_CONTAINER_NAME, INGESTION_ROOT_PATH
    global MAX_INGEST_RETRIES_TIMES, RETRY_END_IN_FAIL_CONTAINER_NAME
    global BLOB_REQ_MAX_ATTEMPT, BLOB_REQ_MAX_RETRY_DELAY_SEC
    global APP_INSIGHT_APP_ID, APP_INSIGHT_APP_KEY, APP_INSIGHT_QUERY_URL

    RETRY_END_IN_FAIL_EVENT_NAME = os.getenv("RETRY_END_IN_FAIL_EVENT_NAME", RETRY_END_IN_FAIL_EVENT_NAME)
    RETRY_EVENT_NAME = os.getenv("RETRY_EVENT_NAME", RETRY_EVENT_NAME)
    MAX_INGEST_RETRIES_TIMES = int(os.getenv("MAX_INGEST_RETRIES_TIMES", str(MAX_INGEST_RETRIES_TIMES)))
    APP_INSIGHT_KEY = os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY", APP_INSIGHT_KEY)
    AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING", AZURE_STORAGE_CONNECTION_STRING)
    INGESTION_STORAGE_ACCOUNT_URL = os.getenv(
        "INGESTION_STORAGE_ACCOUNT_URL", INGESTION_STORAGE_ACCOUNT_URL)
    INGESTION_CONTAINER_NAME = os.getenv("INGESTION_CONTAINER_NAME", INGESTION_CONTAINER_NAME)
    INGESTION_ROOT_PATH = os.getenv("INGESTION_ROOT_PATH", INGESTION_ROOT_PATH)
    RETRY_END_IN_FAIL_CONTAINER_NAME = os.getenv("RETRY_END_IN_FAIL_CONTAINER_NAME", RETRY_END_IN_FAIL_CONTAINER_NAME)
    BLOB_REQ_MAX_ATTEMPT = int(os.getenv("BLOB_REQ_MAX_ATTEMPT", str(BLOB_REQ_MAX_ATTEMPT)))
    BLOB_REQ_MAX_RETRY_DELAY_SEC = int(os.getenv("BLOB_REQ_MAX_RETRY_DELAY_SEC", str(BLOB_REQ_MAX_RETRY_DELAY_SEC)))
    APP_INSIGHT_APP_ID = os.environ.get('APP_INSIGHT_APP_ID', APP_INSIGHT_APP_ID)
    APP_INSIGHT_APP_KEY = os.environ.get('APP_INSIGHT_APP_KEY', APP_INSIGHT_APP_KEY)
    APP_INSIGHT_QUERY_URL = os.environ.get('APP_INSIGHT_QUERY_URL', APP_INSIGHT_QUERY_URL)

    required_settings = {
        "AZURE_STORAGE_CONNECTION_STRING": AZURE_STORAGE_CONNECTION_STRING,
        "INGESTION_STORAGE_ACCOUNT_URL": INGESTION_STORAGE_ACCOUNT_URL,
        "INGESTION_CONTAINER_NAME": INGESTION_CONTAINER_NAME,
        "INGESTION_ROOT_PATH": INGESTION_ROOT_PATH,
        "RETRY_END_IN_FAIL_CONTAINER_NAME": RETRY_END_IN_FAIL_CONTAINER_NAME,
    }
    missing_settings = [name for name, value in required_settings.items() if not value]
    if missing_settings:
        raise EnvironmentError(
            "Missing required application settings: {}".format(", ".join(missing_settings)))
    if not CONTAINER_NAME_REGEX.fullmatch(INGESTION_CONTAINER_NAME):
        raise EnvironmentError("INGESTION_CONTAINER_NAME is not a valid Azure Blob container name.")
    if not CONTAINER_NAME_REGEX.fullmatch(RETRY_END_IN_FAIL_CONTAINER_NAME):
        raise EnvironmentError(
            "RETRY_END_IN_FAIL_CONTAINER_NAME is not a valid Azure Blob container name.")
    get_configured_root_parts()


def get_allowed_storage_hosts(account_url: str):
    """ Return the blob and DFS hosts for a configured Azure Storage account URL. """
    parsed_url = urlparse(account_url)
    try:
        port = parsed_url.port
    except ValueError as error:
        raise EnvironmentError("INGESTION_STORAGE_ACCOUNT_URL has an invalid port.") from error

    if (parsed_url.scheme.lower() != "https" or parsed_url.username or parsed_url.password
            or port is not None):
        raise EnvironmentError("INGESTION_STORAGE_ACCOUNT_URL must be an HTTPS account URL.")
    if parsed_url.query or parsed_url.fragment or parsed_url.path not in ("", "/"):
        raise EnvironmentError(
            "INGESTION_STORAGE_ACCOUNT_URL must not include a path, query, or fragment.")

    host_parts = (parsed_url.hostname or "").lower().split(".")
    if len(host_parts) < 3 or host_parts[1] not in STORAGE_SERVICE_NAMES:
        raise EnvironmentError("INGESTION_STORAGE_ACCOUNT_URL must use a blob or DFS endpoint.")

    account_name = host_parts[0]
    endpoint_suffix = ".".join(host_parts[2:])
    return frozenset(
        f"{account_name}.{service_name}.{endpoint_suffix}"
        for service_name in STORAGE_SERVICE_NAMES)


def get_retry_folder(blob_path: str):
    """ Return the retry folder index and count, rejecting ambiguous retry paths. """
    folder_parts = blob_path.split("/")[:-1]
    retry_folders = [
        (index, RETRY_FOLDER_REGEX.fullmatch(path_part))
        for index, path_part in enumerate(folder_parts)
        if RETRY_FOLDER_REGEX.fullmatch(path_part)
    ]
    if len(retry_folders) > 1:
        raise ValueError("Blob path contains multiple retry folders.")
    if not retry_folders:
        if folder_parts and folder_parts[-1].startswith("retry"):
            raise ValueError("Blob path contains an invalid retry folder.")
        return None, 0
    retry_index, retry_match = retry_folders[0]
    if retry_index != len(folder_parts) - 1:
        raise ValueError("Retry folder must be immediately before the ingestion file.")
    return retry_index, int(retry_match.group(1))


def get_configured_root_parts():
    """ Return the validated configured root path segments. """
    if not isinstance(INGESTION_ROOT_PATH, str) or not INGESTION_ROOT_PATH:
        raise EnvironmentError("INGESTION_ROOT_PATH must be a non-empty relative blob path.")
    root_parts = INGESTION_ROOT_PATH.split("/")
    if any(
            not part or part in (".", "..") or "\\" in part or CONTROL_CHARACTER_REGEX.search(part)
            for part in root_parts):
        raise EnvironmentError("INGESTION_ROOT_PATH contains an invalid path segment.")
    return tuple(root_parts)


def validate_blob_location(container_name: str, blob_path: str,
                           allow_final_failure_container: bool = False) -> None:
    """ Validate a blob location before using the privileged storage connection. """
    allowed_containers = {INGESTION_CONTAINER_NAME}
    if allow_final_failure_container:
        allowed_containers.add(RETRY_END_IN_FAIL_CONTAINER_NAME)
    if container_name not in allowed_containers:
        raise PermissionError("Blob container is outside the configured ingestion scope.")

    path_parts = blob_path.split("/")
    if any(
            not part or part in (".", "..") or "\\" in part or CONTROL_CHARACTER_REGEX.search(part)
            for part in path_parts):
        raise ValueError("Blob path contains an invalid path segment.")
    root_parts = get_configured_root_parts()
    if tuple(path_parts[:len(root_parts)]) != root_parts:
        raise PermissionError("Blob path is outside the configured ingestion root path.")
    if not INGESTION_FILE_NAME_REGEX.fullmatch(path_parts[-1]):
        raise PermissionError("Blob path does not identify an ADX ingestion data file.")
    get_retry_folder(blob_path)


def get_blob_retry_times(blob_path: str) -> int:
    """ Get the ingest trial count for a given blob path """
    _, retry_times = get_retry_folder(blob_path)
    return retry_times

def move_blob_file(connect_str: str, source_container: str, target_container: str,
                   source_path: str, target_path: str) -> None:
    """ Move blob from source to destination container """
    validate_blob_location(source_container, source_path)
    validate_blob_location(target_container, target_path, allow_final_failure_container=True)
    expected_target = get_new_blob_move_file_path(source_container, source_path)
    if (target_container, target_path) != expected_target:
        raise PermissionError("Blob move destination does not match the authorized retry path.")

    logging.info('Move blob from %s/%s to %s/%s',
                 source_container, source_path, target_container, target_path)
    blob_service_client = BlobServiceClient.from_connection_string(connect_str)
    blob_source_client = blob_service_client.get_blob_client(container=source_container, blob=source_path)
    blob_target_client = blob_service_client.get_blob_client(container=target_container, blob=target_path)
    copy_result = blob_target_client.start_copy_from_url(
        blob_source_client.url, requires_sync=True)
    copy_status = getattr(copy_result.get("copy_status"), "value",
                          copy_result.get("copy_status"))
    if copy_status != "success":
        raise RuntimeError(
            f"Blob copy did not complete synchronously; copy status was {copy_status}.")
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
    retry_index, retry_times = get_retry_folder(blob_file_path)
    path_parts = blob_file_path.split("/")
    if no_retry:
        # case no-retry: <folder path>/<filename> -> <folder path>/<filename> in retryEndInFail container
        return RETRY_END_IN_FAIL_CONTAINER_NAME, blob_file_path
    if retry_times == 0:
        # case retry: <folder path>/<filename> -> <folder path>/retryx/<filename> in same container
        path_parts.insert(len(path_parts) - 1, "retry1")
        return blob_container, "/".join(path_parts)
    if retry_times >= MAX_INGEST_RETRIES_TIMES:
        # case retry-end-fail: <folder path>/retryX/<filename> -> <folder path>/<filename>
        # in retryEndInFail container
        del path_parts[retry_index]
        return RETRY_END_IN_FAIL_CONTAINER_NAME, "/".join(path_parts)

    # case keep-retry: update the retry<retry_times> to retry<retry_times+1> in same container
    path_parts[retry_index] = f"retry{retry_times + 1}"
    return blob_container, "/".join(path_parts)

def get_blob_info_from_url(url: str) -> Tuple[str, str]:
    """ Validate a queue-provided URL and return its authorized container and blob path. """
    parsed_url = urlparse(url)
    try:
        port = parsed_url.port
    except ValueError as error:
        raise ValueError("Blob URL has an invalid port.") from error

    if (parsed_url.scheme.lower() != "https" or parsed_url.username or parsed_url.password
            or port is not None):
        raise ValueError("Blob URL must use HTTPS without credentials or an explicit port.")
    if parsed_url.query or parsed_url.fragment:
        raise ValueError("Blob URL must not include a query string or fragment.")
    if (parsed_url.hostname or "").lower() not in get_allowed_storage_hosts(
            INGESTION_STORAGE_ACCOUNT_URL):
        raise PermissionError("Blob URL does not belong to the configured ingestion storage account.")
    if ENCODED_PATH_SEPARATOR_REGEX.search(parsed_url.path):
        raise ValueError("Blob URL contains an encoded path separator.")

    try:
        decoded_path = unquote(parsed_url.path, errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("Blob URL path is not valid UTF-8.") from error

    if not decoded_path.startswith("/") or decoded_path.startswith("//"):
        raise ValueError("Blob URL path is malformed.")
    path_parts = decoded_path[1:].split("/")
    if len(path_parts) < 2 or path_parts[0] != INGESTION_CONTAINER_NAME:
        raise PermissionError("Blob URL does not belong to the configured ingestion container.")
    if any(
            not part or part in (".", "..") or "\\" in part or CONTROL_CHARACTER_REGEX.search(part)
            for part in path_parts):
        raise ValueError("Blob URL contains an invalid path segment.")

    blob_path = "/".join(path_parts[1:])
    validate_blob_location(path_parts[0], blob_path)
    return path_parts[0], blob_path

def main(msg: func.QueueMessage) -> None:
    """
    Main function, triggered by Azure Storage Queue, parsed queue content
    :param msg: func.QueueMessage
    :return: None
    """
    logging.info('Python queue trigger function processed a queue item')
    get_config_values()

    # Get blob file content
    content = json.loads(msg.get_body().decode('utf-8'))
    filepath = content['data']['url']

    container_name, blob_file_path = get_blob_info_from_url(filepath)
    dest_container_name, dest_blob_file_path = get_new_blob_move_file_path(container_name, blob_file_path)
    retry_times = get_blob_retry_times(blob_file_path)
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
