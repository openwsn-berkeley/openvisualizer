import pytest
from click.testing import CliRunner

from openvisualizer.client.__main__ import cli


def test_start_cli():
    """ Tests entry point command. """
    runner = CliRunner()
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage:" in result.output


def test_get_motes(server):
    runner = CliRunner()
    result = runner.invoke(cli, ['network', 'motes'])
    assert result.exit_code == 0


def test_start_view(server):
    runner = CliRunner()
    result = runner.invoke(cli, ['view'])
    assert result.exit_code == 0
    assert 'Usage:' in result.output
