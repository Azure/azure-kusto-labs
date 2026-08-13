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

# Control characters only. A blob name may legitimately contain a space, so the
# stricter URL rule above is not applied to the name the SDK resolves.
_CONTROL_CHARS_REGEX = re.compile(r'[\x00-\x1f\x7f-\x9f]')

# A retry generation is written by this function as a whole path segment, for
# example "databricks-out/.../retry1/part-0.c000.json".
_RETRY_SEGMENT_REGEX = re.compile(r'^retry(\d{1,3})$')


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


def validate_container_name(container_name: str, allowed_containers: Set[str]) -> str:
    """Validate a container name and check it against the containers this app serves.

    :param container_name: container name resolved from the untrusted URL
    :param allowed_containers: containers this function is permitted to touch
    :return: the validated container name
    :raises ValidationError: when the name is malformed, or is not one this app serves
    """
    if not allowed_containers:
        # Fail closed. An empty set means configuration is missing, and continuing
        # would let a queue message name any container in the account.
        raise ValidationError('No allowed containers are configured for this function app.')
    if not container_name or not isinstance(container_name, str):
        raise ValidationError('Container name is missing or not a string.')
    if not _CONTAINER_NAME_REGEX.match(container_name):
        raise ValidationError('Container name {!r} is not a valid Azure container name.'.format(container_name))
    if container_name not in allowed_containers:
        raise ValidationError('Container {!r} is not one this function app serves.'.format(container_name))
    return container_name


def validate_blob_path(blob_path: str, required_root: str, required_suffix: str) -> str:
    """Validate a blob path resolved from an untrusted URL.

    The path is validated *after* the storage SDK has resolved and percent-decoded
    it, so encoded traversal sequences such as ``%2e%2e%2f`` are caught here.

    ``required_root`` and ``required_suffix`` are policy, not conveniences, so they
    have no defaults and a blank value is an error. If they were optional, a
    deployment that failed to supply them would silently widen this function to
    every blob in the container instead of failing.

    :param blob_path: blob name resolved by the storage SDK
    :param required_root: first path segment the blob must live under
    :param required_suffix: file name suffix the blob must carry
    :return: the validated blob path
    :raises ValidationError: when policy is missing, or the path is malformed or
        outside the pipeline
    """
    if not required_root:
        raise ValidationError('SOURCE_PATH_ROOT is not configured for this function app.')
    if not required_suffix:
        raise ValidationError('SOURCE_FILE_SUFFIX is not configured for this function app.')
    if '/' in required_root:
        raise ValidationError('SOURCE_PATH_ROOT must be a single path segment.')

    if not blob_path or not isinstance(blob_path, str):
        raise ValidationError('Blob path is missing or not a string.')
    if len(blob_path) > MAX_BLOB_PATH_LENGTH:
        raise ValidationError('Blob path exceeds {} characters.'.format(MAX_BLOB_PATH_LENGTH))
    if _CONTROL_CHARS_REGEX.search(blob_path):
        raise ValidationError('Blob path contains control characters.')
    if '\\' in blob_path:
        raise ValidationError('Blob path must not contain backslashes.')
    if blob_path.startswith('/'):
        raise ValidationError('Blob path must be relative to the container.')

    segments = blob_path.split('/')
    if any(segment in ('', '.', '..') for segment in segments):
        raise ValidationError('Blob path {!r} contains empty or traversal segments.'.format(blob_path))

    # Compare whole segments. A prefix comparison would also accept a sibling
    # directory whose name merely starts with the expected one. The comparison is
    # exact because Azure blob names are case sensitive.
    if segments[0] != required_root:
        raise ValidationError(
            'Blob path {!r} is outside the {!r} directory.'.format(blob_path, required_root))
    if len(segments) < 2:
        raise ValidationError('Blob path {!r} does not name a file.'.format(blob_path))
    if not segments[-1].endswith(required_suffix):
        raise ValidationError(
            'Blob path {!r} is not a {} file.'.format(blob_path, required_suffix))
    return blob_path


def retry_generation(blob_path: str, max_retry_times: int) -> int:
    """Return the retry generation encoded in a blob path.

    The generation is written as its own path segment. Matching the segment rather
    than searching the whole string keeps an unrelated file name such as
    "notaretry999folder/part-0.c000.json" from being read as generation 999, which
    would send the blob straight to the final failure container and delete it.

    :param blob_path: validated blob path
    :param max_retry_times: highest generation this deployment allows
    :return: the generation, or 0 when the path carries none
    :raises ValidationError: when more than one generation is present, or the
        generation is outside the configured range
    """
    generations = [int(match.group(1))
                   for match in (_RETRY_SEGMENT_REGEX.match(segment)
                                 for segment in blob_path.split('/'))
                   if match]
    if not generations:
        return 0
    if len(generations) > 1:
        raise ValidationError(
            'Blob path {!r} carries more than one retry generation.'.format(blob_path))
    generation = generations[0]
    if generation < 1 or generation > max_retry_times:
        raise ValidationError(
            'Retry generation {} in {!r} is outside the configured range 1..{}.'.format(
                generation, blob_path, max_retry_times))
    return generation
