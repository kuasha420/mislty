"""Test scaffolding, package layout, and basic CLI entrypoints."""

import pytest
import mislty
from mislty.cli.main import build_parser

def test_package_metadata():
    """Verify package version and authors."""
    assert mislty.__version__ == "1.0.0"
    assert "Purrfect" in mislty.__author__

def test_cli_parser_version():
    """Verify CLI parser --version output."""
    parser = build_parser()
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(["--version"])
    assert exc_info.value.code == 0

def test_cli_parser_subcommands():
    """Verify that all core operational subcommands are configured in CLI parser."""
    parser = build_parser()
    
    test_cases = [
        (["status"], "status"),
        (["connect"], "connect"),
        (["disconnect"], "disconnect"),
        (["wifi", "status"], "wifi"),
        (["mode", "router"], "mode"),
        (["sim"], "sim"),
        (["sms", "list"], "sms"),
        (["at", "AT+CSQ"], "at"),
    ]
    
    for args, expected_sub in test_cases:
        parsed = parser.parse_args(args)
        assert parsed.subcommand == expected_sub

def test_daemon_parser():
    """Verify daemon parser flags."""
    from mislty.core.daemon import build_parser as build_daemon_parser
    parser = build_daemon_parser()
    parsed = parser.parse_args(["-f"])
    assert parsed.foreground is True
