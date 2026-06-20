from click.testing import CliRunner
from overcast_opml_parser.__main__ import cli


def test_cli():
    runner = CliRunner()
    result = runner.invoke(cli, ["tests/fixtures/overcast.opml"])
    print(result.output)
    assert result.exit_code == 0
    assert "The Pen Addict" in result.output


def test_no_cli():
    runner = CliRunner()
    result = runner.invoke(cli, ["nothing"])
    print(result.output)
    # assert result.exit_code == 0
    assert "No such file or directory" in result.output
