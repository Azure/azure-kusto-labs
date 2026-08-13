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

# The container and directory the deployment ingests from, matching
# Storage.FileSystemName and Storage.AzureStorageTargetFolder in provision-config.
SOURCE_CONTAINER = 'data'
PATH_ROOT = 'databricks-out'
BLOB_PATH = PATH_ROOT + '/companyIdkey=company-id-0/typekey=TEMP/part-uuid.c000.json'
RETRY_PATH = PATH_ROOT + '/companyIdkey=company-id-0/typekey=TEMP/retry1/part-uuid.c000.json'
BLOB_URL = 'https://test.blob.core.windows.net/{}/{}'.format(SOURCE_CONTAINER, BLOB_PATH)

class TestUtAdxIngestErrorHandler():
    @pytest.fixture(autouse=True)
    def configure_function(self, monkeypatch, mocker):
        """ Apply the function app configuration the deployment provides. """
        monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', FAKE_CONNECTION_STRING)
        monkeypatch.setenv('ALLOWED_SOURCE_CONTAINERS', SOURCE_CONTAINER)
        monkeypatch.setenv('SOURCE_PATH_ROOT', PATH_ROOT)
        # Never emit real telemetry from a unit test. The App Insights sender
        # retries against the live endpoint and otherwise dominates the runtime
        # of the whole suite. patch.object is undone properly after each test,
        # unlike assigning over the module attribute directly.
        mocker.patch.object(errorhandler, 'TelemetryClient')
        errorhandler.get_config_values()

    def test_main(self, mocker):
        msg_body = {
            "eventType": "Microsoft.Storage.BlobCreated",
            "eventTime": "2020-08-18T17:02:19.6069787Z",
            "id": "{guid}",
            "data": {
                "api": "PutBlockList",
                "contentLength": 4194349,
                "blobType": "BlockBlob",
                "url": BLOB_URL
            }
        }

        req = func.QueueMessage(body=json.dumps(msg_body))
        mock_move_blob_file = mocker.patch('__app__.errorhandler.move_blob_file')
        mock_move_blob_file.return_value = None
        errorhandler.move_blob_file = mock_move_blob_file
        
        spy_retry_blob_ingest_to_adx = mocker.spy(errorhandler, 'retry_blob_ingest_to_adx')

        errorhandler.main(req)
        spy_retry_blob_ingest_to_adx.assert_called_once_with(
            SOURCE_CONTAINER, BLOB_PATH, SOURCE_CONTAINER, RETRY_PATH)

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
        assert errorhandler.get_blob_retry_times(BLOB_PATH) == 0
        assert errorhandler.get_blob_retry_times(RETRY_PATH) == 1

    @pytest.mark.parametrize('bad_path', [
        # A generation far beyond the configured maximum would send the blob
        # straight to the final failure container and delete the original.
        PATH_ROOT + '/a/retry999/part-uuid.c000.json',
        # retry0 is never written by this function.
        PATH_ROOT + '/a/retry0/part-uuid.c000.json',
        # Two generations leave the intended one ambiguous.
        PATH_ROOT + '/a/retry1/retry2/part-uuid.c000.json',
    ])
    def test_get_blob_retry_times_rejects_unusable_generations(self, bad_path):
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_retry_times(bad_path)

    def test_get_blob_retry_times_ignores_lookalike_directories(self):
        # A directory that merely contains the word must not be read as a
        # generation, otherwise an ordinary file name could force a final failure.
        assert errorhandler.get_blob_retry_times(
            PATH_ROOT + '/notaretry999folder/part-uuid.c000.json') == 0

    def test_get_blob_info_from_url(self):
        actual_container, actual_blob_path = errorhandler.get_blob_info_from_url(BLOB_URL)
        assert actual_container == SOURCE_CONTAINER
        assert actual_blob_path == BLOB_PATH

    def test_get_blob_info_from_url_allows_a_space_in_the_blob_name(self):
        # Spaces are legal in Azure blob names, so a percent encoded space must
        # survive validation once the sdk has decoded it.
        url = 'https://test.blob.core.windows.net/{}/{}/my%20file.c000.json'.format(
            SOURCE_CONTAINER, PATH_ROOT)
        _, blob_path = errorhandler.get_blob_info_from_url(url)
        assert blob_path.endswith('my file.c000.json')

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
            errorhandler.retry_blob_ingest_to_adx(
                SOURCE_CONTAINER, BLOB_PATH, SOURCE_CONTAINER, RETRY_PATH)
        assert spy_move_blob_file.call_count == errorhandler.BLOB_REQ_MAX_ATTEMPT

    # --- Validation of the queue supplied blob url ---

    @pytest.mark.parametrize('bad_host', [
        # Different storage account entirely.
        'attacker.blob.core.windows.net',
        # Lookalike host that only shares a prefix with the allowed host.
        'test.blob.core.windows.net.attacker.example',
        # Credentials embedded to confuse naive host parsing.
        'test.blob.core.windows.net:pwd@attacker.example',
    ])
    def test_get_blob_info_from_url_rejects_off_account_urls(self, bad_host):
        url = 'https://{}/{}/{}'.format(bad_host, SOURCE_CONTAINER, BLOB_PATH)
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(url)

    @pytest.mark.parametrize('bad_url', [
        # Non https schemes.
        'http://test.blob.core.windows.net/data/databricks-out/part-uuid.c000.json',
        'file:///etc/passwd',
        # Control characters used to smuggle values past url parsers.
        'https://test.blob.core.windows.net/data/databricks-out/part\n.c000.json',
    ])
    def test_get_blob_info_from_url_rejects_unusable_urls(self, bad_url):
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(bad_url)

    @pytest.mark.parametrize('bad_path', [
        '../../other-container/secret.c000.json',
        'a/../../../secret.c000.json',
        # Percent encoded traversal, decoded by the storage sdk before it reaches
        # the sink, so it must be validated after the sdk has resolved it.
        '%2e%2e%2f%2e%2e%2fsecret.c000.json',
    ])
    def test_get_blob_info_from_url_rejects_traversal(self, bad_path):
        url = 'https://test.blob.core.windows.net/{}/{}'.format(SOURCE_CONTAINER, bad_path)
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(url)

    def test_get_blob_info_from_url_fails_closed_without_configuration(self, monkeypatch):
        monkeypatch.setenv('AZURE_STORAGE_CONNECTION_STRING', '')
        errorhandler.get_config_values()
        assert errorhandler.ALLOWED_STORAGE_HOSTS == set()
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(BLOB_URL)

    def test_get_blob_info_from_url_fails_closed_without_a_container(self, monkeypatch):
        # Naming the account is not enough on its own; without a container the
        # function would accept any blob in the account.
        monkeypatch.setenv('ALLOWED_SOURCE_CONTAINERS', '')
        errorhandler.get_config_values()
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(BLOB_URL)

    def test_allowed_hosts_cover_both_blob_and_dfs_endpoints(self):
        # Databricks emits dfs (ADLS Gen2) urls while the blob sdk uses blob urls;
        # both address the same account and must both be accepted.
        assert errorhandler.ALLOWED_STORAGE_HOSTS == {
            'test.blob.core.windows.net', 'test.dfs.core.windows.net'}

    @pytest.mark.parametrize('container,blob_path', [
        # A real container in the same account, but not the one this app serves.
        ('private', PATH_ROOT + '/part-uuid.c000.json'),
        # The right container, but outside the directory the pipeline writes to.
        (SOURCE_CONTAINER, 'unrelated/critical.c000.json'),
        # A sibling directory whose name merely starts with the expected one.
        (SOURCE_CONTAINER, PATH_ROOT + 'X/part-uuid.c000.json'),
        # The right directory, but not a file this pipeline produces.
        (SOURCE_CONTAINER, PATH_ROOT + '/payroll.csv'),
    ])
    def test_get_blob_info_from_url_rejects_blobs_outside_the_pipeline(self, container, blob_path):
        url = 'https://test.blob.core.windows.net/{}/{}'.format(container, blob_path)
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(url)

    def test_main_rejects_off_account_url_before_moving_anything(self, mocker):
        spy_move_blob_file = mocker.spy(errorhandler, 'move_blob_file')
        msg_body = {
            "data": {"url": 'https://attacker.blob.core.windows.net/data/databricks-out/p.c000.json'}
        }
        req = func.QueueMessage(body=json.dumps(msg_body))

        with pytest.raises(errorhandler.ValidationError):
            errorhandler.main(req)
        # The copy/delete must not have been attempted at all.
        assert spy_move_blob_file.call_count == 0

    @pytest.mark.parametrize('container,blob_path', [
        (SOURCE_CONTAINER, '../escaped/part-uuid.c000.json'),
        # A destination outside the pipeline directory, which is where the copy
        # would land and the source would be deleted from.
        (SOURCE_CONTAINER, 'unrelated/part-uuid.c000.json'),
        ('private', PATH_ROOT + '/part-uuid.c000.json'),
    ])
    def test_retry_blob_ingest_to_adx_rejects_unusable_destination(self, mocker, container, blob_path):
        spy_move_blob_file = mocker.spy(errorhandler, 'move_blob_file')
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.retry_blob_ingest_to_adx(
                SOURCE_CONTAINER, BLOB_PATH, container, blob_path)
        assert spy_move_blob_file.call_count == 0

    def test_retry_blob_ingest_to_adx_allows_the_final_failure_container(self, mocker):
        # The terminal move targets a different container by design, so it must not
        # be blocked by the source container boundary.
        mocker.patch('__app__.errorhandler.move_blob_file', return_value=None)
        errorhandler.retry_blob_ingest_to_adx(
            SOURCE_CONTAINER, BLOB_PATH,
            errorhandler.RETRY_END_IN_FAIL_CONTAINER_NAME, BLOB_PATH)