"""
Unit tests for MisLTy CLI suite and formatting engine:
- TerminalFormatter (ANSI styling, signal meters, tables, byte formatting)
- CLI argument parsing and flags
- Subcommand execution flows
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from mislty.cli.formatter import Colors, TerminalFormatter
from mislty.cli.main import build_parser, main


# ---------------------------------------------------------------------------
# Formatter Tests
# ---------------------------------------------------------------------------

def test_formatter_styling():
    """Verify ANSI color application and disable behavior."""
    fmt_on = TerminalFormatter(force_color=True)
    fmt_off = TerminalFormatter(force_color=False)

    styled = fmt_on.bold("Hello")
    assert Colors.BOLD in styled
    assert Colors.RESET in styled

    plain = fmt_off.bold("Hello")
    assert plain == "Hello"
    assert Colors.BOLD not in plain

    assert Colors.GREEN in fmt_on.green("OK")
    assert Colors.RED in fmt_on.red("FAIL")
    assert Colors.YELLOW in fmt_on.yellow("WARN")
    assert Colors.CYAN in fmt_on.cyan("INFO")


def test_formatter_signal_meter():
    """Verify signal meter levels and formatting."""
    fmt = TerminalFormatter(force_color=False)

    no_sig = fmt.format_signal_meter(None)
    assert "No Signal" in no_sig

    weak_sig = fmt.format_signal_meter(5, dbm=-103)
    assert "5/31" in weak_sig
    assert "-103 dBm" in weak_sig
    assert "weak" in weak_sig

    full_sig = fmt.format_signal_meter(31, dbm=-51)
    assert "31/31" in full_sig
    assert "4/4 bars" in full_sig
    assert "██████████" in full_sig


def test_formatter_badge():
    """Verify status badge formatting."""
    fmt = TerminalFormatter(force_color=False)
    assert "ONLINE" in fmt.format_badge(True)
    assert "OFFLINE" in fmt.format_badge(False)
    assert "CONNECTED" in fmt.format_badge(True, on_text="CONNECTED")


def test_formatter_bytes():
    """Verify byte size formatting."""
    fmt = TerminalFormatter(force_color=False)
    assert fmt.format_bytes(512) == "512.0 B"
    assert fmt.format_bytes(1024 * 100) == "100.0 KB"
    assert fmt.format_bytes(1024 * 1024 * 15.5) == "15.5 MB"
    assert fmt.format_bytes(1024 * 1024 * 1024 * 2.5) == "2.5 GB"


def test_formatter_table():
    """Verify table alignment and formatting."""
    fmt = TerminalFormatter(force_color=False)
    headers = ["ID", "Name", "Role"]
    rows = [
        ["1", "Alice", "Admin"],
        ["20", "Bob", "User"],
    ]
    table = fmt.format_table(headers, rows)
    lines = table.splitlines()
    assert len(lines) == 4  # Header, separator, row 1, row 2
    assert "Alice" in lines[2]
    assert "Bob" in lines[3]


# ---------------------------------------------------------------------------
# CLI Parser & Subcommand Tests
# ---------------------------------------------------------------------------

def test_parser_options():
    """Verify CLI argument parsing structure."""
    parser = build_parser()

    # Root flags
    args = parser.parse_args(["--no-color", "status"])
    assert args.no_color is True
    assert args.subcommand == "status"

    # Connect flags
    args_conn = parser.parse_args(["connect", "--apn", "custom.apn", "--default", "--timeout", "15"])
    assert args_conn.subcommand == "connect"
    assert args_conn.apn == "custom.apn"
    assert args_conn.default is True
    assert args_conn.timeout == 15.0

    # Wi-Fi subcommands
    args_wifi = parser.parse_args(["wifi", "ssid", "MyHotspot"])
    assert args_wifi.subcommand == "wifi"
    assert args_wifi.action == "ssid"
    assert args_wifi.param == "MyHotspot"

    # SMS subcommands
    args_sms = parser.parse_args(["sms", "send", "+1234567890", "Hello!"])
    assert args_sms.subcommand == "sms"
    assert args_sms.sms_action == "send"
    assert args_sms.recipient == "+1234567890"
    assert args_sms.text == "Hello!"


def test_cli_status_execution(capsys):
    """Verify mislty status output with mock client."""
    mock_client = MagicMock()
    mock_client.active_transport = "socket"
    mock_client.get_status.return_value = {
        "daemon": {"carrier": "TestCarrier", "rssi": 25, "dbm": -63, "technology": "LTE"},
        "hardware": {"is_present": True, "control": "/dev/mislty/control", "data": "/dev/mislty/data", "aux_wifi": "wlan1"},
        "cellular_ppp": {"connected": True, "interface": "ppp0", "ip_address": "10.0.0.1", "peer_ip": "10.0.0.2", "dns_servers": ["1.1.1.1"], "rx_bytes": 2048, "tx_bytes": 1024, "uptime_seconds": 120.0},
        "wifi": {"power": True, "ssid": "TestAP", "clients_count": 2},
    }

    with patch("mislty.ipc.client.MisltyClient", return_value=mock_client):
        with pytest.raises(SystemExit) as exc_info:
            main(["--no-color", "status"])
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "MisLTy Cellular & Wi-Fi Station" in captured.out
    assert "TestCarrier" in captured.out
    assert "TestAP" in captured.out
    assert "ppp0" in captured.out
    assert "10.0.0.1" in captured.out


def test_cli_status_json_output(capsys):
    """Verify mislty status --json output."""
    mock_client = MagicMock()
    mock_client.get_status.return_value = {"daemon": {"rssi": 31}}

    with patch("mislty.ipc.client.MisltyClient", return_value=mock_client):
        with pytest.raises(SystemExit) as exc_info:
            main(["status", "--json"])
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["daemon"]["rssi"] == 31
