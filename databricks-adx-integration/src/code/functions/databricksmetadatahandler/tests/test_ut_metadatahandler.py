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

# The container and directory the Databricks job writes to, matching
# Storage.FileSystemName and Storage.AzureStorageTargetFolder in provision-config.
METADATA_CONTAINER = 'data'
PATH_ROOT = 'databricks-out'
CHECKPOINT_BLOB = PATH_ROOT + '/splitdata/output_0/_spark_metadata/0'
CHECKPOINT_URL = 'https://account.dfs.core.windows.net/{}/{}'.format(
    METADATA_CONTAINER, CHECKPOINT_BLOB)
OUTPUT_ABFSS = ('abfss://' + METADATA_CONTAINER + '@account.dfs.core.windows.net/'
                + PATH_ROOT + '/companyIdkey=company-id-0/typekey=TEMP/fake{}.json')
OUTPUT_HTTPS = ('https://account.blob.core.windows.net/' + METADATA_CONTAINER + '/'
                + PATH_ROOT + '/companyIdkey=company-id-0/typekey=TEMP/fake{}.json')

class TestUtDatabricksMetadataHandler():
    @pytest.fixture(autouse=True)
    def configure_function(self, mocker, monkeypatch):
        """ Apply the function app configuration the deployment provides. """
        # init_config_values() reads each setting as os.getenv(NAME, <current global>),
        # so a value set by a previous test survives monkeypatch's env cleanup and
        # would leak into the next one. Reset the globals this suite varies.
        metadatahandler.METADATA_PATH_ROOT = ''
        metadatahandler.METADATA_REQUIRED_SEGMENT = '_spark_metadata'
        monkeypatch.setenv('DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL', FAKE_ACCOUNT_URL)
        monkeypatch.setenv('ADX_INGEST_QUEUE_URL_LIST', FAKE_QUEUE_URLS)
        monkeypatch.setenv('ADX_INGEST_QUEUE_SAS_TOKEN', 'fake_token')
        monkeypatch.setenv('ALLOWED_METADATA_CONTAINERS', METADATA_CONTAINER)
        monkeypatch.setenv('METADATA_PATH_ROOT', PATH_ROOT)
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

    @pytest.mark.parametrize('abfss_path', [
        # An accepted reference buried inside a longer string.
        'prefix abfss://container@account.dfs.core.windows.net/folder/fake.json',
        # A host that only looks like the storage endpoint.
        'abfss://container@account.dfs.core.windows.net.attacker.example/folder/fake.json',
    ])
    def test_convert_abfss_path_to_https_is_anchored(self, abfss_path):
        with pytest.raises(ValueError):
            metadatahandler.convert_abfss_path_to_https(abfss_path)

    def test_generate_metadata_queue_messages(self):
        event_time = '2020-09-07T06:43:03.2126947Z'
        metadata_file_content = "\n".join(
            ['v1'] + ['{{"path":"{}","size":1014200,"modificationTime":1599182552000}}'.format(
                OUTPUT_ABFSS.format(i + 1)) for i in (2, 1, 0)])
        expected_result = []
        for i in range(3):
            msg = metadatahandler.INGEST_QUEUE_MSG_TEMPLATE.format(blob_size='1014200',
                                                                   blob_url=OUTPUT_HTTPS.format(i + 1),
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
                "destinationUrl": CHECKPOINT_URL
            }
        }
        req = func.QueueMessage(body=json.dumps(msg_body))

        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        fake_metadata_file_content = "\n".join(
            ['v1'] + ['{{"path":"{}","size":1014200,"modificationTime":1599182552000}}'.format(
                OUTPUT_ABFSS.format(i + 1)) for i in range(3)])
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

    @pytest.mark.parametrize('bad_host', [
        # A different storage account. The privileged client is built from the
        # configured account, so this would read our own storage, not theirs.
        'attacker.blob.core.windows.net',
        # Lookalike host that only shares a prefix with the allowed host.
        'account.blob.core.windows.net.attacker.example',
        # Credentials embedded to confuse naive host parsing.
        'account.blob.core.windows.net:pwd@attacker.example',
    ])
    def test_main_rejects_off_account_url(self, mocker, bad_host):
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        bad_url = 'https://{}/{}/{}'.format(bad_host, METADATA_CONTAINER, CHECKPOINT_BLOB)
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(bad_url))
        assert mock_get_blob_content.call_count == 0

    def test_main_rejects_a_non_https_url(self, mocker):
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        bad_url = 'http://account.blob.core.windows.net/{}/{}'.format(
            METADATA_CONTAINER, CHECKPOINT_BLOB)
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(bad_url))
        assert mock_get_blob_content.call_count == 0

    @pytest.mark.parametrize('bad_path', [
        # Traversal out of the metadata directory.
        PATH_ROOT + '/_spark_metadata/../../secret.compact',
        # Percent encoded traversal, decoded by the storage sdk before it reaches
        # the sink, so it must be validated after the sdk has resolved it.
        '%2e%2e%2f%2e%2e%2fsecret.compact',
        # Any blob outside a _spark_metadata directory, which is the only place
        # this function has a legitimate reason to read or rewrite.
        PATH_ROOT + '/production/customer-data.compact',
        # Lookalike directory that must not satisfy the required directory.
        PATH_ROOT + '/_spark_metadata_evil/0',
        # The directory somewhere above the file rather than directly containing
        # it, which would still reach an unrelated blob.
        PATH_ROOT + '/_spark_metadata/nested/evil.compact',
        # A file name Spark never writes.
        PATH_ROOT + '/output_0/_spark_metadata/not-a-spark-file.compact',
        # Outside the directory the Databricks job writes to.
        'unrelated/output_0/_spark_metadata/0',
        # A sibling directory whose name merely starts with the expected one.
        PATH_ROOT + 'X/output_0/_spark_metadata/0',
        # Backslash as a separator, which some path handlers treat as a delimiter.
        PATH_ROOT + '%5C..%5C_spark_metadata%5C0',
        # Null byte, historically used to truncate a name after validation.
        PATH_ROOT + '/output_0/_spark_metadata/0%00',
        # Raw control character smuggled through the url.
        PATH_ROOT + '/output_0/_spark_metadata/0%0a',
    ])
    def test_main_rejects_paths_outside_the_metadata_directory(self, mocker, bad_path):
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        url = 'https://account.blob.core.windows.net/{}/{}'.format(METADATA_CONTAINER, bad_path)
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(url))
        assert mock_get_blob_content.call_count == 0

    def test_main_rejects_another_container_in_the_same_account(self, mocker):
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        url = 'https://account.blob.core.windows.net/private/{}'.format(CHECKPOINT_BLOB)
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(url))
        assert mock_get_blob_content.call_count == 0

    def test_main_fails_closed_without_a_container(self, mocker, monkeypatch):
        # Naming the account is not enough on its own; without a container the
        # function would accept any blob in the account.
        monkeypatch.setenv('ALLOWED_METADATA_CONTAINERS', '')
        metadatahandler.init_config_values()
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(CHECKPOINT_URL))
        assert mock_get_blob_content.call_count == 0

    @pytest.mark.parametrize('setting', ['METADATA_PATH_ROOT', 'METADATA_REQUIRED_SEGMENT'])
    def test_main_fails_closed_on_blank_policy(self, mocker, monkeypatch, setting):
        # A blank setting must deny rather than quietly skip its check, otherwise a
        # partial deployment widens the function instead of breaking loudly.
        monkeypatch.setenv(setting, '')
        metadatahandler.init_config_values()
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(CHECKPOINT_URL))
        assert mock_get_blob_content.call_count == 0

    def test_root_comparison_is_case_sensitive(self, mocker, monkeypatch):
        # Azure blob names are case sensitive, so the directory comparison must be
        # too. Accepting a differently cased spelling would name a different blob.
        monkeypatch.setenv('METADATA_PATH_ROOT', 'DataBricks-Out')
        metadatahandler.init_config_values()
        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(CHECKPOINT_URL))
        assert mock_get_blob_content.call_count == 0

    def test_main_fails_closed_without_configuration(self, mocker, monkeypatch):
        monkeypatch.setenv('DATABRICKS_OUTPUT_STORAGE_ACCOUNT_URL', '')
        metadatahandler.init_config_values()
        assert metadatahandler.ALLOWED_STORAGE_HOSTS == set()

        mock_get_blob_content = mocker.patch('__app__.metadatahandler.get_blob_content')
        with pytest.raises(metadatahandler.ValidationError):
            metadatahandler.main(self._metadata_message(CHECKPOINT_URL))
        assert mock_get_blob_content.call_count == 0

    def test_allowed_hosts_cover_both_blob_and_dfs_endpoints(self):
        # Databricks emits dfs (ADLS Gen2) urls while the blob sdk uses blob urls;
        # both address the same account and must both be accepted.
        assert metadatahandler.ALLOWED_STORAGE_HOSTS == {
            'account.blob.core.windows.net', 'account.dfs.core.windows.net'}

    def test_get_part_number_reports_no_part_number_for_a_malformed_marker(self):
        # A checkpoint line is written upstream, so the characters after the marker
        # are not guaranteed to be digits. One bad line must not fail the file.
        assert metadatahandler.get_part_number('output/part-abcde.json') == -1
        assert metadatahandler.get_part_number('output/part-00007-x.json') == 7

    def test_skipped_checkpoint_paths_cannot_forge_log_records(self, caplog):
        # A checkpoint entry is untrusted content. A newline in a rejected path
        # must arrive escaped so it cannot fabricate an extra log record.
        event_time = '2020-09-07T06:43:03.2126947Z'
        metadata_file_content = (
            'v1\n'
            '{"path":"abfss://data@account.dfs.core.windows.net/'
            'unrelated/part-0\\nWARNING:root:forged entry.json",'
            '"size":1,"modificationTime":1599182552000}'
        )
        with caplog.at_level(logging.WARNING):
            actual = metadatahandler.generate_metadata_queue_messages(
                event_time, metadata_file_content)

        assert actual == []
        assert caplog.records, 'the skipped entry should be reported'
        for record in caplog.records:
            assert '\n' not in record.getMessage()

    def test_generate_metadata_queue_messages_skips_references_outside_the_pipeline(self):
        # The metadata file content also selects destinations for the downstream
        # ingest function, so entries outside this account, container or output
        # directory must not be forwarded.
        event_time = '2020-09-07T06:43:03.2126947Z'
        entry = ('{{"path":"{}","size":1,"modificationTime":1599182552000}}')
        metadata_file_content = "\n".join([
            'v1',
            entry.format(OUTPUT_ABFSS.format(1)),
            # Another storage account.
            entry.format('abfss://data@attacker.dfs.core.windows.net/'
                         + PATH_ROOT + '/bad.json'),
            # Another container in the same account.
            entry.format('abfss://private@account.dfs.core.windows.net/'
                         + PATH_ROOT + '/bad.json'),
            # The right container, but outside the Databricks output directory.
            entry.format('abfss://data@account.dfs.core.windows.net/unrelated/bad.json'),
        ])
        actual = metadatahandler.generate_metadata_queue_messages(event_time, metadata_file_content)
        assert len(actual) == 1
        assert OUTPUT_HTTPS.format(1) in actual[0]
        assert 'attacker' not in actual[0]
        assert 'private' not in actual[0]
        assert 'unrelated' not in actual[0]
