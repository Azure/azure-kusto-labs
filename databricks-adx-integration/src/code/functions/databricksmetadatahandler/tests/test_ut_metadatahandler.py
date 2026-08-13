import asyncio
import json
import logging

import __app__.metadatahandler as metadatahandler
import azure.functions as func
import nest_asyncio
import pytest

nest_asyncio.apply()

# The function derives the storage account it is allowed to act on from its own
# configured account url, so the tests must supply one just as the deployment does.
FAKE_ACCOUNT_URL = 'https://account.blob.core.windows.net/'
FAKE_QUEUE_URLS = ('https://account.queue.core.windows.net/q1, '
                   'https://account.queue.core.windows.net/q2, '
                   'https://account.queue.core.windows.net/q3')

class TestUtDatabricksMetadataHandler():
    @pytest.fixture(autouse=True)
    def configure_function(self, mocker, monkeypatch):
        """ Apply the function app configuration the deployment provides. """
        monkeypatch.setenv('DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL', FAKE_ACCOUNT_URL)
        monkeypatch.setenv('ADX_INGEST_QUEUE_URL_LIST', FAKE_QUEUE_URLS)
        monkeypatch.setenv('ADX_INGEST_QUEUE_SAS_TOKEN', 'fake_token')
        # main() builds a telemetry client before it reaches any validation, and a
        # real one opens a sender thread, so every test gets a mocked one.
        mocker.patch('__app__.metadatahandler.TelemetryClient')
        metadatahandler.init_config_values()

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

    def test_main(self, mocker):
        # main() is a synchronous function that owns its own event loop, so the
        # test must not run inside one: closing a running loop raises RuntimeError.
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

        async def fake_send_message(*args, **kwargs):
            return None
        mocker.patch('__app__.metadatahandler.QueueClient.send_message', side_effect=fake_send_message)
        mocker.patch('__app__.metadatahandler.close_queue_clients', return_value=None)

        spy_enqueue_message = mocker.spy(metadatahandler.QueueClient, 'send_message')
        metadatahandler.main(req)

        spy_enqueue_message.assert_called()
        assert spy_enqueue_message.call_count == 3

    # --- Validation of the queue supplied metadata url ---

    def _metadata_message(self, destination_url):
        return func.QueueMessage(body=json.dumps({
            "eventTime": "2020-08-18T17:02:19.6069787Z",
            "data": {"destinationUrl": destination_url}
        }))

    @pytest.mark.parametrize('bad_url', [
        # A different storage account. The privileged client is built from the
        # configured account, so this would read our own storage, not theirs.
        'https://attacker.blob.core.windows.net/container/_spark_metadata/0',
        # Lookalike host that only shares a prefix with the allowed host.
        'https://account.blob.core.windows.net.attacker.example/container/_spark_metadata/0',
        # Credentials embedded to confuse naive host parsing.
        'https://account.blob.core.windows.net:pwd@attacker.example/container/_spark_metadata/0',
        'http://account.blob.core.windows.net/container/_spark_metadata/0',
    ])
    def test_main_rejects_off_account_url(self, mocker, bad_url):
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(bad_url))
        assert mock_get_blob_content.call_count == 0

    @pytest.mark.parametrize('bad_path', [
        # Traversal out of the metadata directory.
        'container/_spark_metadata/../../secret.compact',
        # Percent encoded traversal, decoded by the storage sdk before it reaches
        # the sink, so it must be validated after the sdk has resolved it.
        'container/%2e%2e%2f%2e%2e%2fsecret.compact',
        # Any blob outside a _spark_metadata directory, which is the only place
        # this function has a legitimate reason to read or rewrite.
        'container/production/customer-data.compact',
        # Lookalike directory that must not satisfy the required segment.
        'container/_spark_metadata_evil/0',
    ])
    def test_main_rejects_paths_outside_the_metadata_directory(self, mocker, bad_path):
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        url = 'https://account.blob.core.windows.net/{}'.format(bad_path)
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(url))
        assert mock_get_blob_content.call_count == 0

    def test_main_fails_closed_without_configuration(self, mocker, monkeypatch):
        monkeypatch.setenv('DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL', '')
        metadatahandler.init_config_values()
        assert metadatahandler.ALLOWED_STORAGE_HOSTS == set()

        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(
                'https://account.blob.core.windows.net/container/_spark_metadata/0'))
        assert mock_get_blob_content.call_count == 0

    def test_allowed_hosts_cover_both_blob_and_dfs_endpoints(self):
        # Databricks emits dfs (ADLS Gen2) urls while the blob sdk uses blob urls;
        # both address the same account and must both be accepted.
        assert metadatahandler.ALLOWED_STORAGE_HOSTS == {
            'account.blob.core.windows.net', 'account.dfs.core.windows.net'}

    def test_generate_metadata_queue_messages_skips_off_account_paths(self):
        # The metadata file content also selects destinations for the downstream
        # ingest function, so off-account entries must not be forwarded.
        event_time = '2020-09-07T06:43:03.2126947Z'
        metadata_file_content = (
            'v1\n'
            '{"path":"abfss://container@account.dfs.core.windows.net/folder/good.json",'
            '"size":1,"modificationTime":1599182552000}\n'
            '{"path":"abfss://container@attacker.dfs.core.windows.net/folder/bad.json",'
            '"size":1,"modificationTime":1599182552000}\n'
        )
        actual = metadatahandler.generate_metadata_queue_messages(event_time, metadata_file_content)
        assert len(actual) == 1
        assert 'account.blob.core.windows.net' in actual[0]
        assert 'attacker' not in actual[0]
