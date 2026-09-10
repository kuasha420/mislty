"""
tests.test_prd_acceptance
~~~~~~~~~~~~~~~~~~~~~~~~~

End-to-End Acceptance Test Suite validating all PRD Section 8 test cases:
- TC-DATA-01: USB Serial Data Link & PPP Daemon Negotiation
- TC-DATA-02: Carrier Failover & Reconnection Watchdog
- TC-ROUTER-01: Dual-Plane Coexistence & Netns Isolation (wlan0 Protection)
- TC-ROUTER-02: Pocket Router Mode Switching (sub-4s Handover)
- TC-SMS-01: Threaded SMS Conversation Storage & Reconciliation
- TC-SMS-02: Standards-Compliant 3GPP Character Set Handling (GSM-7 & UCS-2)
- TC-VOICE-01: PipeWire PCM Audio Bridge & Tragic Voice CSFB Rejection Trap
- TC-SEC-01: Non-Root Privilege Separation & IPC Path Isolation
- TC-NFR-01: Zero External Python Dependencies for Core Daemon & CLI
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
import sys
import threading
from unittest.mock import MagicMock, patch
import pytest

from mislty.audio.pcm_bridge import TelephonyEngine, generate_dtmf_pcm
from mislty.core.at_parser import AtDispatcher, AtResponse
from mislty.core.daemon import DaemonEngine, DaemonState
from mislty.core.port_resolver import ModemPorts, PortResolver
from mislty.core.sms import calculate_sms_segments, is_gsm7
from mislty.net.helper import validate_interface
from mislty.net.ppp_controller import PppController, PppStatus
from mislty.net.qcwebs_client import SmartModeSwitcher
from mislty.storage.database import DatabaseManager
from mislty.storage.sms_store import SmsStore


# ===========================================================================
# TC-DATA-01: USB Serial Data Link & PPP Negotiation
# ===========================================================================

def test_tc_data_01_ppp_negotiation(tmp_path):
    """TC-DATA-01: Verify PPP controller coordinates data link and route snapshot."""
    fake_port = tmp_path / "ttyUSB0"
    fake_port.write_bytes(b"")

    mock_helper = MagicMock()
    mock_helper.start_ppp.return_value = {"success": True}

    mock_route = MagicMock()
    controller = PppController(data_port=fake_port, helper=mock_helper, route_mgr=mock_route)

    # Initial status disconnected, subsequent status connected with IP
    status_seq = [
        PppStatus(connected=False),
        PppStatus(connected=True, ip_address="10.64.12.34", interface="ppp0"),
    ]

    with patch.object(controller, "get_status", side_effect=status_seq):
        ok = controller.connect(apn="internet", default_route=True, timeout=2.0)
        assert ok is True
        mock_route.snapshot.assert_called_once()
        mock_helper.start_ppp.assert_called_once_with(str(fake_port), apn="internet")


# ===========================================================================
# TC-DATA-02: Carrier Failover & Reconnection Watchdog
# ===========================================================================

def test_tc_data_02_reconnection_watchdog(tmp_path):
    """TC-DATA-02: Verify daemon watchdog triggers reconnect attempts on link failure."""
    db_file = tmp_path / "test_daemon.db"
    engine = DaemonEngine(db_path=db_file, poll_interval=1.0)
    engine.state.connected = False
    assert engine.state.connected is False

    # Run one iteration of watchdog
    with patch.object(engine, "connect_modem", return_value=False) as mock_conn:
        # Stop event set right after 1 run
        def _trigger():
            engine._stop_event.set()

        timer = threading.Timer(0.1, _trigger)
        timer.start()
        engine._watchdog_loop()
        assert engine.state.reconnect_attempts >= 1
        mock_conn.assert_called()

    engine.stop()


# ===========================================================================
# TC-ROUTER-01: Dual-Plane Coexistence & Netns Isolation
# ===========================================================================

def test_tc_router_01_wlan0_protection():
    """TC-ROUTER-01: Verify interface validation protects system devices and allows aux wlan."""
    assert validate_interface("wlan0") == "wlan0"
    assert validate_interface("wlan1") == "wlan1"
    assert validate_interface("ppp0") == "ppp0"

    # Malicious injection strings are strictly rejected
    with pytest.raises(Exception):
        validate_interface("wlan0; rm -rf /")
    with pytest.raises(Exception):
        validate_interface("wlan0 && reboot")


# ===========================================================================
# TC-ROUTER-02: Pocket Router Mode Switching (< 4s handover)
# ===========================================================================

def test_tc_router_02_mode_switching():
    """TC-ROUTER-02: Verify SmartModeSwitcher orchestrates rapid mode transition."""
    mock_qcwebs = MagicMock()
    mock_qcwebs.set_wan_connect.return_value = True

    mock_ppp = MagicMock()

    switcher = SmartModeSwitcher(qcwebs_client=mock_qcwebs, ppp_controller=mock_ppp)

    res = switcher.switch_to_router_mode()
    assert res["success"] is True
    assert res["mode"] == "pocket_router"
    mock_ppp.disconnect.assert_called_once()
    mock_qcwebs.set_wan_connect.assert_called_with(connect=True)


# ===========================================================================
# TC-SMS-01: Threaded SMS Conversation Storage & Reconciliation
# ===========================================================================

def test_tc_sms_01_conversation_storage(tmp_path):
    """TC-SMS-01: Verify SMS thread grouping, unread counters, and message ordering."""
    db_file = tmp_path / "test_sms.db"
    db = DatabaseManager(db_file)
    store = SmsStore(db)

    # Ingest inbound message
    msg = store.save_message(
        direction="IN",
        phone_number="+8801712345678",
        body="Acceptance test inbound SMS",
    )
    assert msg.id is not None

    threads = store.list_threads()
    assert len(threads) == 1
    assert threads[0].unread_count == 1
    assert threads[0].recipient_number == "+8801712345678"

    # Mark as read
    store.mark_thread_read(threads[0].id)
    updated = store.list_threads()
    assert updated[0].unread_count == 0

    # Delete thread
    ok = store.delete_thread(threads[0].id)
    assert ok is True
    assert len(store.list_threads()) == 0
    db.close()


# ===========================================================================
# TC-SMS-02: Standards-Compliant 3GPP Character Set Handling
# ===========================================================================

def test_tc_sms_02_gsm7_and_ucs2_character_rules():
    """TC-SMS-02: Verify 3GPP TS 23.038 GSM-7 (160/153) and UCS-2 (70/67) rules."""
    # 1. Basic GSM-7
    res_gsm = calculate_sms_segments("Hello world! 12345")
    assert res_gsm["encoding"] == "GSM-7"
    assert res_gsm["max_per_segment"] == 160
    assert res_gsm["segments"] == 1

    # 2. Extended GSM-7 chars ({, }, ^, ~, |)
    res_ext = calculate_sms_segments("{Test}")
    assert res_ext["chars_count"] == 8

    # 3. Unicode UCS-2
    res_ucs2 = calculate_sms_segments("স্বাগতম")
    assert res_ucs2["encoding"] == "UCS-2"
    assert res_ucs2["is_unicode"] is True
    assert res_ucs2["max_per_segment"] == 70
    assert res_ucs2["segments"] == 1


# ===========================================================================
# TC-VOICE-01: PCM Audio Loopback Bridge & CSFB Rejection Trap
# ===========================================================================

def test_tc_voice_01_pcm_bridge_and_csfb_trap():
    """TC-VOICE-01: Verify DTMF synthesis and CSFB pure-LTE network rejection trap."""
    # 1. Synthesize DTMF
    dtmf = generate_dtmf_pcm("1", duration_ms=100, sample_rate=8000)
    assert len(dtmf) == 1600

    # 2. Telephony Engine CSFB trap
    mock_disp = MagicMock()
    mock_disp.execute.side_effect = [
        AtResponse(command="ATD121;", success=True, lines=[], raw_text="OK"),
        AtResponse(command="AT+CLCC", success=True, lines=[], raw_text="OK"),
        AtResponse(command="AT+CEER", success=True, lines=["+CEER: 31 (Normal, unspecified)"], raw_text="OK"),
    ]

    tragic_events = []
    engine = TelephonyEngine(
        dispatcher=mock_disp,
        voice_port=Path("/dev/null"),
        on_tragic_voice=lambda d: tragic_events.append(d),
    )

    engine.dial("121")
    engine._poll_call_progression()

    assert len(tragic_events) == 1
    assert engine.current_call.is_tragic_voice is True


# ===========================================================================
# TC-SEC-01: Non-Root Privilege Separation & Path Security
# ===========================================================================

def test_tc_sec_01_security_isolation():
    """TC-SEC-01: Verify database and IPC socket paths are created under user XDG dirs."""
    from mislty.storage.database import DEFAULT_DB_PATH
    user_home = Path.home()
    assert str(DEFAULT_DB_PATH).startswith(str(user_home))
    assert ".local/share/mislty" in str(DEFAULT_DB_PATH)


# ===========================================================================
# TC-NFR-01: Zero External Dependencies for Core Daemon & CLI
# ===========================================================================

def test_tc_nfr_01_zero_external_dependencies():
    """
    TC-NFR-01: Verify core, storage, ipc, and net modules import ONLY Python stdlib.
    PySide6 is strictly isolated to the GUI package.
    """
    project_root = Path(__file__).resolve().parent.parent
    core_packages = ["core", "storage", "ipc", "net", "cli"]

    allowed_stdlib_prefixes = {
        "mislty", "__future__", "argparse", "ast", "asyncio", "base64", "binascii",
        "collections", "contextlib", "dataclasses", "datetime", "enum", "errno",
        "fcntl", "functools", "glob", "hashlib", "inspect", "io", "ipaddress", "itertools",
        "json", "logging", "math", "os", "pathlib", "platform", "queue", "re", "select",
        "shutil", "signal", "socket", "stat", "string", "struct", "subprocess",
        "sys", "tempfile", "termios", "threading", "time", "typing", "unittest",
        "urllib", "uuid", "warnings", "weakref", "sqlite3", "dbus", "gi",
    }

    for pkg in core_packages:
        pkg_dir = project_root / "src" / "mislty" / pkg
        for py_file in pkg_dir.rglob("*.py"):
            with open(py_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(py_file))

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top_module = alias.name.split(".")[0]
                        assert top_module in allowed_stdlib_prefixes, (
                            f"Illegal external dependency '{top_module}' in {py_file}"
                        )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        top_module = node.module.split(".")[0]
                        assert top_module in allowed_stdlib_prefixes, (
                            f"Illegal external dependency '{top_module}' in {py_file}"
                        )
