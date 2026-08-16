"""
  [Microsoft Kusto Lab Project]

  Configuration policy shared by provisioning and ingestion.

  The ingestion function rebuilds its allow-list of ADX destinations from the
  same database name format, database count and table list used here. A
  configuration accepted by one side and refused by the other would provision
  without complaint and then reject every file, so the rule lives in one place.
"""
import re

# Table names are written into management commands, and the ingestion function
# has to be able to name them from a blob path, so they are kept to a plain
# identifier.
TABLE_NAME_REGEX = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,1023}$')


def validate_provisioning_policy(name_format, count, table_list):
    """Refuse a configuration the ingestion function could never serve.

    :param name_format: the database name template, which must contain {INDEX}
    :param count: how many databases are about to be provisioned
    :param table_list: the normalised table names
    :raises ValueError: when the configuration cannot be served
    """
    if not name_format or '{INDEX}' not in name_format:
        raise ValueError(
            'DATABASE_NAME_FORMAT {!r} must contain {{INDEX}}.'.format(name_format))
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError('Database count must be a positive number; got {!r}.'.format(count))
    try:
        names = {name_format.format(INDEX=index) for index in range(count)}
    except Exception as exc:  # pylint: disable=broad-except
        # Any way the template fails to render is a configuration error, not a
        # different kind of problem, so they are all reported the same way.
        raise ValueError(
            'DATABASE_NAME_FORMAT {!r} is not a usable name template: {}.'.format(
                name_format, exc))
    # Checked against the real count. A template that varies for the first few
    # indices can still collapse across the whole range.
    if len(names) != count:
        raise ValueError(
            'DATABASE_NAME_FORMAT {!r} produced {} names for {} databases.'.format(
                name_format, len(names), count))
    if any('{' in name or '}' in name for name in names):
        raise ValueError(
            'DATABASE_NAME_FORMAT {!r} leaves unresolved braces in the name.'.format(name_format))

    if not table_list:
        raise ValueError('TABLE_LIST_STR names no tables.')
    if len({name.upper() for name in table_list}) != len(set(table_list)):
        # The ingestion function matches a table without regard to case, so two
        # names that fold together could not be told apart from a blob path.
        raise ValueError('TABLE_LIST_STR contains names that differ only by case.')
    for name in table_list:
        if not TABLE_NAME_REGEX.match(name):
            raise ValueError('Table name {!r} is not a plain identifier.'.format(name))
