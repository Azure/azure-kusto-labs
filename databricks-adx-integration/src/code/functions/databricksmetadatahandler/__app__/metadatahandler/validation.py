"""
  [Microsoft Kusto Lab Project]

  Input validation helpers for the Databricks metadata handler.

  This function is triggered by a storage queue message whose payload selects the
  blob that is downloaded and, for checkpoint compact files, overwritten in place
  using the function app's configured storage credential. The original url's own
  account is discarded when the privileged client is built, so the container and
  blob taken from the message are validated here before they are used.
"""
import re
from typing import Optional, Set, Tuple
from urllib.parse import unquote, urlsplit

# Azure Storage naming limits. See
# https://learn.microsoft.com/rest/api/storageservices/naming-and-referencing-containers--blobs--and-metadata
MAX_URL_LENGTH = 2048

# The only endpoint suffix whose <account>.<service> shape this repository deploys
# against. A host outside it is trusted only as configured, never expanded.
AZURE_STORAGE_SUFFIX = 'core.windows.net'
MAX_BLOB_PATH_LENGTH = 1024

# Container names are 3-63 chars, lowercase letters/digits/single dashes, and must
# start and end with a letter or digit. This also rejects the reserved system
# containers ($root, $logs, $web).
_CONTAINER_NAME_REGEX = re.compile(r'^[a-z0-9](?:[a-z0-9]|-(?!-)){1,61}[a-z0-9]$')

# C0/C1 control characters and whitespace. These are the characters typically used
# to smuggle values past URL parsers, so they are rejected before parsing.
_FORBIDDEN_CHARS_REGEX = re.compile(r'[\x00-\x20\x7f-\x9f]')
# Control characters only. A blob name may legitimately contain a space, so the
# stricter url rule above is not applied to the name the sdk resolves.
_CONTROL_CHARS_REGEX = re.compile(r'[\x00-\x1f\x7f-\x9f]')

# Spark's structured streaming file sink names each checkpoint log entry after its
# batch number, and periodically rolls them up into "<batch>.compact".
_SPARK_METADATA_FILE_REGEX = re.compile(r'^\d{1,19}(\.compact)?$')

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

    Blob and queue urls routinely carry a SAS token in the query string, so
    recording one verbatim would copy a credential into the application logs.
    The path is retained because it is what makes the entry useful.

    A url is also passed here when it has just been rejected, so nothing has
    vouched for its shape yet: it can still carry credentials in its authority and
    control characters anywhere.

    :param url: the url about to be recorded, may be None
    :return: the url without credentials, with control characters escaped and any
        query string replaced by a marker
    """
    if not url or not isinstance(url, str):
        return url
    # Cut at whichever comes first. A fragment is not part of the request the sdk
    # issues, so it adds nothing to a log entry but can still carry a token.
    cut = len(url)
    for marker in ('?', '#'):
        index = url.find(marker)
        if 0 <= index < cut:
            cut = index
    base, trimmed = url[:cut], cut < len(url)

    prefix, delimiter, remainder = base.partition('://')
    if not delimiter:
        prefix, remainder = '', base
    # The authority follows any leading slashes, which are all a scheme relative
    # url has in front of it.
    slashes = remainder[:len(remainder) - len(remainder.lstrip('/'))]
    authority, slash, path = remainder[len(slashes):].partition('/')
    if '@' in authority:
        authority = authority.rsplit('@', 1)[1]
    base = prefix + delimiter + slashes + authority + slash + path

    # Escaped rather than removed, so the recorded value still shows what arrived
    # without letting a newline forge a second log record.
    base = _CONTROL_CHARS_REGEX.sub(
        lambda match: '\\x{:02x}'.format(ord(match.group(0))), base)
    return base + '?<redacted>' if trimmed else base


def storage_hosts_from_account_url(account_url: Optional[str]) -> Set[str]:
    """Derive the storage hostnames this function app is entitled to act on.

    Databricks emits ``dfs`` (ADLS Gen2) urls while the blob sdk uses ``blob``
    urls, and both address the same storage account, so both are accepted. The
    allow-list is derived from configuration the function already has, so no
    additional setting is required to bind the function to its own account.

    :param account_url: the configured blob service url for this function
    :return: set of allowed hostnames, empty when the url is unusable
    """
    host = (urlsplit(account_url or '').hostname or '').lower()
    if not host:
        return set()
    labels = host.split('.')
    if (len(labels) < 3 or labels[1] not in ('blob', 'dfs')
            or '.'.join(labels[2:]) != AZURE_STORAGE_SUFFIX):
        # Only a real Azure Storage endpoint has a service label to swap. A custom
        # domain that merely looks like one, such as "storage.blob.example.com",
        # says nothing about who owns "storage.dfs.example.com", so the configured
        # host is trusted on its own.
        return {host}
    account, suffix = labels[0], '.'.join(labels[2:])
    return {host} | {'{}.{}.{}'.format(account, service, suffix) for service in ('blob', 'dfs')}


def validate_blob_url_host(url: str, allowed_hosts: Set[str]) -> None:
    """Assert that a blob url points at a storage account this function may touch.

    Validation is deliberately performed on the raw url string, before it is
    handed to the storage sdk, so that the host authorised here is the host the
    sdk will subsequently parse.

    :param url: untrusted blob url taken from the queue message
    :param allowed_hosts: hostnames the function is entitled to act on
    :raises ValidationError: when the url is malformed or off-account
    """
    if not url or not isinstance(url, str):
        raise ValidationError('Blob url is missing or not a string.')
    if len(url) > MAX_URL_LENGTH:
        raise ValidationError('Blob url exceeds {} characters.'.format(MAX_URL_LENGTH))
    if _FORBIDDEN_CHARS_REGEX.search(url):
        raise ValidationError('Blob url contains control or whitespace characters.')
    if not allowed_hosts:
        # Fail closed: without a configured account there is nothing to authorise
        # against, and guessing would defeat the purpose of the check.
        raise ValidationError(
            'No allowed storage hosts are configured; refusing to act on a queue supplied url.')

    parts = urlsplit(url)
    if parts.scheme != 'https':
        raise ValidationError('Blob url scheme must be https, got {!r}.'.format(parts.scheme))
    if parts.username or parts.password:
        raise ValidationError('Blob url must not embed credentials.')
    if parts.fragment:
        # A blob request never carries a fragment, so one here is not addressing
        # part of the blob; it is carrying something else along for the ride.
        raise ValidationError('Blob url must not contain a fragment.')

    hostname = (parts.hostname or '').lower()
    # Exact match only. A suffix match would accept lookalikes such as
    # "myacct.blob.core.windows.net.attacker.example".
    if hostname not in allowed_hosts:
        raise ValidationError('Blob url host {!r} is not an allowed storage host.'.format(hostname))


def validate_container_name(container_name: str, allowed_containers: Set[str]) -> str:
    """Validate a container name and check it against the containers this app serves.

    :param container_name: container name resolved from the untrusted url
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


def _validate_path_syntax(blob_path: str, required_root: str) -> list:
    """Run the checks every blob path must pass, and return its segments.

    ``required_root`` is policy, not a convenience, so it has no default and a
    blank value is an error. If it were optional, a deployment that failed to
    supply it would silently widen this function to every blob in the container
    instead of failing.

    :param blob_path: blob name resolved by the storage sdk
    :param required_root: first path segment the blob must live under
    :return: the path segments
    :raises ValidationError: when policy is missing, or the path is malformed or
        outside the configured directory
    """
    if not required_root:
        raise ValidationError('METADATA_PATH_ROOT is not configured for this function app.')
    root_segments = required_root.strip('/').split('/')
    if any(segment in ('', '.', '..') for segment in root_segments):
        raise ValidationError(
            'METADATA_PATH_ROOT {!r} is not a valid directory.'.format(required_root))

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
    if segments[:len(root_segments)] != root_segments:
        raise ValidationError(
            'Blob path {!r} is outside the {!r} directory.'.format(blob_path, required_root))
    if len(segments) <= len(root_segments):
        raise ValidationError('Blob path {!r} does not name a file.'.format(blob_path))
    return segments


def validate_checkpoint_path(blob_path: str, required_root: str, required_parent: str) -> str:
    """Validate the path of a checkpoint log file this function reads or rewrites.

    :param blob_path: blob name resolved by the storage sdk
    :param required_root: first path segment the blob must live under
    :param required_parent: directory that must contain the file directly
    :return: the validated blob path
    :raises ValidationError: when policy is missing, or the path is not a
        checkpoint log file inside the configured directory
    """
    if not required_parent:
        raise ValidationError(
            'METADATA_REQUIRED_SEGMENT is not configured for this function app.')
    segments = _validate_path_syntax(blob_path, required_root)

    # The checkpoint log lives directly inside this directory. Accepting it
    # anywhere in the path would also accept an unrelated file that merely has
    # such a directory somewhere above it.
    if len(segments) < 2 or segments[-2] != required_parent:
        raise ValidationError(
            'Blob path {!r} is not directly inside a {!r} directory.'.format(
                blob_path, required_parent))
    if not _SPARK_METADATA_FILE_REGEX.match(segments[-1]):
        raise ValidationError(
            'Blob path {!r} is not a checkpoint log file name.'.format(blob_path))
    return blob_path


def validate_output_path(blob_path: str, required_root: str) -> str:
    """Validate the path of an output file referenced by checkpoint content.

    These are the data files the Databricks job produced, so they carry no
    checkpoint naming rules; only the directory boundary applies.

    :param blob_path: blob path taken from a checkpoint entry
    :param required_root: directory the blob must live under
    :return: the validated blob path
    :raises ValidationError: when policy is missing, or the path is malformed or
        outside the configured directory
    """
    _validate_path_syntax(blob_path, required_root)
    return blob_path

def split_blob_url(url: str) -> Tuple[str, str]:
    """Split a blob url into its container and blob path.

    Used for references derived from checkpoint file content, which name a blob
    but are never handed to the storage sdk here, so they have no client object to
    read the container and path from.

    :param url: an https blob url that has already passed host validation
    :return: (container, blob path); either may be empty when the url has no path
    """
    path = unquote(urlsplit(url or '').path).lstrip('/')
    container, _, blob_path = path.partition('/')
    return container, blob_path


def is_compact_checkpoint(blob_path: str) -> bool:
    """Report whether a validated path names a rolled up checkpoint file.

    The decision is taken from the path the storage sdk resolved rather than from
    the raw url, so a query string or fragment cannot change the answer.

    :param blob_path: blob path that has already passed validation
    :return: True when the file is a Spark ``.compact`` checkpoint log
    """
    return blob_path.rsplit('/', 1)[-1].endswith('.compact')
