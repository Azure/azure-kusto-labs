"""
  [Microsoft Kusto Lab Project]

  Input validation for the ADX ingestion function.

  The queue message names a blob, and the directories in that blob path also
  choose the ADX database and table the data is written to. Both the blob and the
  destination are therefore attacker reachable, so this module confines each of
  them to what the deployment actually provisioned.
"""
import re
from typing import Optional, Set
from urllib.parse import unquote, urlsplit

from .destination_policy import (
    MAX_DATABASE_COUNT,
    PolicyError,
    build_database_names,
    normalise_table_list,
    validate_table_list,
)

# A blob url and an identifier are both bounded in practice. Rejecting anything
# longer keeps a crafted value from reaching the sdk or the ingestion properties.
MAX_URL_LENGTH = 2048
MAX_IDENTIFIER_LENGTH = 1024

# The only endpoint suffix whose <account>.<service> shape this repository deploys
# against. A host outside it is trusted only as configured, never expanded.
AZURE_STORAGE_SUFFIX = 'core.windows.net'

# Databases are generated as company-id-0 .. company-id-(N-1) by the provisioning
# tool. The bound on that count is part of the shared destination policy.

# Azure container naming rules, applied to the container resolved from the url.
_CONTAINER_NAME_REGEX = re.compile(r'^[a-z0-9](?:[a-z0-9]|-(?!-)){1,61}[a-z0-9]$')

# Control and whitespace characters have no place in a url this function received.
_FORBIDDEN_CHARS_REGEX = re.compile(r'[\x00-\x20\x7f-\x9f]')

# Control characters in a blob path, which may legitimately contain spaces.
_CONTROL_CHARS_REGEX = re.compile(r'[\x00-\x1f\x7f-\x9f]')


# The largest value a file length can take, matching the signed 64 bit length
# the storage service reports.
MAX_BLOB_SIZE_BYTES = 2 ** 63 - 1


class ValidationError(Exception):
    """Raised when untrusted input is refused."""


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

    The blob url this function handles is given a storage sas token before it is
    handed to ADX, so recording one verbatim would copy a credential into the
    application logs. A url is also passed here when it has just been rejected,
    so nothing has vouched for its shape yet.

    :param url: the url about to be recorded, may be None
    :return: the url without credentials, with control characters escaped and any
        query string replaced by a marker
    """
    if not url:
        return url
    if not isinstance(url, str):
        # A queue message can carry any json value here, and it reaches the log
        # before anything has checked it. Describe it rather than print it.
        return '<non-string URL>'
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


def _sibling_service_hosts(host: str) -> Set[str]:
    """Expand a storage host into the blob and dfs endpoints of the same account.

    Databricks emits ``dfs`` (ADLS Gen2) urls while the queue message may carry a
    ``blob`` url, and both address the same account, so both are treated as
    equivalent.

    :param host: a storage hostname, e.g. ``myacct.blob.core.windows.net``
    :return: set of equivalent hostnames for the same storage account
    """
    host = (host or '').lower()
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


def storage_hosts_from_account_url(account_url: Optional[str]) -> Set[str]:
    """Derive the storage hostnames this function app is entitled to ingest from.

    The allow-list is derived from configuration the function already has, so no
    additional setting is required to bind the function to its own account.

    :param account_url: the configured storage url for the telemetry account
    :return: set of allowed hostnames, empty when the url is unusable
    """
    host = (urlsplit(account_url or '').hostname or '').lower()
    return _sibling_service_hosts(host)


def validate_blob_url(url: str, allowed_hosts: Set[str]) -> str:
    """Assert that a blob url points at storage this function may read.

    This function appends its own storage sas token to the url before handing it
    to ADX, so an off-account url would deliver that token to whoever controls
    the host. Validation is performed on the raw url string, before the token is
    attached and before ADX resolves it.

    :param url: untrusted blob url taken from the queue message
    :param allowed_hosts: hostnames the function is entitled to read from
    :return: the validated url
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
    if parts.query or parts.fragment:
        # The sas token is added here, from configuration. One arriving on the
        # message would either be someone else's or an attempt to override ours.
        raise ValidationError('Blob url must not carry a query string or fragment.')

    hostname = (parts.hostname or '').lower()
    # Exact match only. A suffix match would accept lookalikes such as
    # "myacct.blob.core.windows.net.attacker.example".
    if hostname not in allowed_hosts:
        raise ValidationError('Blob url host {!r} is not an allowed storage host.'.format(hostname))
    return url


def blob_path_segments(url: str) -> list:
    """Return the container and blob path segments of a validated blob url.

    The path is percent decoded first, because that is what the storage sdk
    resolves the blob name to. Checking the encoded form instead would accept
    ``%2e%2e`` as an ordinary segment while the request addressed ``..``.

    :param url: a blob url that has already passed host validation
    :return: the decoded path segments, container first
    :raises ValidationError: when the path is malformed
    """
    path = unquote(urlsplit(url).path).lstrip('/')
    if not path:
        raise ValidationError('Blob url does not name a container.')
    if _CONTROL_CHARS_REGEX.search(path):
        raise ValidationError('Blob url path contains control characters.')
    if '\\' in path:
        raise ValidationError('Blob url path must not contain backslashes.')
    segments = path.split('/')
    if any(segment in ('', '.', '..') for segment in segments):
        raise ValidationError('Blob url path contains empty or traversal segments.')
    return segments


def validate_source_location(url: str, allowed_containers: Set[str],
                             required_root: str) -> str:
    """Assert that a blob url names a file inside the directory this app ingests.

    ``allowed_containers`` and ``required_root`` are policy, not conveniences, so
    they have no defaults and a blank value is an error. If they were optional, a
    deployment that failed to supply them would silently widen this function to
    every blob in the account instead of failing.

    :param url: a blob url that has already passed host validation
    :param allowed_containers: containers this function is permitted to read
    :param required_root: directory the blob must live under
    :return: the blob path within the container
    :raises ValidationError: when policy is missing, or the blob is outside it
    """
    if not allowed_containers:
        raise ValidationError('No allowed source containers are configured for this function app.')
    if not required_root:
        raise ValidationError('SOURCE_PATH_ROOT is not configured for this function app.')
    root_segments = required_root.strip('/').split('/')
    if any(segment in ('', '.', '..') for segment in root_segments):
        raise ValidationError(
            'SOURCE_PATH_ROOT {!r} is not a valid directory.'.format(required_root))

    segments = blob_path_segments(url)
    container, path_segments = segments[0], segments[1:]
    if not _CONTAINER_NAME_REGEX.match(container):
        raise ValidationError('Container name {!r} is not a valid Azure container name.'.format(container))
    if container not in allowed_containers:
        raise ValidationError('Container {!r} is not one this function app serves.'.format(container))

    # Compare whole segments. A prefix comparison would also accept a sibling
    # directory whose name merely starts with the expected one. The comparison is
    # exact because Azure blob names are case sensitive.
    if path_segments[:len(root_segments)] != root_segments:
        raise ValidationError(
            'Blob path {!r} is outside the {!r} directory.'.format(
                '/'.join(path_segments), required_root))
    if len(path_segments) <= len(root_segments):
        raise ValidationError('Blob url does not name a file.')
    return '/'.join(path_segments)


def build_database_allow_list(name_format: Optional[str], count: Optional[int]) -> Set[str]:
    """Build the set of ADX databases this deployment provisioned.

    The provisioning tool creates databases by substituting 0..count-1 into
    ``name_format``. Both sides call the same policy, so the set authorised here
    is the set that was created, and a configuration one side would refuse cannot
    be accepted by the other.

    :param name_format: the name template, e.g. ``company-id-{INDEX}``
    :param count: how many databases the deployment created
    :return: the set of database names
    :raises ValidationError: when the format or count is unusable
    """
    try:
        return build_database_names(name_format, count)
    except PolicyError as exc:
        raise ValidationError(str(exc))


def build_table_allow_list(raw: Optional[str]) -> Set[str]:
    """Build the set of ADX tables this deployment provisioned.

    Applies the same rule the provisioning tool used when it created them, so a
    table list one side would refuse is not silently authorised by the other.

    :param raw: comma separated table names
    :return: the set of table names
    :raises ValidationError: when the list is unusable
    """
    try:
        return set(validate_table_list(normalise_table_list(raw)))
    except PolicyError as exc:
        raise ValidationError(str(exc))


def validate_selector_keys(database_key: Optional[str], table_key: Optional[str]) -> None:
    """Assert that the two destination markers can name two different things.

    A blob path is expected to carry one database directory and one table
    directory. If the markers were equal, or one were a prefix of the other, a
    single directory would answer both questions and the path could no longer
    express which database and which table were meant.

    :param database_key: the marker that introduces the database directory
    :param table_key: the marker that introduces the table directory
    :raises ValidationError: when the pair cannot express that grammar
    """
    for value, name in ((database_key, 'DATABASEID_KEY'), (table_key, 'TABLEID_KEY')):
        if not value or not isinstance(value, str):
            raise ValidationError('{} is not configured for this function app.'.format(name))
        if '/' in value:
            raise ValidationError('{} must name part of one path segment.'.format(name))
        if '\\' in value or _CONTROL_CHARS_REGEX.search(value):
            # Path validation refuses these characters, so a selector containing
            # one could never match a blob this function is willing to read.
            raise ValidationError(
                '{} contains characters a blob path may not carry.'.format(name))
    if database_key.startswith(table_key) or table_key.startswith(database_key):
        raise ValidationError(
            'DATABASEID_KEY {!r} and TABLEID_KEY {!r} cannot select different directories.'.format(
                database_key, table_key))


def validate_content_length(size) -> int:
    """Assert that the size on the queue message is a file length.

    The value is forwarded to ADX as the raw data size of the blob, and this
    function treats its queue as untrusted, so it cannot rely on the producer
    having checked it.

    :param size: the contentLength taken from the queue message
    :return: the validated size
    :raises ValidationError: when the value is not a file length
    """
    if isinstance(size, bool) or not isinstance(size, int):
        raise ValidationError('Content length {!r} is not a whole number.'.format(size))
    if not 0 <= size <= MAX_BLOB_SIZE_BYTES:
        raise ValidationError(
            'Content length {!r} is outside the range a file can take.'.format(size))
    return size


def validate_target(value: Optional[str], kind: str, allowed_values: Set[str],
                    fold_case: bool = False) -> str:
    """Assert that a destination the blob path selected is one this app provisioned.

    The directories that carry these values are named from the telemetry itself,
    so the value is only ever a request. Checking it against the destinations the
    deployment actually created is what turns that request into an authorisation.

    With ``fold_case`` the provisioned spelling is returned rather than the one
    from the path. Kusto identifiers are case sensitive, so the name that reaches
    the ingestion properties has to be the one that was created, not the casing a
    telemetry field happened to use.

    :param value: the database or table name taken from the blob path
    :param kind: which of the two, for the error message
    :param allowed_values: the destinations this deployment provisioned
    :param fold_case: match without regard to case and return the provisioned name
    :return: the validated destination name
    :raises ValidationError: when the value is missing, malformed or not allowed
    """
    if not allowed_values:
        # Fail closed. An empty allow-list means configuration is missing, and
        # continuing would let a blob path name any database in the cluster.
        raise ValidationError('No allowed target {}s are configured for this function app.'.format(kind))
    if not value or not isinstance(value, str):
        raise ValidationError('Target {} is missing from the blob path.'.format(kind))
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValidationError('Target {} exceeds {} characters.'.format(kind, MAX_IDENTIFIER_LENGTH))

    if fold_case:
        provisioned = {allowed.upper(): allowed for allowed in allowed_values}
        if len(provisioned) != len(allowed_values):
            # Two provisioned names differing only by case cannot be told apart
            # from a path, so there is no safe answer to give.
            raise ValidationError(
                'Configured target {}s differ only by case; refusing to guess.'.format(kind))
        if value.upper() not in provisioned:
            raise ValidationError(
                'Target {} {!r} is not one this deployment provisioned.'.format(kind, value))
        return provisioned[value.upper()]

    # Whole-value match against the provisioned set. Nothing is normalised here
    # beyond what the caller already did, so a lookalike cannot pass as a
    # neighbour's destination.
    if value not in allowed_values:
        raise ValidationError(
            'Target {} {!r} is not one this deployment provisioned.'.format(kind, value))
    return value
