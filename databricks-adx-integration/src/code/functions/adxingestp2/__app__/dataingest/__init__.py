"""
  [Microsoft Kusto Lab Project]

  1. This code is based on Azure Functions Python Runtime.
  2. It will be triggered by Azure Storage Queue
  3. When it been triggered, it will parse the trigger information,
  get the data time of the data and generate ingestion meta-data (eg. Data Time) for Azure Data Explorer.
  4. Best effort to check if input has not been processed.
     Bypass check when the check has problem such as connection issue to table service.
  5. After the ingestion meta data is prepared,
  it will call Azure Data Explore SDK to ingest data from Azure DataLake
"""
import datetime
import json
import logging
import ntpath
import os
import re
import time
import uuid
import hashlib
from distutils.util import strtobool
from pathlib import Path
import dateutil.parser as p
import azure.functions as func
from azure.kusto.data import KustoConnectionStringBuilder
from azure.kusto.ingest import (
    BlobDescriptor,
    IngestionProperties,
    DataFormat,
    ReportLevel,
)
from azure.kusto.ingest import KustoIngestClient
from azure.kusto.ingest.status import KustoIngestStatusQueues
from azure.cosmosdb.table.tableservice import TableService
from azure.cosmosdb.table.models import Entity
from tenacity import (
    retry,
    stop_after_attempt,
    wait_incrementing,
    before_sleep_log,
    Retrying,
    wait_random
)

# # DATA LAKE CONFIG
SOURCE_TELEMETRY_FILE_TOKEN = ""

# ADX CONFIG
APP_AAD_TENANT_ID = None
APP_CLIENT_ID = None
APP_CLIENT_SECRETS = None
INGESTION_SERVER_URI = None
INGESTION_MAPPING = "json_mapping_01"

# CONFIG FOR LOG MESSAGE
LOG_MESSAGE_HEADER = "[ADX-INGESTION-P2]"
PROCESS_PROGRAM_NAME = "INGESTION_EVENTGRID_V001A"

# REGULAR EXPRESSION TO VALIDATE IF THE FILE NEED PROCESS BASED ON FILE NAME and FILE PATH
#Now the filename has been changed from databricks
EVENT_SUBJECT_FILTER_REGEX = "(.*?)[0-9].json"
IS_FLUSH_IMMEDIATELY = "True"  # True or False

KUSTO_INGESTION_CLIENT = None
DATABASEID_KEY = "companyIdkey="
TABLEID_KEY = "typekey="

# MAX Retry Times
RETRY_MAX_ATTEMPT_NUMBER = "5" #times
# Retry wait Incremental value
RETRY_WAIT_INCREMENT_VALUE = "2" #sec
# Max wait time for retry
RETRY_MAX_WAIT_TIME = "10" #sec

#For Module 6
IS_DUPLICATE_CHECK = False
STORAGE_TABLE_ACCOUNT = None
STORAGE_TABLE_TOKEN = None
DUPLICATE_EVENT_NAME = 'KUSTOLAB_DUPLICATE_FAILURE'
LOG_TABLE_PREFIX = 'logtable'
TABLE_SERVICE = None

MANDATORY_ENV_VARS = ["APP_AAD_TENANT_ID", "APP_CLIENT_ID", "APP_CLIENT_SECRETS", \
    "INGESTION_SERVER_URI", "INGESTION_MAPPING"]

def main(msg: func.QueueMessage) -> None:
    """
    Main function, triggered by Azure Storage Queue, parsed queue content and call ingest_to_ADX
    :param msg: func.QueueMessage
    :return: None
    """
    logging.info('Python queue trigger function processed a queue item: %s',
                 msg.get_body().decode('utf-8'))
    # Set the logging level for all azure-* libraries
    logging.getLogger('azure').setLevel(logging.WARNING)
    modification_time = None
    get_config_values()
    #get message content
    #queue from checkpoint function
    content_json = json.loads(msg.get_body().decode('utf-8'))
    file_url = content_json['data']['url']
    logging.info(f"{LOG_MESSAGE_HEADER} file_url:{file_url}")
    msg_time = p.parse(content_json['eventTime'])
    try:
        #modification time is the time databricks processed finished
        modification_time = p.parse(content_json['modificationTime'])
    except Exception:
        modification_time = msg_time

    #get file size from storage queue directly
    file_size = content_json['data']['contentLength']
    # Sharing: New logic based on new schema
    target_database, target_table = get_target_info(file_url)
    logging.info(f"{LOG_MESSAGE_HEADER} target_database:{target_database}, target_table:{target_table}")
    
    #set up if log table connection when duplicate check enable
    if IS_DUPLICATE_CHECK:
        #get log table name
        get_table_connection()
        log_table_name = get_logtable_name()
        check_create_table(log_table_name)
        #get table connection
        get_table_connection()
        processed_Flag, log_table_key = check_file_process_log(log_table_name, file_url, target_database)
    else:
        processed_Flag = False
    #use regexp to check file
    regexp = re.compile(EVENT_SUBJECT_FILTER_REGEX)
    if regexp.search(file_url):  # Check if file path match criteria
        if processed_Flag is False:
            #initailize kusto client
            initialize_kusto_client()
            # Retry max RETRY_MAX_ATTEMPT_NUMBER times
            # Wait starting from random (0 to 3) secs. increment util max wait time
            retryer = Retrying(stop=stop_after_attempt(RETRY_MAX_ATTEMPT_NUMBER), \
                        wait=wait_random(0, 3)+ wait_incrementing(start=1, \
                        increment=RETRY_WAIT_INCREMENT_VALUE, \
                        max=RETRY_MAX_WAIT_TIME), \
                        before_sleep=before_sleep_log(logging, logging.WARNING), reraise=True)
            ingest_source_id = retryer(ingest_to_adx, file_url, file_size, target_database, \
                target_table, msg_time, modification_time)
            logging.info(f"ingest_source_id:{ingest_source_id}")

            if IS_DUPLICATE_CHECK:
            # Add Log in to logtable
                insert_log_table(log_table_name, target_database, log_table_key, msg_time, \
                    modification_time, file_url, ingest_source_id)
        else:
                logging.warning(f"{DUPLICATE_EVENT_NAME} DUPLICATE DATA Subject : {file_url} \
                    has been processed already. Skip process.")      
    else:
        logging.warning(
            "%s Subject : %s does not match regular express %s. Skip process. ", \
                LOG_MESSAGE_HEADER, file_url, EVENT_SUBJECT_FILTER_REGEX)


def get_config_values():
    """
    Get Config setting from predefined variables or environment parameters.
    :return: None
    """
    global SOURCE_TELEMETRY_FILE_TOKEN
    global APP_AAD_TENANT_ID, APP_CLIENT_ID, APP_CLIENT_SECRETS, \
        INGESTION_SERVER_URI, INGESTION_MAPPING
    global LOG_MESSAGE_HEADER, PROCESS_PROGRAM_NAME, EVENT_SUBJECT_FILTER_REGEX
    global IS_FLUSH_IMMEDIATELY
    global DATABASEID_KEY, TABLEID_KEY

    global RETRY_MAX_ATTEMPT_NUMBER, RETRY_WAIT_INCREMENT_VALUE, RETRY_MAX_WAIT_TIME
    global IS_DUPLICATE_CHECK, STORAGE_TABLE_ACCOUNT, STORAGE_TABLE_TOKEN, DUPLICATE_EVENT_NAME, LOG_TABLE_PREFIX
    for var in MANDATORY_ENV_VARS:
        if var not in os.environ:
            raise EnvironmentError(f"{LOG_MESSAGE_HEADER} Get Config Failed: {var} is not set.")

    try:
        SOURCE_TELEMETRY_FILE_TOKEN = os.getenv("SOURCE_TELEMETRY_FILE_TOKEN", SOURCE_TELEMETRY_FILE_TOKEN)
        # ADX CONFIG
        APP_AAD_TENANT_ID = os.getenv("APP_AAD_TENANT_ID", APP_AAD_TENANT_ID)
        APP_CLIENT_ID = os.getenv("APP_CLIENT_ID", APP_CLIENT_ID)
        APP_CLIENT_SECRETS = os.getenv("APP_CLIENT_SECRETS", APP_CLIENT_SECRETS)
        INGESTION_SERVER_URI = os.getenv("INGESTION_SERVER_URI", INGESTION_SERVER_URI)
        INGESTION_MAPPING = os.getenv("INGESTION_MAPPING", INGESTION_MAPPING)

        DATABASEID_KEY =  os.getenv("DATABASEID_KEY", DATABASEID_KEY)
        TABLEID_KEY = os.getenv("TABLEID_KEY", TABLEID_KEY )
        logging.info(f"DATABASEID_KEY:{DATABASEID_KEY}, TABLEID_KEY:{TABLEID_KEY}")
        LOG_MESSAGE_HEADER = os.getenv("LOG_MESSAGE_HEADER", LOG_MESSAGE_HEADER)

        PROCESS_PROGRAM_NAME = os.getenv("PROCESS_PROGRAM_NAME", PROCESS_PROGRAM_NAME)

        EVENT_SUBJECT_FILTER_REGEX = os.getenv("EVENT_SUBJECT_FILTER_REGEX", EVENT_SUBJECT_FILTER_REGEX)
        IS_FLUSH_IMMEDIATELY = strtobool(str(os.getenv("IS_FLUSH_IMMEDIATELY", IS_FLUSH_IMMEDIATELY)))
        logging.info(f"IS_FLUSH_IMMEDIATELY:{IS_FLUSH_IMMEDIATELY}")
        #Retry Setting
        RETRY_MAX_ATTEMPT_NUMBER = int(os.getenv("RETRY_MAX_ATTEMPT_NUMBER", RETRY_MAX_ATTEMPT_NUMBER))
        RETRY_WAIT_INCREMENT_VALUE = int(os.getenv("RETRY_WAIT_INCREMENT_VALUE", RETRY_WAIT_INCREMENT_VALUE))
        RETRY_MAX_WAIT_TIME = int(os.getenv("RETRY_MAX_WAIT_TIME", RETRY_MAX_WAIT_TIME))

        #Module 6
        IS_DUPLICATE_CHECK = strtobool(str(os.getenv("IS_DUPLICATE_CHECK", IS_DUPLICATE_CHECK)))
        STORAGE_TABLE_ACCOUNT = os.getenv("STORAGE_TABLE_ACCOUNT", STORAGE_TABLE_ACCOUNT)
        STORAGE_TABLE_TOKEN = os.getenv("STORAGE_TABLE_TOKEN", STORAGE_TABLE_TOKEN)
        DUPLICATE_EVENT_NAME = os.getenv("DUPLICATE_EVENT_NAME", DUPLICATE_EVENT_NAME)
        LOG_TABLE_PREFIX = os.getenv("LOG_TABLE_PREFIX", LOG_TABLE_PREFIX)

    except Exception as e:
        logging.exception(e)

def ingest_to_adx(file_path, file_size, target_database, target_table, \
    msg_time, modification_time):
    """
    Trigger ADX to ingest the specified file in Azure Data Lake
    Prepare ADX ingestion meta-data
    :param file_path: The full path of blob file
    :param file_size: The full size of blob file
    :param target_database: The target database
    :param target_table: The target table
    :param msg_time: The msg_time from eventgrid
    :param azure_telemetry_client: The telemetry client used for sending telemetry of the ingest function
    :return: None
    """
    logging.info(f'{LOG_MESSAGE_HEADER} start to ingest to adx')
    ingest_source_id = str(uuid.uuid4())
    if SOURCE_TELEMETRY_FILE_TOKEN.startswith('?'):
        blob_path = file_path +  SOURCE_TELEMETRY_FILE_TOKEN
    else:
        blob_path = file_path + '?' + SOURCE_TELEMETRY_FILE_TOKEN
    logging.info(f"{LOG_MESSAGE_HEADER} blob_path:{blob_path}, ingest_source_id:{ingest_source_id}")
    logging.info('%s FILEURL : %s, INGESTION URL: %s, Database: %s, \
                    Table: %s, FILESIZE: %s, msg_time: %s, modification_time: %s', \
                    LOG_MESSAGE_HEADER, blob_path, INGESTION_SERVER_URI, \
                    target_database, target_table, file_size, msg_time, modification_time)
    
    ingestion_properties = IngestionProperties(database=target_database, table=target_table, \
                                            dataFormat=DataFormat.JSON, \
                                            ingestion_mapping_reference=INGESTION_MAPPING, \
                                            reportLevel=ReportLevel.FailuresAndSuccesses, \
                                            additionalProperties={'reportMethod': 'QueueAndTable', \
                                                    "creationTime": msg_time.strftime( \
                                                    "%Y-%m-%d %H:%M"), "modificationTime": modification_time.strftime( \
                                                    "%Y-%m-%d %H:%M")}, \
                                            flushImmediately=IS_FLUSH_IMMEDIATELY)



    blob_descriptor = BlobDescriptor(blob_path, file_size, \
                                    ingest_source_id)  # 10 is the raw size of the data in bytes
    logging.info(f"{LOG_MESSAGE_HEADER} start to ingest to queue")
    start_time = time.time()
    KUSTO_INGESTION_CLIENT.ingest_from_blob(blob_descriptor, ingestion_properties=ingestion_properties)
    logging.info(f"{LOG_MESSAGE_HEADER} ingest process time {time.time()-start_time}")

    return ingest_source_id

def get_target_info(file_url):
    """get target database and table from file path
    :param file_url: file path
    :type file_url: string
    :return: target_database
    :rtype: string
    :return: target_table
    :rtype: string
    """
    global DATABASEID_KEY
    global TABLEID_KEY  
    for part in Path(file_url).parts:
        if part.startswith(DATABASEID_KEY):
            target_database = part.replace(DATABASEID_KEY, '')
        if part.startswith(TABLEID_KEY):
            target_table = (part.replace(TABLEID_KEY, '')).upper()
    return target_database, target_table

def initialize_kusto_client():
    """initialize kusto client
    """
    global KUSTO_INGESTION_CLIENT
    if not KUSTO_INGESTION_CLIENT:
        kcsb_ingest = KustoConnectionStringBuilder.with_aad_application_key_authentication( \
            INGESTION_SERVER_URI, APP_CLIENT_ID, APP_CLIENT_SECRETS, APP_AAD_TENANT_ID)
        KUSTO_INGESTION_CLIENT = KustoIngestClient(kcsb_ingest)
        logging.info(f"{LOG_MESSAGE_HEADER} Build KUSTO_INGESTION_CLIENT")
    else:
        logging.info(f"{LOG_MESSAGE_HEADER} KUSTO_INGESTION_CLIENT exist")

def get_logtable_name():
    """get log table name
    """
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc)
    log_table_name = "{}{}".format(LOG_TABLE_PREFIX, utc_timestamp.strftime("%m%d%Y"))
    return log_table_name

def check_file_process_log(log_table_name, file_url, target_database):
    """check if input has been processed
    :param file_url: file url
    :type file_url: string
    :param target_database: target_database
    :type target_database: string
    :return: validaton result
    :rtype: bool
    """
    start_time = time.time()
    processed = False
    #use md5 for hash
    hash_result = hashlib.md5(file_url.encode('utf-8'))
    table_key = hash_result.hexdigest()
    logging.info(f"{LOG_MESSAGE_HEADER} file_url:{file_url} , table_key:{table_key}")
    query_filter = f"(PartitionKey eq '{target_database}') and (RowKey eq '{table_key}')"
    logging.info(f"{LOG_MESSAGE_HEADER} LOG_TABLE_NAME:{log_table_name}")
    results = None
    try:
        results = query_table(log_table_name, query_filter)
    except Exception:
        logging.exception(f"Failed to query log table from table storage")        

    if results is not None and len(results) > 0:
        processed = True
    logging.info(f"{LOG_MESSAGE_HEADER} check log process time:{time.time() - start_time}, \
        logfile:{file_url}, table_key:{table_key}, result:{processed}")
    return processed, table_key

def query_table(table_name, query):
    """query table
    :param table_name: query table name
    :type table_name: string
    :param query: query
    :type query: string
    :return: results
    :rtype: list
    """
    results = None
    #TODO: if future want to add cache expired time check
    #utc_query_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
    try:
        #get dict from storage table
        logging.info(f"{LOG_MESSAGE_HEADER} table_name:{table_name},get query {query}")
        results = TABLE_SERVICE.query_entities(table_name, query)
    except Exception as err:
        logging.exception(err)
        raise
    return list(results)

def insert_log_table(log_table_name, target_database, table_key, event_time, \
    modification_time, file_url, ingest_source_id):
    """insert log table
    :param target_database: target_database
    :type target_database: string
    :param table_key: table key (hash url)
    :type table_key: string
    :param event_time: msg event time
    :type event_time: datetime
    :param modification_time: modification time
    :type modification_time: datetime
    :param file_url: file url
    :type file_url: string
    :param ingest_source_id: ingest source id
    :type ingest_source_id: string
    """
    status = 'Pending'
    msg_log_data = {'PartitionKey': target_database, 'RowKey': table_key, \
        'eventtime':event_time, 'drop_by_tag':event_time.strftime("%Y-%m-%d"), \
        'modificationtime':modification_time, 'file_url':file_url, \
            'ingest_source_id':ingest_source_id, 'status':status}
    try:
        #Insert data to log
        logging.info(f"{LOG_MESSAGE_HEADER} insert to log_table:{log_table_name},data {msg_log_data}")
        TABLE_SERVICE.insert_entity(log_table_name, msg_log_data)
    except Exception as err:
        logging.exception(err)

def get_table_connection():
    """get table Connection
    """
    logging.info(f"try to get table connection")
    global TABLE_SERVICE
    if not TABLE_SERVICE:
        TABLE_SERVICE = TableService(account_name=STORAGE_TABLE_ACCOUNT, sas_token=STORAGE_TABLE_TOKEN)
        logging.info(f"{LOG_MESSAGE_HEADER} TABLE Storage Connection :{TABLE_SERVICE}")
    else:
        logging.info(f"{LOG_MESSAGE_HEADER} TABLE connection exist")

def check_create_table(table_name):
    """create and rename table
    """
    result = False
    try:
        is_origin_exist = TABLE_SERVICE.exists(table_name, timeout=None)
        if not is_origin_exist:
            logging.info("%s create_table: create table - %s", \
                LOG_MESSAGE_HEADER, table_name)
            result = TABLE_SERVICE.create_table(table_name, True)
        # else: #Leave for debug purpose
        #     logging.info("%s create_table: table exists - %s", \
        #     LOG_MESSAGE_HEADER, table_name)
    except Exception as err:
        logging.exception("%s create_table: error %s", \
            LOG_MESSAGE_HEADER, err)
        raise
    return result
