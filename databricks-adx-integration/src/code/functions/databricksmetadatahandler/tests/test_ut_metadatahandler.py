import asyncio
import json
import logging

import __app__.metadatahandler as metadatahandler
import __app__.metadatahandler.validation as validation
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

    def test_a_custom_endpoint_does_not_admit_lookalike_hosts(self):
        # Only a real blob or dfs endpoint has a service label to swap. Swapping
        # the second label of a custom domain would invent a name that somebody
        # else can register, and admit it to the allow-list.
        assert validation.storage_hosts_from_account_url(
            'https://storage.example.com') == {'storage.example.com'}

    @pytest.mark.parametrize('url,expected', [
        # A rejected url reaches the log before anything has vouched for its shape.
        ('https://account.blob.core.windows.net/data/p\nWARNING:root:forged',
         'https://account.blob.core.windows.net/data/p\\x0aWARNING:root:forged'),
        ('https://user:secret@account.queue.core.windows.net/q?sig=x',
         'https://account.queue.core.windows.net/q?<redacted>'),
    ])
    def test_redacted_urls_carry_no_credentials_and_cannot_forge_records(self, url, expected):
        redacted = validation.redact_url(url)
        assert redacted == expected
        assert 'secret' not in redacted
        assert '\n' not in redacted

    def test_a_nested_output_directory_is_accepted(self, monkeypatch):
        # The configured folder also drives the Databricks output path and the
        # event grid subject filter, both of which accept nested paths. Rejecting
        # one here would deploy cleanly and then refuse every checkpoint.
        monkeypatch.setenv('METADATA_PATH_ROOT', 'landing/' + PATH_ROOT)
        metadatahandler.init_config_values()

        assert validation.validate_checkpoint_path(
            'landing/' + CHECKPOINT_BLOB, 'landing/' + PATH_ROOT, '_spark_metadata')
        with pytest.raises(validation.ValidationError):
            # Matching only the first configured segment is still outside.
            validation.validate_checkpoint_path(
                'landing/_spark_metadata/0', 'landing/' + PATH_ROOT, '_spark_metadata')

    def test_get_part_number_reports_no_part_number_for_a_malformed_marker(self):
        # A checkpoint line is written upstream, so the characters after the marker
        # are not guaranteed to be digits. One bad line must not fail the file.
        assert metadatahandler.get_part_number('output/part-abcde.json') == -1
        assert metadatahandler.get_part_number('output/part-00007-x.json') == 7
        assert metadatahandler.get_part_number('part-00007.json') == 7
        assert metadatahandler.get_part_number('output/nomarker.json') == -1

    def test_get_part_number_reads_only_the_spark_file_name(self):
        # Partition directories are named from telemetry, so they must not be able
        # to supply the part number of the file inside them.
        assert metadatahandler.get_part_number(
            'companyIdkey=part-00000/typekey=TEMP/part-00007-uuid.c000.json') == 7
        assert metadatahandler.get_part_number('output/notapart-00000.json') == -1
        # The number is not truncated to a fixed width, and a run too long to be a
        # real part number is treated as unnumbered rather than as a smaller one.
        assert metadatahandler.get_part_number('part-100000-uuid.c000.json') == 100000
        assert metadatahandler.get_part_number('part-123456789012-uuid.c000.json') == -1

    def test_a_partition_named_like_a_part_number_does_not_suppress_the_batch(self):
        # companyIdkey is written straight from the telemetry, so a company id of
        # this shape reaches the path without any traversal or boundary crossing.
        # Read as the file's part number it would set the ceiling to zero and drop
        # every other file in the batch, including from the rewritten checkpoint.
        first = self._checkpoint_line(
            'landingeventqueue0/companyIdkey=c0/typekey=TEMP/part-00001-uuid.c000.json')
        second = self._checkpoint_line(
            'landingeventqueue0/companyIdkey=c0/typekey=TEMP/part-00006-uuid.c000.json')
        partition_lookalike = self._checkpoint_line(
            'landingeventqueue0/companyIdkey=part-00000/typekey=TEMP/part-00007-uuid.c000.json')
        checkpoint = ['v1', first, second, partition_lookalike]

        messages, _ = self._messages_and_retention(checkpoint)
        rewritten = self._rewritten_checkpoint(checkpoint)

        assert len(messages) == 3, 'every file in the batch should be forwarded'
        assert rewritten == checkpoint, 'the whole batch should survive the rewrite'

    def test_a_batch_numbered_past_the_old_fixed_ceiling_is_still_forwarded(self):
        # Now that the full part number is read rather than its first five digits,
        # a job with more than 100000 output files produces numbers that a fixed
        # starting ceiling would have treated as a previous batch, dropping all of
        # them on the first entry.
        checkpoint = ['v1',
                      self._checkpoint_line('q0/c/t/part-100001-uuid.c000.json'),
                      self._checkpoint_line('q0/c/t/part-100002-uuid.c000.json')]

        messages, _ = self._messages_and_retention(checkpoint)

        assert len(messages) == 2, 'a large job should not be mistaken for a previous batch'
        assert self._rewritten_checkpoint(checkpoint) == checkpoint

    def _checkpoint_line(self, name, size=1):
        return json.dumps({
            'path': 'abfss://{}@account.dfs.core.windows.net/{}/{}'.format(
                METADATA_CONTAINER, PATH_ROOT, name),
            'size': size,
            'modificationTime': 1599182552000,
        })

    def _messages_and_retention(self, lines):
        metadatahandler.MAX_COMPACT_FILE_RECORDS = 0
        messages = metadatahandler.generate_metadata_queue_messages(
            '2020-09-07T06:43:03.2126947Z', '\n'.join(lines))
        return messages, metadatahandler.MAX_COMPACT_FILE_RECORDS

    def _rewritten_checkpoint(self, lines):
        # Mirrors what main() uploads over a compact checkpoint: the retained line
        # count is decided while generating messages, then applied to the file.
        _, retention = self._messages_and_retention(lines)
        return metadatahandler.get_shrinked_checkpoint_content(
            '\n'.join(lines), retention).splitlines()

    @pytest.mark.parametrize('extra_entry_kind', ['rejected', 'missing_field', 'unordered'])
    def test_trimming_a_compact_checkpoint_never_drops_an_accepted_entry(self, extra_entry_kind):
        # The retained window is a trailing slice of the raw file. If it were sized
        # by messages produced rather than lines scanned, an entry this function
        # skipped would occupy a slot and push an accepted entry out of the file,
        # which the overwrite would then make permanent.
        first = self._checkpoint_line('splitdata/output_0/part-00001.c000.json')
        second = self._checkpoint_line('splitdata/output_0/part-00007.c000.json')
        valid = ['v1', first, second]
        extra = {
            'rejected': self._checkpoint_line('../elsewhere/part-00000.c000.json'),
            'missing_field': json.dumps({
                'path': 'abfss://{}@account.dfs.core.windows.net/{}/'
                        'splitdata/output_0/part-00002.c000.json'.format(
                            METADATA_CONTAINER, PATH_ROOT),
                'size': 1,
            }),
            'unordered': self._checkpoint_line('splitdata/output_0/part-abcde.c000.json'),
        }[extra_entry_kind]

        baseline = self._rewritten_checkpoint(valid)
        assert baseline == valid, 'a checkpoint of one batch should survive intact'

        rewritten = self._rewritten_checkpoint(valid + [extra])

        assert rewritten[0] == 'v1', 'the header must be preserved'
        assert first in rewritten, 'the oldest accepted entry must not be displaced'
        assert second in rewritten
        assert extra in rewritten, \
            'a line this deployment does not act on is still the producer\'s to keep'

    def test_trimming_a_multi_batch_checkpoint_keeps_the_whole_current_batch(self):
        # A real compact checkpoint holds earlier batches too, so trimming actually
        # removes lines here. The current batch must survive whole even when a
        # skipped line sits inside it.
        older = [self._checkpoint_line('splitdata/output_0/part-00005.c000.json'),
                 self._checkpoint_line('splitdata/output_0/part-00006.c000.json')]
        first = self._checkpoint_line('splitdata/output_0/part-00001.c000.json')
        second = self._checkpoint_line('splitdata/output_0/part-00002.c000.json')
        rejected = self._checkpoint_line('../elsewhere/part-00000.c000.json')

        rewritten = self._rewritten_checkpoint(['v1'] + older + [first, second, rejected])

        assert rewritten[0] == 'v1', 'the header must be preserved'
        assert first in rewritten, 'the oldest accepted entry must not be displaced'
        assert second in rewritten
        assert older[0] not in rewritten, 'the earlier batch should still be trimmed away'

    @pytest.mark.parametrize('rejected_entry', [
        # Well formed part number, but outside the output root this deployment
        # serves, and carrying the lowest number a batch can contain.
        '../elsewhere/part-00000.c000.json',
        # Same idea, addressed through a container this deployment does not serve.
        None,
    ])
    def test_a_rejected_entry_leaves_the_batch_untouched(self, rejected_entry):
        # The checkpoint is walked in reverse, so an entry appended last is seen
        # first. A rejected entry must not become the batch-order ceiling and cut
        # the scan short, which would drop valid files and shrink the retained
        # record count used when a compact checkpoint is rewritten.
        valid = ['v1',
                 self._checkpoint_line('splitdata/output_0/part-00001.c000.json'),
                 self._checkpoint_line('splitdata/output_0/part-00007.c000.json')]
        if rejected_entry is None:
            extra = json.dumps({
                'path': 'abfss://private@account.dfs.core.windows.net/'
                        + PATH_ROOT + '/part-00000.c000.json',
                'size': 1,
                'modificationTime': 1599182552000,
            })
        else:
            extra = self._checkpoint_line(rejected_entry)

        expected_messages, expected_retention = self._messages_and_retention(valid)
        actual_messages, actual_retention = self._messages_and_retention(valid + [extra])

        assert len(expected_messages) == 2, 'the valid checkpoint should produce two messages'
        assert actual_messages == expected_messages
        # Retention counts lines scanned, so it may grow to cover the extra line but
        # must never shrink, which is what would push an accepted entry out.
        assert actual_retention >= expected_retention

    def test_an_entry_without_a_part_number_does_not_truncate_the_batch(self):
        # A name that carries no usable part number says nothing about batch order.
        # It is still inside the output directory, so it is forwarded rather than
        # dropped, and the valid entries after it must survive.
        valid = ['v1',
                 self._checkpoint_line('splitdata/output_0/part-00001.c000.json'),
                 self._checkpoint_line('splitdata/output_0/part-00007.c000.json')]
        unordered = self._checkpoint_line('splitdata/output_0/part-abcde.c000.json')

        expected_messages, expected_retention = self._messages_and_retention(valid)
        actual_messages, actual_retention = self._messages_and_retention(valid + [unordered])

        assert len(expected_messages) == 2, 'the valid checkpoint should produce two messages'
        assert all(message in actual_messages for message in expected_messages), \
            'the valid entries must still be forwarded'
        assert len(actual_messages) == 3, 'the unordered entry is forwarded, not dropped'
        assert actual_retention >= expected_retention

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
