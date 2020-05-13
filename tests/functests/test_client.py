import pytest
from click.testing import CliRunner

from openvisualizer.client.main import cli


def test_start_cli():
    """ Tests entry point command. """
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_list_support_rpcs(server):
    runner = CliRunner()
    result = runner.invoke(cli, ['list-methods'])
    assert result.exit_code == 0
    assert "boot_motes" in result.output


def test_list_support_rpcs_booted(server_booted):
    runner = CliRunner()
    result = runner.invoke(cli, ['list-methods'])
    assert result.exit_code == 0
    assert "boot_motes" in result.output


def test_get_motes(server):
    runner = CliRunner()
    result = runner.invoke(cli, ['get-motes'])
    assert result.exit_code == 0
    assert "Attached motes:" in result.output


def test_get_motes_booted(server_booted):
    runner = CliRunner()
    result = runner.invoke(cli, ['get-motes'])
    assert result.exit_code == 0
    assert "Attached motes:" in result.output


@pytest.mark.parametrize('opts', ['--mote=all', '--mote=0001'])
def test_boot_command(server, opts):
    runner = CliRunner()
    result = runner.invoke(cli, ['boot', opts])
    assert result.exit_code == 0


@pytest.mark.parametrize('opts', ['--mote=all', '--mote=0001'])
def test_boot_command_booted(server_booted, opts):
    runner = CliRunner()
    result = runner.invoke(cli, ['boot', opts])
    assert result.exit_code == 0


@pytest.mark.parametrize(
    'opts, out',
    [('0001', 'Ok!'), ('emulated1', 'Ok!'),
     ('6846', 'Unknown port or address'),
     ('emulated', 'Unknown port or address')])
def test_set_root_booted(server_booted, opts, out):
    runner = CliRunner()
    result = runner.invoke(cli, ['root', opts])
    assert result.exit_code == 0
    assert out in result.output


@pytest.mark.parametrize(
    'opts, out',
    [('0001', 'Unknown port or address'), ('emulated1', 'Could not set None as root'),
     ('6846', 'Unknown port or address'), ('emulated', 'Unknown port or address')])
def test_set_root(server, opts, out):
    runner = CliRunner()
    result = runner.invoke(cli, ['root', opts])
    assert result.exit_code == 0
    assert out in result.output


def test_start_view(server):
    runner = CliRunner()
    result = runner.invoke(cli, ['view'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
