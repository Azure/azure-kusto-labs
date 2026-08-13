import pytest

import __app__.dataingest as dataingest


@pytest.fixture(autouse=True)
def configure_authorized_destinations():
    dataingest.INGESTION_STORAGE_ACCOUNT_URL = (
        "https://account.blob.core.windows.net/")
    dataingest.INGESTION_CONTAINER_NAME = "data"
    dataingest.INGESTION_ROOT_PATH = "databricks-out"
    dataingest.DATABASEID_KEY = "companyIdkey="
    dataingest.TABLEID_KEY = "typekey="
    (
        dataingest.AUTHORIZED_DATABASES,
        dataingest.AUTHORIZED_TABLES,
    ) = dataingest.build_authorized_destinations(
        "company-id-{INDEX}", 100, "CO2,TEMP")


def test_get_target_info_accepts_documented_blob_and_dfs_urls():
    blob_path = (
        "data/databricks-out/queue0/companyIdkey=company-id-42/"
        "typekey=temp/part-00001.c000.json")

    assert dataingest.get_target_info(
        f"https://account.blob.core.windows.net/{blob_path}") == (
            "company-id-42", "TEMP")
    assert dataingest.get_target_info(
        f"https://account.dfs.core.windows.net/{blob_path}") == (
            "company-id-42", "TEMP")

    retry_blob_path = blob_path.replace(
        "/part-00001.c000.json", "/retry2/part-00001.c000.json")
    assert dataingest.get_target_info(
        f"https://account.blob.core.windows.net/{retry_blob_path}") == (
            "company-id-42", "TEMP")


@pytest.mark.parametrize("file_url", [
    (
        "https://attacker.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1/typekey=TEMP/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/other/databricks-out/"
        "companyIdkey=company-id-1/typekey=TEMP/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1/typekey=TEMP/part-00001.c000.json?sig=secret"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1/typekey=TEMP/"
        "companyIdkey=company-id-2/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "typekey=TEMP/companyIdkey=company-id-1/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-100/typekey=TEMP/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1/typekey=HUMIDITY/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1%2Ftypekey=TEMP/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1/typekey=TEMP/nested/part-00001.c000.json"
    ),
    (
        "https://account.blob.core.windows.net/data/databricks-out/"
        "companyIdkey=company-id-1/typekey=TEMP/part-00001.json"
    ),
])
def test_get_target_info_rejects_untrusted_routes(file_url):
    with pytest.raises((PermissionError, ValueError)):
        dataingest.get_target_info(file_url)


def test_build_authorized_destinations_rejects_ambiguous_configuration():
    with pytest.raises(EnvironmentError):
        dataingest.build_authorized_destinations("company-id", 100, "CO2,TEMP")
    with pytest.raises(EnvironmentError):
        dataingest.build_authorized_destinations(
            "company-{INDEX}-{INDEX}", 100, "CO2,TEMP")
    with pytest.raises(EnvironmentError):
        dataingest.build_authorized_destinations(
            "company-id-{INDEX}", 0, "CO2,TEMP")
    with pytest.raises(EnvironmentError):
        dataingest.build_authorized_destinations(
            "company-id-{INDEX}", 100, "")
    with pytest.raises(EnvironmentError):
        dataingest.build_authorized_destinations(
            "company-id-{INDEX}", 100, "TEMP,temp")


def test_ingest_to_adx_revalidates_the_authorized_destination():
    file_url = (
        "https://account.blob.core.windows.net/data/databricks-out/queue0/"
        "companyIdkey=company-id-1/typekey=TEMP/part-00001.c000.json")

    with pytest.raises(PermissionError):
        dataingest.ingest_to_adx(
            file_url, 1, "company-id-2", "TEMP", None, None)
