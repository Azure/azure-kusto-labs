import asyncio
import json
import logging

import __app__.metadatahandler as metadatahandler
import azure.functions as func
import nest_asyncio
import pytest

nest_asyncio.apply()

class TestUtDatabricksMetadataHandler():
    def test_get_blob_info_from_url(self):
        assert metadatahandler.is_json('bad_json_string') == False
        assert metadatahandler.is_json('{"key": "value"}') == True

    def test_convert_abfss_path_to_https(self):
        fake_abfss_path = 'abfss://container@account.dfs.core.windows.net/folder/fake.json'
        expected_https_path = 'https://account.blob.core.windows.net/container/folder/fake.json'
        assert metadatahandler.convert_abfss_path_to_https(fake_abfss_path) == expected_https_path

        fake_abfss_path = 'abfss://folder/fake.json'
        with pytest.raises(ValueError):
            metadatahandler.convert_abfss_path_to_https(fake_abfss_path)

    def test_generate_metadata_queue_messages(self):
        event_time = '2020-09-07T06:43:03.2126947Z'
        metadata_file_content = """
        v1\n
        {"path":"abfss://container@account.dfs.core.windows.net/folder/fake3.json","size":1014200,"modificationTime":1599182552000}\n
        {"path":"abfss://container@account.dfs.core.windows.net/folder/fake2.json","size":1014200,"modificationTime":1599182552000}\n
        {"path":"abfss://container@account.dfs.core.windows.net/folder/fake1.json","size":1014200,"modificationTime":1599182552000}
        """
        expected_result = []
        for i in range(3):
            msg = metadatahandler.INGEST_QUEUE_MSG_TEMPLATE.format(blob_size='1014200',
                                                                   blob_url=f"https://account.blob.core.windows.net/container/folder/fake{i+1}.json",
                                                                   event_time=event_time,
                                                                   modification_time=1599182552000)
            msg = json.dumps(json.loads(msg))
            expected_result.append(msg) 
        actual = metadatahandler.generate_metadata_queue_messages(event_time, metadata_file_content)
        assert actual == expected_result

    @pytest.mark.asyncio
    async def test_main(self, mocker, monkeypatch):

        event_time = "2020-08-18T17:02:19.6069787Z"
        msg_body = {
            "eventType": "Microsoft.Storage.BlobCreated",
            "eventTime": event_time,
            "data": {
                "api": "PutBlockList",
                "contentLength": 4194349,
                "blobType": "BlockBlob",
                "destinationUrl": "https://account.dfs.core.windows.net/container/_spark_metadata/0"
            }
        }
        req = func.QueueMessage(body=json.dumps(msg_body))

        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        fake_metadata_file_content = """
        v1\n
        {"path":"abfss://container@account.dfs.core.windows.net/folder/fake1.json","size":1014200,"modificationTime":1599182552000}\n
        {"path":"abfss://container@account.dfs.core.windows.net/folder/fake2.json","size":1014200,"modificationTime":1599182552000}\n
        {"path":"abfss://container@account.dfs.core.windows.net/folder/fake3.json","size":1014200,"modificationTime":1599182552000}
        """
        mock_get_blob_content.return_value = fake_metadata_file_content
        metadatahandler.get_blob_content = mock_get_blob_content

        monkeypatch.setenv('ADX_INGEST_QUEUE_URL_LIST', 'https://account.queue.core.windows.net/q1, https://account.queue.core.windows.net/q2, https://account.queue.core.windows.net/q3')
        monkeypatch.setenv('ADX_INGEST_QUEUE_SAS_TOKEN', 'fake_token')
        fake_future = asyncio.Future()
        fake_future.set_result(None)
        mocker.patch('__app__.metadatahandler.QueueClient.send_message', return_value=fake_future)
        mocker.patch('__app__.metadatahandler.close_queue_clients', return_value=None)

        mock_azure_telemetry_client = mocker.patch('applicationinsights.TelemetryClient')
        metadatahandler.TelemetryClient = mock_azure_telemetry_client

        spy_enqueue_message = mocker.spy(metadatahandler.QueueClient, 'send_message')
        metadatahandler.main(req)

        spy_enqueue_message.assert_called()
        assert spy_enqueue_message.call_count == 3
