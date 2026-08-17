import hashlib
import os

import pytest

import __app__.dataingest.destination_policy as policy
import __app__.dataingest.validation as validation

# The policy is deployed inside two independent artifacts, so an identical copy
# lives beside each. This is the source; the function app carries the copy.
_SOURCE = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', '..', 'tools', 'ADXProvisionTool',
    'destination_policy.py'))
_COPY = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '__app__', 'dataingest', 'destination_policy.py'))


def _digest(path):
    with open(path, 'rb') as handle:
        return hashlib.sha256(handle.read()).hexdigest()


# Every configuration below is fed to both sides. Neither may accept what the
# other refuses, because provisioning creates the destinations the function then
# authorises.
POLICY_MATRIX = [
    ('company-id-{INDEX}', 3, 'CO2,TEMP'),
    ('company-id-{INDEX}', 1, 'CO2'),
    ('company-id-{INDEX}', 100, 'CO2, TEMP'),
    ('company id {INDEX}', 3, 'CO2'),
    ('company.id.{INDEX}', 3, 'Temp'),
    # Formats that cannot produce one name per database.
    ('{{INDEX}}', 3, 'CO2'),
    ('company-id-{{INDEX}}', 3, 'CO2'),
    ('db-{INDEX:.0e}', 100, 'CO2'),
    ('company-id', 3, 'CO2'),
    ('company-{INDEX}-{OTHER', 3, 'CO2'),
    ('company-{INDEX}-{INDEX.foo}', 3, 'CO2'),
    ('company-{INDEX}-{INDEX[foo]}', 3, 'CO2'),
    ('', 3, 'CO2'),
    # Names Azure Data Explorer would refuse, or that are unsafe to interpolate.
    ('db;drop-{INDEX}', 3, 'CO2'),
    ('db]-{INDEX}', 3, 'CO2'),
    ('db/{INDEX}', 3, 'CO2'),
    ('-db-{INDEX}', 3, 'CO2'),
    ('d' * 300 + '{INDEX}', 3, 'CO2'),
    # Counts outside the range either side will build.
    ('company-id-{INDEX}', 0, 'CO2'),
    ('company-id-{INDEX}', -1, 'CO2'),
    ('company-id-{INDEX}', 100001, 'CO2'),
    # Table lists neither side can serve.
    ('company-id-{INDEX}', 3, ''),
    ('company-id-{INDEX}', 3, 'Temp,TEMP'),
    ('company-id-{INDEX}', 3, 'CO2,bad name'),
    ('company-id-{INDEX}', 3, 'CO2,drop-table'),
    ('company-id-{INDEX}', 3, 'CO2,2TEMP'),
    ('company-id-{INDEX}', 3, 'CO2,.show'),
]


class TestSharedDestinationPolicy():
    def test_the_two_copies_are_identical(self):
        # If they drift, provisioning and ingestion stop agreeing on which
        # destinations exist, which is the failure this module exists to prevent.
        assert _digest(_SOURCE) == _digest(_COPY), (
            'destination_policy.py differs between the provisioning tool and the '
            'function app; copy the provisioning tool version over the app one')

    @pytest.mark.parametrize('name_format,count,tables', POLICY_MATRIX)
    def test_provisioning_and_runtime_agree(self, name_format, count, tables):
        try:
            policy.validate_destination_policy(
                name_format, count, policy.normalise_table_list(tables))
            provisioning_accepted = True
        except policy.PolicyError:
            provisioning_accepted = False

        try:
            validation.build_database_allow_list(name_format, count)
            validation.build_table_allow_list(tables)
            runtime_accepted = True
        except validation.ValidationError:
            runtime_accepted = False

        assert provisioning_accepted == runtime_accepted, (
            'provisioning and the ingestion function disagree about '
            '{!r} x {} with tables {!r}'.format(name_format, count, tables))

    @pytest.mark.parametrize('name_format,count,tables', POLICY_MATRIX)
    def test_both_sides_produce_the_same_destinations(self, name_format, count, tables):
        try:
            databases, table_names = policy.validate_destination_policy(
                name_format, count, policy.normalise_table_list(tables))
        except policy.PolicyError:
            pytest.skip('configuration is refused by both sides')

        assert validation.build_database_allow_list(name_format, count) == databases
        assert validation.build_table_allow_list(tables) == set(table_names)

    def test_the_documented_configuration_is_served(self):
        databases, tables = policy.validate_destination_policy(
            'company-id-{INDEX}', 100, policy.normalise_table_list('CO2,TEMP'))
        assert len(databases) == 100
        assert 'company-id-99' in databases
        assert tables == ['CO2', 'TEMP']
