import json
import logging
import os

import azure.functions as func
import pytest

import __app__.dataingest as dataingest
import __app__.dataingest.validation as validation

# The destinations the ADX provisioning tool creates from provision-config.json.
DATABASE_FORMAT = 'company-id-{INDEX}'
DATABASE_COUNT = '3'
TABLES = 'CO2,TEMP'

# The storage the Databricks job writes telemetry to.
ACCOUNT_URL = 'https://account.blob.core.windows.net'
SOURCE_CONTAINER = 'data'
PATH_ROOT = 'databricks-out'
BLOB_PATH = (PATH_ROOT + '/landingeventqueue0/companyIdkey=company-id-1/typekey=TEMP/'
             'part-00001-uuid.c000.json')
BLOB_URL = 'https://account.blob.core.windows.net/{}/{}'.format(SOURCE_CONTAINER, BLOB_PATH)


class TestUtAdxIngest():
    @pytest.fixture(autouse=True)
    def configure_function(self, monkeypatch):
        """ Apply the function app configuration the deployment provides. """
        # get_config_values() reads each setting as os.getenv(NAME, <current global>),
        # so a value set by a previous test survives monkeypatch's env cleanup and
        # would leak into the next one. Reset the globals this suite varies.
        dataingest.ALLOWED_DATABASE_NAME_FORMAT = DATABASE_FORMAT
        dataingest.ALLOWED_DATABASE_COUNT = 0
        dataingest.ALLOWED_TABLES = ''
        dataingest.SOURCE_STORAGE_ACCOUNT_URL = ''
        dataingest.ALLOWED_SOURCE_CONTAINERS = set()
        dataingest.SOURCE_PATH_ROOT = ''

        for name, value in (
                ('APP_AAD_TENANT_ID', 'tenant'),
                ('APP_CLIENT_ID', 'client'),
                ('APP_CLIENT_SECRETS', 'PLACEHOLDER-NOT-A-REAL-SECRET'),
                ('INGESTION_SERVER_URI', 'https://ingest-adx.eastus2.kusto.windows.net'),
                ('INGESTION_MAPPING', 'json_mapping_01'),
                ('ALLOWED_DATABASE_NAME_FORMAT', DATABASE_FORMAT),
                ('ALLOWED_DATABASE_COUNT', DATABASE_COUNT),
                ('ALLOWED_TABLES', TABLES),
                ('SOURCE_STORAGE_ACCOUNT_URL', ACCOUNT_URL),
                ('ALLOWED_SOURCE_CONTAINERS', SOURCE_CONTAINER),
                ('SOURCE_PATH_ROOT', PATH_ROOT)):
            monkeypatch.setenv(name, value)
        dataingest.get_config_values()

    def _message(self, url=BLOB_URL, size=1024):
        body = {
            'data': {'api': 'PutBlockList', 'contentLength': size, 'url': url},
            'eventTime': '2020-09-07T06:43:03.2126947Z',
            'modificationTime': '2020-09-07T06:40:00.0000000Z',
        }
        return func.QueueMessage(body=json.dumps(body).encode('utf-8'))

    def test_the_allow_list_matches_what_provisioning_created(self):
        # The provisioning tool writes company-id-0 .. company-id-(N-1). Rebuilding
        # from the same format and count is what keeps the two in step.
        assert dataingest.ALLOWED_DATABASES == {
            'company-id-0', 'company-id-1', 'company-id-2'}
        assert dataingest.ALLOWED_TABLE_NAMES == {'CO2', 'TEMP'}

    def test_a_provisioned_destination_is_accepted(self):
        assert dataingest.get_target_info(BLOB_PATH) == ('company-id-1', 'TEMP')

    @pytest.mark.parametrize('path', [
        # A company the deployment never created.
        PATH_ROOT + '/q/companyIdkey=company-id-99/typekey=TEMP/part-0.c000.json',
        # A database name that is not of the provisioned shape at all.
        PATH_ROOT + '/q/companyIdkey=master/typekey=TEMP/part-0.c000.json',
        # A lookalike that merely starts with a provisioned name.
        PATH_ROOT + '/q/companyIdkey=company-id-1x/typekey=TEMP/part-0.c000.json',
        # A table the deployment never created.
        PATH_ROOT + '/q/companyIdkey=company-id-1/typekey=SECRETS/part-0.c000.json',
        # Neither marker present at all.
        PATH_ROOT + '/q/part-0.c000.json',
        # Only one of the two markers.
        PATH_ROOT + '/q/companyIdkey=company-id-1/part-0.c000.json',
    ])
    def test_a_destination_this_deployment_never_created_is_refused(self, path):
        with pytest.raises(validation.ValidationError):
            dataingest.get_target_info(path)

    @pytest.mark.parametrize('encoded', [
        # The sdk percent decodes the path, so checking the encoded form would
        # accept these as ordinary segments while the request addressed "..".
        'databricks-out/%2e%2e/private/companyIdkey=company-id-1/typekey=TEMP/p.c000.json',
        'databricks-out/%2E%2E/private/companyIdkey=company-id-1/typekey=TEMP/p.c000.json',
        'databricks-out/..%2fprivate/companyIdkey=company-id-1/typekey=TEMP/p.c000.json',
    ])
    def test_encoded_traversal_is_rejected_after_decoding(self, encoded, mocker):
        ingest = mocker.patch.object(dataingest, 'ingest_to_adx')
        url = 'https://account.blob.core.windows.net/{}/{}'.format(SOURCE_CONTAINER, encoded)
        with pytest.raises(validation.ValidationError):
            dataingest.main(self._message(url=url))
        ingest.assert_not_called()

    def test_a_mixed_case_configured_table_is_usable(self, monkeypatch):
        # Kusto identifiers are case sensitive, so the name that reaches the
        # ingestion properties has to be the provisioned spelling, not the casing
        # the telemetry field happened to use.
        monkeypatch.setenv('ALLOWED_TABLES', 'Temp, CO2')
        dataingest.get_config_values()
        assert dataingest.ALLOWED_TABLE_NAMES == {'Temp', 'CO2'}

        for requested in ('Temp', 'temp', 'TEMP'):
            path = PATH_ROOT + '/q/companyIdkey=company-id-1/typekey={}/p.c000.json'.format(requested)
            assert dataingest.get_target_info(path) == ('company-id-1', 'Temp')

    def test_tables_that_differ_only_by_case_are_refused(self, monkeypatch):
        # Two provisioned names that fold together cannot be told apart from a
        # path, so there is no safe answer to give.
        monkeypatch.setenv('ALLOWED_TABLES', 'Temp,TEMP')
        dataingest.get_config_values()
        with pytest.raises(validation.ValidationError):
            dataingest.get_target_info(
                PATH_ROOT + '/q/companyIdkey=company-id-1/typekey=Temp/p.c000.json')

    @pytest.mark.parametrize('size', [-1, 10 ** 30, True, 1.5, '1024', None])
    def test_an_invalid_content_length_never_reaches_ingestion(self, size, mocker):
        ingest = mocker.patch.object(dataingest, 'ingest_to_adx')
        mocker.patch.object(dataingest, 'initialize_kusto_client')
        with pytest.raises((validation.ValidationError, KeyError, TypeError)):
            dataingest.main(self._message(size=size))
        ingest.assert_not_called()

    def test_the_largest_real_file_length_is_accepted(self):
        assert validation.validate_content_length(validation.MAX_BLOB_SIZE_BYTES) == \
            validation.MAX_BLOB_SIZE_BYTES
        assert validation.validate_content_length(0) == 0

    def test_policy_allows_any_provisioned_database_without_producer_binding(self):
        # Recorded deliberately: every company's telemetry arrives through one
        # container and one credential, and companyId is a field inside each
        # record, so this function has no producer identity to bind a database to.
        # The allow-list confines the choice to provisioned databases; it cannot
        # decide which of them the data belongs to. This is a residual limitation,
        # not closure, and it needs the ingress to carry a trusted tenant identity.
        for company in ('company-id-0', 'company-id-2'):
            path = PATH_ROOT + '/q/companyIdkey={}/typekey=TEMP/p.c000.json'.format(company)
            assert dataingest.get_target_info(path) == (company, 'TEMP')

    @pytest.mark.parametrize('name_format', [
        # Escapes the marker, so every index yields the same name. Provisioning
        # would create one database while reporting many.
        '{{INDEX}}',
        'company-id-{{INDEX}}',
        # Contains the marker but leaves another brace unresolved.
        'company-{INDEX}-{OTHER',
    ])
    def test_a_name_format_that_does_not_vary_per_database_is_refused(self, name_format):
        with pytest.raises(validation.ValidationError):
            validation.build_database_allow_list(name_format, 3)

    def test_a_usable_name_format_produces_one_name_per_database(self):
        assert validation.build_database_allow_list('company-id-{INDEX}', 3) == {
            'company-id-0', 'company-id-1', 'company-id-2'}

    @pytest.mark.parametrize('database_key,table_key', [
        # One directory would answer both questions.
        ('key=', 'key='),
        # One marker is a prefix of the other, so a segment matching the longer
        # one also matches the shorter.
        ('key=', 'key=type='),
        ('companyIdkey=', 'companyIdkey'),
        # Absent, or spanning more than one segment.
        ('', 'typekey='),
        ('companyIdkey=', ''),
        ('companyIdkey=/x', 'typekey='),
    ])
    def test_markers_that_cannot_select_two_directories_are_refused(self, database_key, table_key):
        with pytest.raises(validation.ValidationError):
            validation.validate_selector_keys(database_key, table_key)

    def test_the_configured_markers_are_usable(self):
        assert validation.validate_selector_keys('companyIdkey=', 'typekey=') is None

    def test_the_marker_must_start_a_whole_segment(self):
        # A directory that merely contains the marker is not a destination
        # selector, and must not be read as one.
        with pytest.raises(validation.ValidationError):
            dataingest.get_target_info(
                PATH_ROOT + '/q/notcompanyIdkey=company-id-1/typekey=TEMP/part-0.c000.json')

    @pytest.mark.parametrize('path', [
        # Two database selectors: whichever this function reads, the other one is
        # the one an operator would see when looking at the path.
        PATH_ROOT + '/companyIdkey=company-id-0/companyIdkey=company-id-1/'
        'typekey=TEMP/part-0.c000.json',
        # Two table selectors.
        PATH_ROOT + '/companyIdkey=company-id-1/typekey=CO2/typekey=TEMP/part-0.c000.json',
    ])
    def test_an_ambiguous_destination_is_refused(self, path):
        # Both selectors name provisioned destinations, so the allow-list alone
        # cannot settle this; the path itself has to be unambiguous.
        with pytest.raises(validation.ValidationError):
            dataingest.get_target_info(path)

    def test_a_malformed_message_is_refused_without_crashing(self, mocker):
        ingest = mocker.patch.object(dataingest, 'ingest_to_adx')
        for body in ({'data': {}, 'eventTime': '2020-09-07T06:43:03Z'},
                     {'eventTime': '2020-09-07T06:43:03Z'},
                     {'data': {'url': 12345}, 'eventTime': '2020-09-07T06:43:03Z'}):
            message = func.QueueMessage(body=json.dumps(body).encode('utf-8'))
            with pytest.raises((validation.ValidationError, KeyError, TypeError)):
                dataingest.main(message)
        ingest.assert_not_called()

    def test_the_queue_body_is_not_echoed_into_the_logs(self, caplog, mocker):
        # The body carries the blob url, which can include a sas token.
        mocker.patch.object(dataingest, 'ingest_to_adx')
        mocker.patch.object(dataingest, 'initialize_kusto_client')
        url = BLOB_URL
        with caplog.at_level(logging.INFO):
            dataingest.main(self._message(url=url))
        for record in caplog.records:
            assert '"contentLength"' not in record.getMessage(), \
                'the raw queue body must not be logged'

    def test_destination_policy_is_mandatory(self, monkeypatch):
        # Absent configuration must deny, not widen the function to the cluster.
        with pytest.raises(validation.ValidationError):
            validation.validate_target('company-id-1', 'database', set())
        for value in ('', 'company-id', 'no-index-here'):
            with pytest.raises(validation.ValidationError):
                validation.build_database_allow_list(value, 3)
        for count in (0, -1, None, True, validation.MAX_DATABASE_COUNT + 1):
            with pytest.raises(validation.ValidationError):
                validation.build_database_allow_list(DATABASE_FORMAT, count)

    @pytest.mark.parametrize('url', [
        # A host this deployment does not ingest from would receive the storage
        # sas token this function attaches to the url.
        'https://attacker.example/{}/{}'.format(SOURCE_CONTAINER, BLOB_PATH),
        'https://account.blob.core.windows.net.attacker.example/{}/{}'.format(
            SOURCE_CONTAINER, BLOB_PATH),
        # Right account, container this app does not serve.
        'https://account.blob.core.windows.net/private/{}'.format(BLOB_PATH),
        # Right container, outside the directory the pipeline writes to.
        'https://account.blob.core.windows.net/{}/unrelated/companyIdkey=company-id-1/'
        'typekey=TEMP/part-0.c000.json'.format(SOURCE_CONTAINER),
        # A sibling directory whose name merely starts with the expected one.
        'https://account.blob.core.windows.net/{}/{}X/companyIdkey=company-id-1/'
        'typekey=TEMP/part-0.c000.json'.format(SOURCE_CONTAINER, PATH_ROOT),
        # Traversal, and a scheme that is not https.
        'https://account.blob.core.windows.net/{}/{}/../../etc/part-0.c000.json'.format(
            SOURCE_CONTAINER, PATH_ROOT),
        'http://account.blob.core.windows.net/{}/{}'.format(SOURCE_CONTAINER, BLOB_PATH),
        # A url carrying its own token, which would compete with the configured one.
        BLOB_URL + '?sig=someone-elses-token',
    ])
    def test_a_blob_outside_this_pipeline_is_refused(self, url, mocker):
        ingest = mocker.patch.object(dataingest, 'ingest_to_adx')
        with pytest.raises(validation.ValidationError):
            dataingest.main(self._message(url=url))
        ingest.assert_not_called()

    def test_a_rejected_message_does_not_echo_its_url(self, caplog, mocker):
        mocker.patch.object(dataingest, 'ingest_to_adx')
        url = 'https://attacker.example/data/p\nWARNING:root:forged?sig=secret'
        with pytest.raises(validation.ValidationError):
            dataingest.main(self._message(url=url))
        assert caplog.records
        for record in caplog.records:
            assert 'secret' not in record.getMessage()
            assert '\n' not in record.getMessage()

    def test_a_valid_message_reaches_the_provisioned_destination(self, mocker):
        ingest = mocker.patch.object(dataingest, 'ingest_to_adx', return_value='source-id')
        mocker.patch.object(dataingest, 'initialize_kusto_client')

        dataingest.main(self._message())

        assert ingest.call_count == 1
        args = ingest.call_args[0]
        assert args[0] == BLOB_URL
        assert args[2] == 'company-id-1'
        assert args[3] == 'TEMP'

    def test_only_real_azure_storage_hosts_gain_a_sibling(self):
        assert validation.storage_hosts_from_account_url(
            'https://account.blob.core.windows.net') == {
                'account.blob.core.windows.net', 'account.dfs.core.windows.net'}
        assert validation.storage_hosts_from_account_url(
            'https://storage.blob.example.com') == {'storage.blob.example.com'}
        assert validation.storage_hosts_from_account_url(
            'https://storage.example.com') == {'storage.example.com'}
