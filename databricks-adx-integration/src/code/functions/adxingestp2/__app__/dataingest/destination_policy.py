"""
  [Microsoft Kusto Lab Project]

  The ADX destinations a deployment provisions, and therefore authorises.

  The provisioning tool creates databases and tables from a name format, a count
  and a table list. The ingestion function rebuilds the same set from the same
  three values and refuses anything else. A configuration accepted by one side
  and refused by the other would provision without complaint and then reject
  every file, so both sides apply this module.

  It is deployed inside two independent artifacts, so an identical copy lives
  beside each. A test asserts the two copies stay identical; this file is the
  source, and the copy under the function app is generated from it.

  It deliberately has no dependencies beyond the standard library.
"""
import re

# Well above the documented lab value of 100, but bounded so a mistyped count
# cannot ask either side to build an unreasonable set.
MAX_DATABASE_COUNT = 100000

# Azure resource names for a Kusto database allow alphanumerics, hyphens, spaces
# and periods, up to 260 characters. Anything else fails late in Azure, or is
# unsafe to interpolate into a management command.
DATABASE_NAME_REGEX = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 .-]{0,259}$')

# Table names are written into management commands, and the ingestion function
# has to be able to name them from a blob path, so they are kept to a plain
# identifier.
TABLE_NAME_REGEX = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,1023}$')


class PolicyError(ValueError):
    """Raised when a configuration cannot be served by both sides."""


def build_database_names(name_format, count):
    """Return the database names a deployment of this size provisions.

    :param name_format: the name template, which must contain {INDEX}
    :param count: how many databases the deployment creates
    :return: the set of database names
    :raises PolicyError: when the format or count cannot produce that set
    """
    if not name_format or not isinstance(name_format, str) or '{INDEX}' not in name_format:
        raise PolicyError(
            'Database name format {!r} must contain {{INDEX}}.'.format(name_format))
    if not isinstance(count, int) or isinstance(count, bool) or not 0 < count <= MAX_DATABASE_COUNT:
        raise PolicyError(
            'Database count must be between 1 and {}; got {!r}.'.format(MAX_DATABASE_COUNT, count))
    try:
        names = {name_format.format(INDEX=index) for index in range(count)}
    except Exception as exc:  # pylint: disable=broad-except
        # Any way the template fails to render is a configuration error, not a
        # different kind of problem, so they are all reported the same way.
        raise PolicyError(
            'Database name format {!r} is not a usable template: {}.'.format(name_format, exc))
    # Checked against the real count. A template that varies across the first few
    # indices can still collapse across the whole range.
    if len(names) != count:
        raise PolicyError(
            'Database name format {!r} produced {} names for {} databases.'.format(
                name_format, len(names), count))
    for name in sorted(names):
        if not DATABASE_NAME_REGEX.match(name):
            raise PolicyError(
                'Database name {!r} is not a valid Azure Data Explorer database name.'.format(name))
    return names


def normalise_table_list(raw):
    """Split, trim and de-duplicate a configured table list.

    Exact repeats are dropped in order, so provisioning issues one command per
    table and the list it creates matches the set the ingestion function builds
    from the same configuration.

    :param raw: comma separated table names, or an already split sequence
    :return: the trimmed names, in the order first given
    """
    if raw is None:
        return []
    entries = raw.split(',') if isinstance(raw, str) else list(raw)
    names = []
    for entry in entries:
        name = str(entry).strip()
        if name and name not in names:
            names.append(name)
    return names


def validate_table_list(tables):
    """Assert that a table list names tables both sides can agree on.

    :param tables: the normalised table names
    :return: the validated names
    :raises PolicyError: when the list cannot be served
    """
    if not tables:
        raise PolicyError('The table list names no tables.')
    if len({name.upper() for name in tables}) != len(set(tables)):
        # The ingestion function matches a table without regard to case, so two
        # names that fold together could not be told apart from a blob path.
        raise PolicyError('The table list contains names that differ only by case.')
    for name in tables:
        if not TABLE_NAME_REGEX.match(name):
            raise PolicyError('Table name {!r} is not a plain identifier.'.format(name))
    return tables


def validate_destination_policy(name_format, count, tables):
    """Assert that a whole destination configuration can be served.

    :param name_format: the database name template
    :param count: how many databases the deployment creates
    :param tables: the normalised table names
    :return: (database names, table names)
    :raises PolicyError: when the configuration cannot be served
    """
    return build_database_names(name_format, count), validate_table_list(tables)
