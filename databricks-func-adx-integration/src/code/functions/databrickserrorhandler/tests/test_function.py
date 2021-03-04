import json
import logging
import pytest
import __app__.dbserrorhandler
import random
import string

import azure.functions as func
from __app__.dbserrorhandler import get_blob_retry_times, get_new_blob_move_file_path, check_retry_necessary

testdata_check_retry_necessary = [
    ('https://sdldemodatabricksretry.blob.core.windows.net/bad-requests/bad_files/part-00000-9466fa97-8aeb-42a2-a5b5-4be4ca7022b1-0',
     True),

    ('https://sdldemodatabricksretry.blob.core.windows.net/bad-requests/bad_records/part-00000-9466fa97-8aeb-42a2-a5b5-4be4ca7022b1-0',
     False)
]


@pytest.mark.parametrize("test_blob_path, necessary", testdata_check_retry_necessary)
def test_check_retry_necessary(test_blob_path, necessary):
    assert necessary == check_retry_necessary(test_blob_path)


testdata_get_blob_retry_times = [
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz', 0),
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz/retry1/07-23-2020-01-03-17_30770.gz', 1),
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz/retry2/07-23-2020-01-03-17_30770.gz', 2),
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz/retry3/07-23-2020-01-03-17_30770.gz', 3),
]


@pytest.mark.parametrize("test_blob_path, expected_result", testdata_get_blob_retry_times)
def test_get_blob_retry_times(test_blob_path, expected_result):
    assert expected_result == get_blob_retry_times(test_blob_path)


testdata_new_blob_move_file_path = [
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz',
     'split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz', True),
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz',
     'split-output/2020/08/17/17/07-23-2020-01-03-17_30770/retry1/', False),
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770/retry3/07-23-2020-01-03-17_30770.gz',
     'split-output/2020/08/17/17/07-23-2020-01-03-17_30770/', False),
    ('split-output/2020/08/17/17/07-23-2020-01-03-17_30770/retry1/07-23-2020-01-03-17_30770.gz',
     'split-output/2020/08/17/17/07-23-2020-01-03-17_30770/retry2/', False),
]


@pytest.mark.parametrize("test_blob_path, expected_result, no_retry", testdata_new_blob_move_file_path)
def test_get_new_blob_move_file_path(test_blob_path, expected_result, no_retry):
    __app__.dbserrorhandler.MAX_INGEST_RETRIES_TIMES = 3
    assert expected_result in get_new_blob_move_file_path(
        test_blob_path, no_retry)


def test_main(mocker):
    # fake_path = 'split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz'
    # fake_new_path = 'split-output/2020/08/17/17/retry1/07-23-2020-01-03-17_30770.gz'
    # fake_url = 'abfss://split-output@sdldemodatabricksretry.dfs.core.windows.net/{}'.format(
    #     fake_path)

    msg_body = {
        "topic": "/subscriptions/74e52e75-154d-498c-bab3-1fe772244f79/resourceGroups/sdlms-rg/providers/Microsoft.Storage/storageAccounts/sdldemodatabricksretry",
        "subject": "/blobServices/default/containers/bad-requests/blobs/part-00000-9466fa97-8aeb-42a2-a5b5-4be4ca7022b1-0",
        "eventType": "Microsoft.Storage.BlobCreated",
        "id": "3ffce4c6-801e-001e-60c2-765ee406c6b7",
        "data": {
            "api": "PutBlob",
            "clientRequestId": "0de4b6d8-1db7-4e2e-8fd3-39a0b3eca019",
            "requestId": "3ffce4c6-801e-001e-60c2-765ee4000000",
            "eTag": "0x8D844D9356B4C3F",
            "contentType": "application/octet-stream",
            "contentLength": 385,
            "blobType": "BlockBlob",
            "url": "https://sdldemodatabricksretry.blob.core.windows.net/bad-requests/part-00000-9466fa97-8aeb-42a2-a5b5-4be4ca7022b1-0",
            "sequencer": "00000000000000000000000000000a4b0000000000030f55",
            "storageDiagnostics": {
                "batchId": "a6a93152-f11b-41e2-a69f-9d35902e5a5b"}},
        "dataVersion": "",
        "metadataVersion": "1",
        "eventTime": "2020-08-20T07:18:16.7742808Z"}

    Jsontext = {
        "path": "abfss://split-output@sdldemodatabricksretry.dfs.core.windows.net/2020/08/17/17/07-23-2020-01-03-17_30770.gz",
        "reason": "1ja1v1a.io.FileNotFoundException: HEAD https://sdldemodatabricksretry.blob.core.windows.net/split-output/2020/08/17/17/07-23-2020-01-03-17_30770.gz?timeout=90\nStatusCode=404\nStatusDescription=The specified path does not exist.\nErrorCode=\nErrorMessage="
    }

    req = func.QueueMessage(body=json.dumps(msg_body))
    mock_move_blob_file = mocker.patch(
        '__app__.dbserrorhandler.retry_blob_databireck_split')
    mock_move_blob_file.return_value = None

    mock_download_logfile = mocker.patch('__app__.dbserrorhandler.download_logfile')
    __app__.dbserrorhandler.download_logfile = mock_download_logfile
    mock_download_logfile.return_value = json.dumps(Jsontext)

    mock_get_config_values = mocker.patch('__app__.dbserrorhandler.get_config_values')
    __app__.dbserrorhandler.get_config_values = mock_get_config_values

    mock_azure_telemetry_client = mocker.patch(
        'applicationinsights.TelemetryClient')
    __app__.dbserrorhandler.TelemetryClient = mock_azure_telemetry_client

    __app__.dbserrorhandler.main(req)
    assert mock_move_blob_file.called
