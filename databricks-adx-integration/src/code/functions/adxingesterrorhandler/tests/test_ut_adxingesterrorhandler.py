import json
import logging
import pytest

import azure.functions as func
from azure.core.exceptions import ResourceNotFoundError
import __app__.errorhandler as errorhandler
import __app__.errorhandler.validation as validation

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
        # get_config_values() reads each setting as os.getenv(NAME, <current global>),
        # so a value set by a previous test survives monkeypatch's env cleanup and
        # would leak into the next one. Reset the globals this suite varies.
        errorhandler.SOURCE_PATH_ROOT = ''
        errorhandler.SOURCE_FILE_SUFFIX = '.c000.json'
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
        # Backslash as a separator, which some path handlers treat as a delimiter.
        'databricks-out%5C..%5Csecret.c000.json',
        # Null byte, historically used to truncate a name after validation.
        'databricks-out/part%00.c000.json',
    ])
    def test_get_blob_info_from_url_rejects_traversal(self, bad_path):
        url = 'https://test.blob.core.windows.net/{}/{}'.format(SOURCE_CONTAINER, bad_path)
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(url)

    def test_double_encoded_traversal_stays_a_literal_name(self):
        # A doubly encoded sequence decodes once to literal percent text, not to a
        # traversal, so it is a legal blob name and must be accepted as written.
        url = 'https://test.blob.core.windows.net/{}/{}/%252e%252e%252fpart.c000.json'.format(
            SOURCE_CONTAINER, PATH_ROOT)
        _, blob_path = errorhandler.get_blob_info_from_url(url)
        assert blob_path.endswith('%2e%2e%2fpart.c000.json')

    def test_validated_path_is_the_path_that_would_be_requested(self):
        # The value the validator approves must be the value the sdk addresses. If
        # the two ever diverge, validation could pass for one blob while a
        # different one is copied and deleted.
        from azure.storage.blob import BlobClient
        from urllib.parse import unquote, urlsplit

        for name in ['part-0.c000.json', 'my file.c000.json', '%2e%2e%2fpart.c000.json',
                     'caf\u00e9.c000.json', 'cafe\u0301.c000.json']:
            source = 'https://test.blob.core.windows.net/{}/{}/{}'.format(
                SOURCE_CONTAINER, PATH_ROOT, name.replace('%', '%25').replace(' ', '%20'))
            container, blob_path = errorhandler.get_blob_info_from_url(source)
            requested = BlobClient(
                'https://test.blob.core.windows.net', container, blob_path).url
            addressed = unquote(urlsplit(requested).path).lstrip('/')
            assert addressed == '{}/{}'.format(container, blob_path)

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

    @pytest.mark.parametrize('setting', ['SOURCE_PATH_ROOT', 'SOURCE_FILE_SUFFIX'])
    def test_get_blob_info_from_url_fails_closed_on_blank_policy(self, monkeypatch, setting):
        # A blank setting must deny rather than quietly skip its check, otherwise a
        # partial deployment widens the function instead of breaking loudly.
        monkeypatch.setenv(setting, '')
        errorhandler.get_config_values()
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(BLOB_URL)

    def test_root_comparison_is_case_sensitive(self, monkeypatch):
        # Azure blob names are case sensitive, so the directory comparison must be
        # too. Accepting a differently cased spelling would name a different blob.
        monkeypatch.setenv('SOURCE_PATH_ROOT', 'DataBricks-Out')
        errorhandler.get_config_values()
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(BLOB_URL)

    def test_allowed_hosts_cover_both_blob_and_dfs_endpoints(self):
        # Databricks emits dfs (ADLS Gen2) urls while the blob sdk uses blob urls;
        # both address the same account and must both be accepted.
        assert errorhandler.ALLOWED_STORAGE_HOSTS == {
            'test.blob.core.windows.net', 'test.dfs.core.windows.net'}

    def test_a_custom_endpoint_does_not_admit_lookalike_hosts(self):
        # Only a real Azure Storage endpoint has a service label to swap. A custom
        # domain shaped like one says nothing about who owns its sibling.
        def hosts(endpoint):
            return validation.storage_hosts_from_connection_string(
                'DefaultEndpointsProtocol=https;AccountName=storage;'
                'AccountKey=PLACEHOLDER-NOT-A-REAL-KEY==;'
                'BlobEndpoint=https://' + endpoint)

        assert hosts('storage.example.com') == {'storage.example.com'}
        assert hosts('storage.blob.example.com') == {'storage.blob.example.com'}
        assert hosts('storage.dfs.example.com') == {'storage.dfs.example.com'}
        assert hosts('account.blob.core.windows.net') == {
            'account.blob.core.windows.net', 'account.dfs.core.windows.net'}

    @pytest.mark.parametrize('tenant', ['tenant-retry1', 'tenant-retry2', 'tenant-retry3'])
    def test_rewriting_the_retry_generation_leaves_the_tenant_alone(self, tenant):
        # The partition value is the tenant, and it can legitimately contain the
        # same text as a retry directory. Rewriting it would send the next
        # ingestion to a different customer's database.
        base = PATH_ROOT + '/companyIdkey=' + tenant + '/typekey=T'
        for generation in (1, 2):
            container, path = errorhandler.get_new_blob_move_file_path(
                SOURCE_CONTAINER, base + '/retry{}/part-uuid.c000.json'.format(generation))
            assert container == SOURCE_CONTAINER
            assert path == base + '/retry{}/part-uuid.c000.json'.format(generation + 1)

        # At the final generation the retry directory is removed, and nothing else.
        container, path = errorhandler.get_new_blob_move_file_path(
            SOURCE_CONTAINER, base + '/retry3/part-uuid.c000.json')
        assert container == errorhandler.RETRY_END_IN_FAIL_CONTAINER_NAME
        assert path == base + '/part-uuid.c000.json'

        # A blob with no retry directory gains one directly above the file name.
        container, path = errorhandler.get_new_blob_move_file_path(
            SOURCE_CONTAINER, base + '/part-uuid.c000.json')
        assert container == SOURCE_CONTAINER
        assert path == base + '/retry1/part-uuid.c000.json'

    def test_the_retry_reader_and_writer_use_the_same_slot(self):
        # A directory further up can legitimately be named retry1, for example a
        # nested output root. If the reader looked there while the writer wrote
        # above the file name, the blob would collect two generations and then be
        # refused for the rest of its life. Such a directory is ordinary path data.
        path = PATH_ROOT + '/retry1/companyIdkey=c/typekey=T/part-uuid.c000.json'
        assert errorhandler.get_blob_retry_times(path) == 0
        assert errorhandler.get_blob_retry_times(
            PATH_ROOT + '/retry1/retry2/part-uuid.c000.json') == 2

        container, first = errorhandler.get_new_blob_move_file_path(SOURCE_CONTAINER, path)
        assert first == PATH_ROOT + '/retry1/companyIdkey=c/typekey=T/retry1/part-uuid.c000.json'
        assert errorhandler.get_blob_retry_times(first) == 1

        container, second = errorhandler.get_new_blob_move_file_path(SOURCE_CONTAINER, first)
        assert second == PATH_ROOT + '/retry1/companyIdkey=c/typekey=T/retry2/part-uuid.c000.json'
        assert errorhandler.get_blob_retry_times(second) == 2

    @pytest.mark.parametrize('segment', ['retry\u0661', 'retry\uff11'])
    def test_only_ascii_digits_make_a_retry_segment(self, segment):
        # int() accepts these digits, so a lookalike directory would otherwise be
        # read as a generation and could send the blob to the give-up container.
        assert not validation.is_retry_segment(segment)
        assert errorhandler.get_blob_retry_times(
            PATH_ROOT + '/' + segment + '/part-uuid.c000.json') == 0

    @pytest.mark.parametrize('copy_status', ['pending', 'failed', 'aborted', None])
    def test_the_source_is_kept_unless_the_copy_succeeded(self, mocker, copy_status):
        # The source is the only copy of the payload. Deleting it before the
        # destination holds the data would leave nothing to retry from.
        source, target = mocker.Mock(), mocker.Mock()
        service = mocker.Mock()
        service.get_blob_client.side_effect = [source, target]
        mocker.patch.object(errorhandler.BlobServiceClient, 'from_connection_string',
                            return_value=service)
        target.get_blob_properties.side_effect = ResourceNotFoundError('missing')
        target.start_copy_from_url.return_value = (
            None if copy_status is None else {'copy_status': copy_status})

        with pytest.raises(RuntimeError):
            errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')
        source.delete_blob.assert_not_called()

    def test_a_completed_copy_from_a_redelivery_is_adopted(self, mocker):
        # The queue redelivers and the destination path is derived from the source,
        # so an earlier attempt may already have done the copy. Finishing that move
        # is better than starting a competing one.
        source, target = mocker.Mock(), mocker.Mock()
        source.url = 'https://test.blob.core.windows.net/data/a/b.json'
        service = mocker.Mock()
        service.get_blob_client.side_effect = [source, target]
        mocker.patch.object(errorhandler.BlobServiceClient, 'from_connection_string',
                            return_value=service)
        target.get_blob_properties.return_value = mocker.Mock(
            copy=mocker.Mock(source=source.url + '?sig=x', status='success'))

        errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')

        target.start_copy_from_url.assert_not_called()
        source.delete_blob.assert_called_once()

    def test_a_destination_copied_from_somewhere_else_is_not_adopted(self, mocker):
        # Only a copy of this exact source says the payload is safe.
        source, target = mocker.Mock(), mocker.Mock()
        source.url = 'https://test.blob.core.windows.net/data/a/b.json'
        service = mocker.Mock()
        service.get_blob_client.side_effect = [source, target]
        mocker.patch.object(errorhandler.BlobServiceClient, 'from_connection_string',
                            return_value=service)
        target.get_blob_properties.return_value = mocker.Mock(
            copy=mocker.Mock(source='https://test.blob.core.windows.net/data/other.json',
                             status='success'))
        target.start_copy_from_url.return_value = {'copy_status': 'success'}

        errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')

        target.start_copy_from_url.assert_called_once()
        source.delete_blob.assert_called_once()

    def test_a_redelivery_after_the_move_completed_is_not_an_error(self, mocker):
        # Storage queues deliver at least once, so the same message can arrive after
        # the move already finished. The destination holds this source's data and
        # the source is gone, which is the completed state. Raising would send a
        # message whose work succeeded to the poison queue.
        source, target = mocker.Mock(), mocker.Mock()
        source.url = 'https://test.blob.core.windows.net/data/a/b.json'
        service = mocker.Mock()
        service.get_blob_client.side_effect = [source, target]
        mocker.patch.object(errorhandler.BlobServiceClient, 'from_connection_string',
                            return_value=service)
        target.get_blob_properties.return_value = mocker.Mock(
            copy=mocker.Mock(source=source.url, status='success'))
        source.delete_blob.side_effect = ResourceNotFoundError('already moved')

        errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')

        target.start_copy_from_url.assert_not_called()

    def test_a_missing_source_is_still_an_error_when_no_copy_completed(self, mocker):
        # Without a completed destination copy there is no evidence the move ever
        # happened, so a missing source is a real failure.
        source, target = mocker.Mock(), mocker.Mock()
        source.url = 'https://test.blob.core.windows.net/data/a/b.json'
        service = mocker.Mock()
        service.get_blob_client.side_effect = [source, target]
        mocker.patch.object(errorhandler.BlobServiceClient, 'from_connection_string',
                            return_value=service)
        target.get_blob_properties.side_effect = ResourceNotFoundError('missing')
        target.start_copy_from_url.return_value = {'copy_status': 'pending'}

        with pytest.raises(RuntimeError):
            errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')
        source.delete_blob.assert_not_called()

    def test_the_source_is_kept_when_the_copy_has_not_completed(self, mocker):
        # The source is the only copy of the payload. Deleting it while the copy is
        # still pending would leave nothing to retry from.
        source, target = mocker.Mock(), mocker.Mock()
        service = mocker.Mock()
        service.get_blob_client.side_effect = [source, target]
        mocker.patch.object(errorhandler.BlobServiceClient, 'from_connection_string',
                            return_value=service)
        target.get_blob_properties.side_effect = ResourceNotFoundError('missing')

        target.start_copy_from_url.return_value = {'copy_status': 'pending'}
        with pytest.raises(RuntimeError):
            errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')
        source.delete_blob.assert_not_called()

        service.get_blob_client.side_effect = [source, target]
        target.start_copy_from_url.return_value = {'copy_status': 'success'}
        errorhandler.move_blob_file('cs', 'data', 'data', 'a/b.json', 'a/retry1/b.json')
        source.delete_blob.assert_called_once()

    def test_a_url_carrying_a_fragment_is_refused_and_not_logged(self):
        # A blob request drops the fragment, so it reaches nothing but the logs.
        with pytest.raises(errorhandler.ValidationError):
            errorhandler.get_blob_info_from_url(BLOB_URL + '#access_token=SECRET')
        assert 'SECRET' not in validation.redact_url(BLOB_URL + '#access_token=SECRET')

    @pytest.mark.parametrize('url,expected', [
        # A rejected url reaches the log before anything has vouched for its shape.
        ('https://acct.blob.core.windows.net/data/p\nWARNING:root:forged',
         'https://acct.blob.core.windows.net/data/p\\x0aWARNING:root:forged'),
        ('https://user:secret@acct.blob.core.windows.net/data/p?sig=x',
         'https://acct.blob.core.windows.net/data/p?<redacted>'),
        ('https://acct.blob.core.windows.net/data/p?sig=x',
         'https://acct.blob.core.windows.net/data/p?<redacted>'),
        # A url that never had a scheme still has an authority to clean.
        ('//user:secret@acct.blob.core.windows.net/data/p', '//acct.blob.core.windows.net/data/p'),
    ])
    def test_redacted_urls_carry_no_credentials_and_cannot_forge_records(self, url, expected):
        redacted = validation.redact_url(url)
        assert redacted == expected
        assert 'secret' not in redacted
        assert '\n' not in redacted

    def test_a_nested_output_directory_is_accepted(self, monkeypatch):
        # The configured folder also drives the Databricks output path and the
        # event grid subject filter, both of which accept nested paths. Rejecting
        # one here would deploy cleanly and then refuse every blob.
        monkeypatch.setenv('SOURCE_PATH_ROOT', 'landing/' + PATH_ROOT)
        errorhandler.get_config_values()
        nested = BLOB_URL.replace('/' + PATH_ROOT + '/', '/landing/' + PATH_ROOT + '/')

        assert errorhandler.get_blob_info_from_url(nested)
        with pytest.raises(errorhandler.ValidationError):
            # A path that matches only the first configured segment is still out.
            errorhandler.get_blob_info_from_url(
                BLOB_URL.replace('/' + PATH_ROOT + '/', '/landing/'))

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