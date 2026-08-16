import json
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

    def test_the_marker_must_start_a_whole_segment(self):
        # A directory that merely contains the marker is not a destination
        # selector, and must not be read as one.
        with pytest.raises(validation.ValidationError):
            dataingest.get_target_info(
                PATH_ROOT + '/q/notcompanyIdkey=company-id-1/typekey=TEMP/part-0.c000.json')

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
