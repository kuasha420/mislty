"""
Unit and integration tests for mislty.core.serial_transport and mislty.core.at_parser.
"""

import os
import pty
import select
from pathlib import Path
import pytest

from mislty.core.serial_transport import (
    SerialTransport,
    PortNotFoundError,
    PortBusyError,
    SerialTransportError,
)
from mislty.core.at_parser import (
    AtParser,
    AtCommand,
    AtResponse,
    AtDispatcher,
    parse_error,
    is_urc,
)
from mislty.core.port_resolver import PortResolver


def test_port_not_found():
    """Verify PortNotFoundError on non-existent device node."""
    transport = SerialTransport("/dev/nonexistent_serial_dev_12345")
    with pytest.raises(PortNotFoundError):
        transport.open()


def test_serial_pty_io():
    """Verify SerialTransport read/write operations using a pseudo-terminal pair."""
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    try:
        transport = SerialTransport(slave_name, baudrate=115200, timeout=1.0, exclusive_lock=False)
        transport.open()
        assert transport.is_open is True

        # Test write from transport to master
        test_data = "AT+TEST\r\n"
        transport.write(test_data)

        r, _, _ = select.select([master_fd], [], [], 1.0)
        assert master_fd in r
        received = os.read(master_fd, 1024).decode("utf-8")
        assert received == test_data

        # Test read_line from master to transport
        response_data = b"OK\r\n"
        os.write(master_fd, response_data)

        line = transport.read_line(timeout=1.0)
        assert line == "OK"

        transport.close()
        assert transport.is_open is False
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def test_at_parser_tokens():
    """Test terminal token parsing for success and error conditions."""
    parser = AtParser()

    # OK response
    resp_ok = parser.parse_transaction("AT", ["AT", "OK"])
    assert resp_ok.success is True
    assert resp_ok.lines == []

    # Command with payload
    resp_csq = parser.parse_transaction("AT+CSQ", ["AT+CSQ", "+CSQ: 28,99", "OK"])
    assert resp_csq.success is True
    assert resp_csq.lines == ["+CSQ: 28,99"]
    assert resp_csq.value == "+CSQ: 28,99"

    # Generic ERROR
    resp_err = parser.parse_transaction("AT+INVALID", ["AT+INVALID", "ERROR"])
    assert resp_err.success is False
    assert resp_err.error == "ERROR"

    # 3GPP CME ERROR
    resp_cme = parser.parse_transaction("AT+CPIN?", ["+CME ERROR: 10"])
    assert resp_cme.success is False
    assert resp_cme.error_code == 10
    assert resp_cme.error_detail == "SIM not inserted"

    # 3GPP CMS ERROR
    resp_cms = parser.parse_transaction("AT+CMGS=15", ["+CMS ERROR: 500"])
    assert resp_cms.success is False
    assert resp_cms.error_code == 500
    assert resp_cms.error_detail == "Unknown error"

    # CONNECT response
    resp_conn = parser.parse_transaction("ATD*99#", ["CONNECT 115200"])
    assert resp_conn.success is True

    # Call disconnect tokens
    for tok in ["NO CARRIER", "BUSY", "NO DIALTONE"]:
        resp_term = parser.parse_transaction("ATD", [tok])
        assert resp_term.success is False
        assert resp_term.error == tok


def test_at_parser_prompt_mode():
    """Test interactive prompt ('> ') parsing for SMS and USSD."""
    parser = AtParser()
    resp_prompt = parser.parse_transaction("AT+CMGS=\"+8801700000000\"", [">"], prompt_mode=True)
    assert resp_prompt.success is True
    assert resp_prompt.is_prompt is True


def test_urc_filtering():
    """Test unsolicited result codes (URC) extraction during AT response parsing."""
    urcs_received = []

    def handle_urc(line: str):
        urcs_received.append(line)

    parser = AtParser(urc_callback=handle_urc)
    raw_lines = [
        "AT+CSQ",
        "+CMTI: \"SM\", 5",   # Incoming SMS URC
        "^MODE: 3, 2",       # Qualcomm Mode URC
        "+CSQ: 31,99",
        "OK",
    ]

    resp = parser.parse_transaction("AT+CSQ", raw_lines)
    assert resp.success is True
    assert resp.lines == ["+CSQ: 31,99"]
    assert len(urcs_received) == 2
    assert "+CMTI: \"SM\", 5" in urcs_received
    assert "^MODE: 3, 2" in urcs_received


@pytest.mark.hardware
def test_live_hardware_at_commands():
    """Verify AT transaction execution on live Qualcomm MDM9600 hardware."""
    resolver = PortResolver()
    ports = resolver.resolve()
    if not ports.is_ready or not ports.control:
        pytest.skip("No Qualcomm MDM9600 hardware connected on control port.")

    transport = SerialTransport(ports.control, timeout=3.0)
    dispatcher = AtDispatcher(transport)

    # 1. Basic AT ping
    resp_at = dispatcher.execute("AT")
    assert resp_at.success is True

    # 2. Identification query (ATI)
    resp_ati = dispatcher.execute("ATI")
    assert resp_ati.success is True
    assert any("QUALCOMM" in line.upper() for line in resp_ati.lines)

    # 3. Signal quality query (AT+CSQ)
    resp_csq = dispatcher.execute("AT+CSQ")
    assert resp_csq.success is True
    assert any("+CSQ:" in line for line in resp_csq.lines)

    # 4. SIM status query (AT+CPIN?)
    resp_cpin = dispatcher.execute("AT+CPIN?")
    assert resp_cpin.success is True
    assert any("+CPIN:" in line for line in resp_cpin.lines)

    transport.close()
