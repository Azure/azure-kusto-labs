import json
import logging
import pytest

import azure.functions as func
import __app__.errorhandler as errorhandler

# The function derives the storage account it is allowed to act on from its own
# connection string, so the tests must supply one just as the deployment does.
# The key is a placeholder; only AccountName and EndpointSuffix are read. The
# trailing '==' is kept so the parser is exercised against a value that itself
# contains the separator character.
FAKE_CONNECTION_STRING = ('DefaultEndpointsProtocol=https;AccountName=test;'
                          'AccountKey=PLACEHOLDER-NOT-A-REAL-KEY==;'
                          'EndpointSuffix=core.windows.net')

class TestUtAdxIngestErrorHandler():
    @pytest.fixture(autouse=True)
    def configure_function(self, monkeypatch, mocker):
        """ Apply the function app configuration the deployment provides. """
        monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', FAKE_CONNECTION_STRING)
        # Never emit real telemetry from a unit test. The App Insights sender
        # retries against the live endpoint and otherwise dominates the runtime
        # of the whole suite. patch.object is undone properly after each test,
        # unlike assigning over the module attribute directly.
        mocker.patch.object(errorhandler, 'TelemetryClient')
        errorhandler.get_config_values()

    def test_main(self, mocker):
        fake_container = 'split'
        fake_path = '2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        fake_new_path = '2020/08/17/17/00/customerId=cId/pname=sao/retry1/part-uuid.c000.json'
        fake_url = 'https://test.blob.core.windows.net/{}/{}'.format(
            fake_container,
            fake_path
        )
        msg_body = {
            "eventType": "Microsoft.Storage.BlobCreated",
            "eventTime": "2020-08-18T17:02:19.6069787Z",
            "id": "{guid}",
            "data": {
                "api": "PutBlockList",
                "contentLength": 4194349,
                "blobType": "BlockBlob",
                "url": fake_url
            }
        }

        req = func.QueueMessage(body=json.dumps(msg_body))
        mock_move_blob_file = mocker.patch('__app__.errorhandler.move_blob_file')
        mock_move_blob_file.return_value = None
        errorhandler.move_blob_file = mock_move_blob_file
        
        spy_retry_blob_ingest_to_adx = mocker.spy(errorhandler, 'retry_blob_ingest_to_adx')

        errorhandler.main(req)
        spy_retry_blob_ingest_to_adx.assert_called_once_with(fake_container, fake_path, fake_container, fake_new_path)

    def test_get_new_blob_move_file_path(self):
        # case no-retry: <folder path>/<filename> -> <folder path>/<filename> in retryEndInFail container
        fake_src_container = 'container'
        fake_src_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        expected_dest_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'

        actual_container, actual_path = errorhandler.get_new_blob_move_file_path(fake_src_container, fake_src_path, no_retry=True)
        assert actual_container == errorhandler.RETRY_END_IN_FAIL_CONTAINER_NAME
        assert actual_path == expected_dest_path

        # case retry: <folder path>/<filename> -> <folder path>/retry1/<filename> in same container
        fake_src_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        expected_dest_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/retry1/part-uuid.c000.json'
        actual_container, actual_path = errorhandler.get_new_blob_move_file_path(fake_src_container, fake_src_path)
        assert actual_container == fake_src_container
        assert actual_path == expected_dest_path

        # case retry with no folder: <filename> -> retry1/<filename> in same container
        fake_src_path = 'part-uuid.c000.json'
        expected_dest_path = 'retry1/part-uuid.c000.json'
        actual_container, actual_path = errorhandler.get_new_blob_move_file_path(fake_src_container, fake_src_path)
        assert actual_container == fake_src_container
        assert actual_path == expected_dest_path

        # case retry-end-fail: <folder path>/retryX/<filename> -> retryEndInFail/<folder path>/<filename>
        # in retryEndInFail container
        errorhandler.MAX_INGEST_RETRIES_TIMES = 3
        fake_src_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/retry3/part-uuid.c000.json'
        expected_dest_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        actual_container, actual_path = errorhandler.get_new_blob_move_file_path(fake_src_container, fake_src_path)
        assert actual_container == errorhandler.RETRY_END_IN_FAIL_CONTAINER_NAME
        assert actual_path == expected_dest_path

        # case keep-retry: update the retry<retry_times> to retry<retry_times+1> in same container
        errorhandler.MAX_INGEST_RETRIES_TIMES = 3
        fake_src_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/retry1/part-uuid.c000.json'
        expected_dest_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/retry2/part-uuid.c000.json'
        actual_container, actual_path = errorhandler.get_new_blob_move_file_path(fake_src_container, fake_src_path)
        assert actual_path == expected_dest_path

    def test_get_blob_retry_times(self):
        fake_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        expected = 0
        actual = errorhandler.get_blob_retry_times(fake_path)
        assert actual == expected

        fake_path = 'split/2020/08/17/17/00/customerId=cId/pname=sao/retry1/part-uuid.c000.json'
        expected = 1
        actual = errorhandler.get_blob_retry_times(fake_path)
        assert actual == expected

    def test_get_blob_info_from_url(self):
        fake_url = 'https://test.blob.core.windows.net/split/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        expected_container = 'split'
        expected_blob_path = '2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'

        actual_cotainer, actual_blob_path = errorhandler.get_blob_info_from_url(fake_url)
        assert actual_cotainer == expected_container
        assert actual_blob_path == expected_blob_path

    def test_retry_blob_ingest_to_adx(self, mocker, monkeypatch):
        spy_move_blob_file = mocker.spy(errorhandler, 'move_blob_file')
        # Shorten the backoff. The global is BLOB_REQ_MAX_RETRY_DELAY_SEC; setting
        # any other name leaves the default 60s in place and makes this test sleep
        # through a full minute of real backoff.
        monkeypatch.setenv('BLOB_REQ_MAX_RETRY_DELAY_SEC', '1')
        # Keep move_blob_file failing locally on an unusable connection string
        # rather than attempting to reach a storage account over the network.
        monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', '')
        errorhandler.get_config_values()
        with pytest.raises(Exception):
            errorhandler.retry_blob_ingest_to_adx('fake-container', 'fake_path', 'fake-container', 'fake_new_path')
        assert spy_move_blob_file.call_count == errorhandler.BLOB_REQ_MAX_ATTEMPT

    # --- Validation of the queue supplied blob url ---

    @pytest.mark.parametrize('bad_url', [
        # Different storage account entirely.
        'https://attacker.blob.core.windows.net/split/part-uuid.c000.json',
        # Lookalike host that only shares a prefix with the allowed host.
        'https://test.blob.core.windows.net.attacker.example/split/part-uuid.c000.json',
        # Credentials embedded to confuse naive host parsing.
        'https://test.blob.core.windows.net:pwd@attacker.example/split/part-uuid.c000.json',
        # Non https schemes.
        'http://test.blob.core.windows.net/split/part-uuid.c000.json',
        'file:///etc/passwd',
        # Control characters used to smuggle values past url parsers.
        'https://test.blob.core.windows.net/split/part\n.json',
    ])
    def test_get_blob_info_from_url_rejects_off_account_urls(self, bad_url):
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(bad_url)

    @pytest.mark.parametrize('bad_path', [
        '../../other-container/secret.json',
        'a/../../../secret.json',
        # Percent encoded traversal, decoded by the storage sdk before it reaches
        # the sink, so it must be validated after the sdk has resolved it.
        '%2e%2e%2f%2e%2e%2fsecret.json',
    ])
    def test_get_blob_info_from_url_rejects_traversal(self, bad_path):
        url = 'https://test.blob.core.windows.net/split/{}'.format(bad_path)
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(url)

    def test_get_blob_info_from_url_fails_closed_without_configuration(self, monkeypatch):
        monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', '')
        errorhandler.get_config_values()
        assert errorhandler.ALLOWED_STORAGE_HOSTS == set()
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(
                'https://test.blob.core.windows.net/split/part-uuid.c000.json')

    def test_allowed_hosts_cover_both_blob_and_dfs_endpoints(self):
        # Databricks emits dfs (ADLS Gen2) urls while the blob sdk uses blob urls;
        # both address the same account and must both be accepted.
        assert errorhandler.ALLOWED_STORAGE_HOSTS == {
            'test.blob.core.windows.net', 'test.dfs.core.windows.net'}

    def test_optional_container_allow_list_is_enforced(self, monkeypatch):
        monkeypatch.setenv('ALLOWED_SOURCE_CONTAINERS', 'split, othercontainer')
        errorhandler.get_config_values()

        container, _ = errorhandler.get_blob_info_from_url(
            'https://test.blob.core.windows.net/split/part-uuid.c000.json')
        assert container == 'split'

        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(
                'https://test.blob.core.windows.net/notallowed/part-uuid.c000.json')

    def test_main_rejects_off_account_url_before_moving_anything(self, mocker):
        spy_move_blob_file = mocker.spy(errorhandler, 'move_blob_file')
        msg_body = {
            "data": {"url": 'https://attacker.blob.core.windows.net/split/part-uuid.c000.json'}
        }
        req = func.QueueMessage(body=json.dumps(msg_body))

        with pytest.raises(errorhandler.ValidationError):
            errorhandler.main(req)
        # The copy/delete must not have been attempted at all.
        assert spy_move_blob_file.call_count == 0

    def test_retry_blob_ingest_to_adx_rejects_traversal_destination(self, mocker):
        spy_move_blob_file = mocker.spy(errorhandler, 'move_blob_file')
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.retry_blob_ingest_to_adx(
                'split', 'part-uuid.c000.json', 'split', '../escaped/part-uuid.c000.json')
        assert spy_move_blob_file.call_count == 0