import importlib.util
import os

import pytest

# The policy lives beside the provisioning tool and has no sdk dependency, so it
# is loaded by path rather than imported as a package.
_POLICY = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'tools', 'ADXProvisionTool',
                       'provisioning_policy.py')
_SPEC = importlib.util.spec_from_file_location('adx_provisioning_policy', os.path.abspath(_POLICY))
policy = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(policy)


class TestProvisioningPolicy():
    """Provisioning and the ingestion function must agree on the destinations.

    The function rebuilds its allow-list from the same name format and count, so
    a configuration accepted here but refused there would provision cleanly and
    then reject every file.
    """

    def test_the_documented_configuration_is_accepted(self):
        assert policy.validate_provisioning_policy(
            'company-id-{INDEX}', 100, ['CO2', 'TEMP']) is None

    @pytest.mark.parametrize('name_format,count', [
        # Escapes the marker, so every index yields the same name.
        ('{{INDEX}}', 3),
        ('company-id-{{INDEX}}', 3),
        # Distinct across the first two indices but not across the real count,
        # which a two-index sample would have missed.
        ('db-{INDEX:.0e}', 100),
        # No marker at all.
        ('company-id', 3),
        # Templates that fail to render, reported the same way as the rest.
        ('company-{INDEX}-{OTHER', 3),
        ('company-{INDEX}-{INDEX.foo}', 3),
        ('company-{INDEX}-{INDEX[foo]}', 3),
    ])
    def test_a_name_format_that_cannot_serve_the_count_is_refused(self, name_format, count):
        with pytest.raises(ValueError):
            policy.validate_provisioning_policy(name_format, count, ['CO2'])

    @pytest.mark.parametrize('count', [0, -1, True, '3', None])
    def test_an_unusable_database_count_is_refused(self, count):
        with pytest.raises(ValueError):
            policy.validate_provisioning_policy('company-id-{INDEX}', count, ['CO2'])

    @pytest.mark.parametrize('tables', [
        [],
        # The ingestion function matches tables without regard to case, so these
        # two could never be told apart from a blob path.
        ['Temp', 'TEMP'],
        # Written into management commands, so kept to a plain identifier.
        ['CO2', 'bad name'],
        ['CO2', 'drop-table'],
        ['CO2', '2TEMP'],
        ['CO2', 'a"b'],
        ['CO2', '.show'],
    ])
    def test_a_table_list_the_function_could_not_serve_is_refused(self, tables):
        with pytest.raises(ValueError):
            policy.validate_provisioning_policy('company-id-{INDEX}', 3, tables)
