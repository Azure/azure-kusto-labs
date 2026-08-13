import json
import logging
import pytest

import azure.functions as func
import __app__.errorhandler as errorhandler


@pytest.fixture(autouse=True)
def configure_ingestion_storage():
    errorhandler.INGESTION_STORAGE_ACCOUNT_URL = (
        "https://test.blob.core.windows.net/")
    errorhandler.INGESTION_CONTAINER_NAME = "split"
    errorhandler.INGESTION_ROOT_PATH = "databricks-out"


class TestUtAdxIngestErrorHandler():
    def test_main(self, mocker):
        fake_container = 'split'
        fake_path = 'databricks-out/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        fake_new_path = 'databricks-out/2020/08/17/17/00/customerId=cId/pname=sao/retry1/part-uuid.c000.json'
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
        mock_get_config_values = mocker.patch('__app__.errorhandler.get_config_values')
        errorhandler.get_config_values = mock_get_config_values
        mock_azure_telemetry_client = mocker.patch('applicationinsights.TelemetryClient')
        errorhandler.TelemetryClient = mock_azure_telemetry_client
        
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
        fake_url = 'https://test.blob.core.windows.net/split/databricks-out/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'
        expected_container = 'split'
        expected_blob_path = 'databricks-out/2020/08/17/17/00/customerId=cId/pname=sao/part-uuid.c000.json'

        actual_cotainer, actual_blob_path = errorhandler.get_blob_info_from_url(fake_url)
        assert actual_cotainer == expected_container
        assert actual_blob_path == expected_blob_path

        retry_named_folder_url = (
            "https://test.blob.core.windows.net/split/databricks-out/"
            "retryqueue/company/type/part-uuid.c000.json")
        assert errorhandler.get_blob_info_from_url(retry_named_folder_url) == (
            "split", "databricks-out/retryqueue/company/type/part-uuid.c000.json")

    @pytest.mark.parametrize("fake_url", [
        (
            "https://attacker.blob.core.windows.net/split/databricks-out/2020/08/17/"
            "part-uuid.c000.json"
        ),
        (
            "https://test.blob.core.windows.net/other/databricks-out/2020/08/17/"
            "part-uuid.c000.json"
        ),
        (
            "https://test.blob.core.windows.net/split/databricks-out/2020/08/17/"
            "part-uuid.c000.json?sig=secret"
        ),
        (
            "https://test.blob.core.windows.net/split/databricks-out/2020/08/17/"
            "part-uuid.json"
        ),
        (
            "https://test.blob.core.windows.net/split/databricks-out/2020/../08/17/"
            "part-uuid.c000.json"
        ),
        (
            "https://test.blob.core.windows.net/split/databricks-out/2020%2F08/17/"
            "part-uuid.c000.json"
        ),
        (
            "https://test.blob.core.windows.net/split/databricks-out/2020/retry0/"
            "part-uuid.c000.json"
        ),
        (
            "https://test.blob.core.windows.net/split/databricks-out/retry1/2020/"
            "part-uuid.c000.json"
        ),
        (
            "https://test.blob.core.windows.net/split/other/2020/08/17/"
            "part-uuid.c000.json"
        ),
    ])
    def test_get_blob_info_from_url_rejects_untrusted_paths(self, fake_url):
        with pytest.raises((PermissionError, ValueError)):
            errorhandler.get_blob_info_from_url(fake_url)

    def test_retry_blob_ingest_to_adx(self, mocker):
        spy_move_blob_file = mocker.spy(errorhandler, 'move_blob_file')
        errorhandler.BLOB_MAX_RETRY_DELAY_SEC = 1  # Shorten the delay time
        with pytest.raises(Exception):
            errorhandler.retry_blob_ingest_to_adx('fake_container', 'fake_path', 'fake_container', 'fake_new_path')
        assert spy_move_blob_file.call_count == errorhandler.BLOB_REQ_MAX_ATTEMPT

    def test_move_blob_file_revalidates_retry_destination(self):
        source_path = "databricks-out/queue0/part-uuid.c000.json"

        with pytest.raises(PermissionError):
            errorhandler.move_blob_file(
                "fake_connection",
                "split",
                "split",
                source_path,
                "databricks-out/queue0/arbitrary/part-uuid.c000.json")

    def test_move_blob_file_deletes_source_only_after_copy_success(self, mocker):
        source_path = "databricks-out/queue0/part-uuid.c000.json"
        target_path = "databricks-out/queue0/retry1/part-uuid.c000.json"
        blob_service_client = mocker.Mock()
        source_client = mocker.Mock(url="https://test/source")
        target_client = mocker.Mock()
        target_client.start_copy_from_url.return_value = {
            "copy_status": "success",
        }
        blob_service_client.get_blob_client.side_effect = [
            source_client,
            target_client,
        ]
        mocker.patch(
            "__app__.errorhandler.BlobServiceClient.from_connection_string",
            return_value=blob_service_client)

        errorhandler.move_blob_file(
            "fake_connection", "split", "split", source_path, target_path)

        target_client.start_copy_from_url.assert_called_once_with(
            source_client.url, requires_sync=True)
        source_client.delete_blob.assert_called_once_with()

    def test_move_blob_file_preserves_source_when_copy_is_not_complete(self, mocker):
        source_path = "databricks-out/queue0/part-uuid.c000.json"
        target_path = "databricks-out/queue0/retry1/part-uuid.c000.json"
        blob_service_client = mocker.Mock()
        source_client = mocker.Mock(url="https://test/source")
        target_client = mocker.Mock()
        target_client.start_copy_from_url.return_value = {
            "copy_status": "pending",
        }
        blob_service_client.get_blob_client.side_effect = [
            source_client,
            target_client,
        ]
        mocker.patch(
            "__app__.errorhandler.BlobServiceClient.from_connection_string",
            return_value=blob_service_client)

        with pytest.raises(RuntimeError):
            errorhandler.move_blob_file(
                "fake_connection", "split", "split", source_path, target_path)

        source_client.delete_blob.assert_not_called()