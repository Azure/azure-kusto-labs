"""
  [Microsoft Kusto Lab Project]

  Input validation helpers for the ADX ingestion error handler.

  This function is triggered by a storage queue message whose payload selects the
  blob that is copied and then DELETED using the function app's account-wide
  connection string. The queue payload is untrusted input reaching a privileged,
  destructive sink, so every value taken from it is validated here before use.
"""
import re
from typing import Optional, Set
from urllib.parse import urlsplit

# Azure Storage naming limits. See
# https://learn.microsoft.com/rest/api/storageservices/naming-and-referencing-containers--blobs--and-metadata
MAX_URL_LENGTH = 2048
MAX_BLOB_PATH_LENGTH = 1024

DEFAULT_ENDPOINT_SUFFIX = 'core.windows.net'

# Container names are 3-63 chars, lowercase letters/digits/single dashes, and must
# start and end with a letter or digit. This also rejects the reserved system
# containers ($root, $logs, $web).
_CONTAINER_NAME_REGEX = re.compile(r'^[a-z0-9](?:[a-z0-9]|-(?!-)){1,61}[a-z0-9]$')

# C0/C1 control characters and whitespace. These are the characters typically used
# to smuggle values past URL parsers, so they are rejected before parsing.
_FORBIDDEN_CHARS_REGEX = re.compile(r'[\x00-\x20\x7f-\x9f]')


class ValidationError(ValueError):
    """Raised when untrusted input fails validation."""


def parse_allow_list(raw: Optional[str]) -> Set[str]:
    """Parse a comma separated allow-list setting into a set of entries.

    :param raw: comma separated string, may be None or empty
    :return: set of non-empty, stripped entries
    """
    if not raw:
        return set()
    return {entry.strip() for entry in raw.split(',') if entry.strip()}


def redact_url(url: Optional[str]) -> Optional[str]:
    """Return a url safe to write to logs or telemetry.

    Blob urls routinely carry a SAS token in the query string, so recording one
    verbatim would copy a credential into the application logs. The path is
    retained because it is what makes the entry useful.

    :param url: the url about to be recorded, may be None
    :return: the url with any query string replaced by a marker
    """
    if not url or not isinstance(url, str):
        return url
    base, separator, _ = url.partition('?')
    return base + '?<redacted>' if separator else base


def _sibling_service_hosts(host: str) -> Set[str]:
    """Expand a storage host into the blob and dfs endpoints of the same account.

    Databricks emits ``dfs`` (ADLS Gen2) URLs while the blob SDK uses ``blob``
    URLs, and both address the same account, so both are treated as equivalent.

    :param host: a storage hostname, e.g. ``myacct.blob.core.windows.net``
    :return: set of equivalent hostnames for the same storage account
    """
    host = (host or '').lower()
    if not host:
        return set()
    labels = host.split('.')
    if len(labels) < 3:
        # Not a standard <account>.<service>.<suffix> host (for example the local
        # storage emulator). Trust it verbatim rather than deriving nonsense.
        return {host}
    account, suffix = labels[0], '.'.join(labels[2:])
    return {host} | {'{}.{}.{}'.format(account, service, suffix) for service in ('blob', 'dfs')}


def storage_hosts_from_connection_string(connection_string: Optional[str]) -> Set[str]:
    """Derive the storage hostnames this function app is entitled to act on.

    The allow-list is derived from the credential the function already holds, so
    no additional configuration is required to bind the function to its own
    storage account.

    :param connection_string: an Azure Storage connection string
    :return: set of allowed hostnames, empty when the connection string is unusable
    """
    settings = {}
    for segment in (connection_string or '').split(';'):
        key, separator, value = segment.partition('=')
        if separator:
            # partition() splits on the first '=' only, so base64 padding inside
            # AccountKey is preserved rather than truncated.
            settings[key.strip().lower()] = value.strip()

    blob_endpoint = settings.get('blobendpoint')
    if blob_endpoint:
        return _sibling_service_hosts(urlsplit(blob_endpoint).hostname or '')

    account = settings.get('accountname', '').lower()
    if not account:
        return set()
    suffix = settings.get('endpointsuffix', DEFAULT_ENDPOINT_SUFFIX).strip('.').lower()
    return {'{}.{}.{}'.format(account, service, suffix) for service in ('blob', 'dfs')}


def validate_blob_url_host(url: str, allowed_hosts: Set[str]) -> None:
    """Assert that a blob URL points at a storage account this function may touch.

    Validation is deliberately performed on the raw URL string, before it is
    handed to the storage SDK, so that the host authorised here is the host the
    SDK will subsequently parse.

    :param url: untrusted blob URL taken from the queue message
    :param allowed_hosts: hostnames the function is entitled to act on
    :raises ValidationError: when the URL is malformed or off-account
    """
    if not url or not isinstance(url, str):
        raise ValidationError('Blob URL is missing or not a string.')
    if len(url) > MAX_URL_LENGTH:
        raise ValidationError('Blob URL exceeds {} characters.'.format(MAX_URL_LENGTH))
    if _FORBIDDEN_CHARS_REGEX.search(url):
        raise ValidationError('Blob URL contains control or whitespace characters.')
    if not allowed_hosts:
        # Fail closed: without a configured account there is nothing to authorise
        # against, and guessing would defeat the purpose of the check.
        raise ValidationError(
            'No allowed storage hosts are configured; refusing to act on a queue supplied URL.')

    parts = urlsplit(url)
    if parts.scheme != 'https':
        raise ValidationError('Blob URL scheme must be https, got {!r}.'.format(parts.scheme))
    if parts.username or parts.password:
        raise ValidationError('Blob URL must not embed credentials.')

    hostname = (parts.hostname or '').lower()
    # Exact match only. A suffix match would accept lookalikes such as
    # "myacct.blob.core.windows.net.attacker.example".
    if hostname not in allowed_hosts:
        raise ValidationError('Blob URL host {!r} is not an allowed storage host.'.format(hostname))


def validate_container_name(container_name: str, allowed_containers: Optional[Set[str]] = None) -> str:
    """Validate a container name and optionally check it against an allow-list.

    :param container_name: container name resolved from the untrusted URL
    :param allowed_containers: optional explicit allow-list; no check when empty
    :return: the validated container name
    :raises ValidationError: when the name is malformed or not allowed
    """
    if not container_name or not isinstance(container_name, str):
        raise ValidationError('Container name is missing or not a string.')
    if not _CONTAINER_NAME_REGEX.match(container_name):
        raise ValidationError('Container name {!r} is not a valid Azure container name.'.format(container_name))
    if allowed_containers and container_name not in allowed_containers:
        raise ValidationError('Container {!r} is not in the configured allow-list.'.format(container_name))
    return container_name


def validate_blob_path(blob_path: str, required_prefix: Optional[str] = None) -> str:
    """Validate a blob path resolved from an untrusted URL.

    The path is validated *after* the storage SDK has resolved and percent-decoded
    it, so encoded traversal sequences such as ``%2e%2e%2f`` are caught here.

    :param blob_path: blob name resolved by the storage SDK
    :param required_prefix: optional prefix the blob must live under
    :return: the validated blob path
    :raises ValidationError: when the path is malformed or outside the prefix
    """
    if not blob_path or not isinstance(blob_path, str):
        raise ValidationError('Blob path is missing or not a string.')
    if len(blob_path) > MAX_BLOB_PATH_LENGTH:
        raise ValidationError('Blob path exceeds {} characters.'.format(MAX_BLOB_PATH_LENGTH))
    if _FORBIDDEN_CHARS_REGEX.search(blob_path):
        raise ValidationError('Blob path contains control or whitespace characters.')
    if '\\' in blob_path:
        raise ValidationError('Blob path must not contain backslashes.')
    if blob_path.startswith('/'):
        raise ValidationError('Blob path must be relative to the container.')

    segments = blob_path.split('/')
    if any(segment in ('', '.', '..') for segment in segments):
        raise ValidationError('Blob path {!r} contains empty or traversal segments.'.format(blob_path))

    if required_prefix and not blob_path.startswith(required_prefix):
        raise ValidationError('Blob path {!r} is outside the required prefix {!r}.'.format(blob_path, required_prefix))
    return blob_path
