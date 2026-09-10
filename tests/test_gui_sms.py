"""
tests.test_gui_sms
~~~~~~~~~~~~~~~~~~

Comprehensive unit and headless QML integration tests for MisLTy SMS Conversation Deck:
- GSM-7 and UCS-2 character/segment calculators (3GPP TS 23.038).
- Freedesktop notification dispatch.
- MisltyBridge SMS invokable slots (calculateSmsSegments, deleteThread, markAsRead, onSmsReceived).
- Headless QML component instantiation for ChatBubble.qml and SmsView.qml.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from mislty.core.sms import (
    calculate_sms_segments,
    count_gsm7_septets,
    is_gsm7,
    send_desktop_notification,
)
from mislty.gui.app import MisltyBridge, create_app


# ---------------------------------------------------------------------------
# GSM-7 & UCS-2 Standards Verification
# ---------------------------------------------------------------------------

def test_gsm7_charset_detection():
    """Verify standard GSM 7-bit alphabet validation and extension table detection."""
    assert is_gsm7("Hello World 123! @£$¥") is True
    assert is_gsm7("Hello {World} [Test] ^ ~ | \\ €") is True
    # Non-GSM (Bengali, Chinese, Emoji)
    assert is_gsm7("হ্যালো বাংলাদেশ") is False
    assert is_gsm7("MisLTy 🐱") is False
    assert is_gsm7("Привет мир") is False


def test_count_gsm7_septets():
    """Verify extended characters cost 2 septets in GSM-7."""
    basic = "Hello"
    assert count_gsm7_septets(basic) == 5

    # '{' and '}' cost 2 septets each (ESC prefix)
    extended = "Hello {A}"
    # H e l l o <sp> { A } -> 5 + 1 + 2 + 1 + 2 = 11 septets
    assert count_gsm7_septets(extended) == 11


def test_calculate_sms_segments_empty():
    """Verify segment calculation for empty text."""
    res = calculate_sms_segments("")
    assert res["chars_count"] == 0
    assert res["segments"] == 0
    assert res["max_per_segment"] == 160
    assert res["is_unicode"] is False
    assert res["summary"] == "0/160 (0 SMS)"


def test_calculate_sms_segments_gsm7_single():
    """Verify single-part GSM-7 message calculation."""
    text = "Hello from MisLTy cellular suite!"
    res = calculate_sms_segments(text)
    assert res["encoding"] == "GSM-7"
    assert res["is_unicode"] is False
    assert res["chars_count"] == len(text)
    assert res["segments"] == 1
    assert res["max_per_segment"] == 160
    assert res["chars_left_in_segment"] == 160 - len(text)
    assert res["summary"] == f"{len(text)}/160 (1 SMS)"


def test_calculate_sms_segments_gsm7_multipart():
    """Verify multi-part concatenated GSM-7 message calculation (153 chars/segment)."""
    # 160 chars -> 1 segment
    msg_160 = "A" * 160
    res_160 = calculate_sms_segments(msg_160)
    assert res_160["segments"] == 1
    assert res_160["max_per_segment"] == 160

    # 161 chars -> 2 segments (each holds max 153 chars)
    msg_161 = "A" * 161
    res_161 = calculate_sms_segments(msg_161)
    assert res_161["segments"] == 2
    assert res_161["max_per_segment"] == 153
    assert res_161["chars_count"] == 161
    assert res_161["chars_left_in_segment"] == (153 - (161 % 153))
    assert res_161["summary"] == "161/153 (2 SMS)"

    # 310 chars -> 3 segments
    msg_310 = "A" * 310
    res_310 = calculate_sms_segments(msg_310)
    assert res_310["segments"] == 3
    assert res_310["max_per_segment"] == 153


def test_calculate_sms_segments_ucs2_unicode():
    """Verify UCS-2 Unicode message calculation (70 chars single, 67 concatenated)."""
    # Bengali unicode text
    bengali = "হ্যালো"
    res = calculate_sms_segments(bengali)
    assert res["encoding"] == "UCS-2"
    assert res["is_unicode"] is True
    assert res["segments"] == 1
    assert res["max_per_segment"] == 70
    assert res["summary"] == "6/70 (1 SMS Unicode)"

    # Concatenated unicode (> 70 chars)
    long_bengali = "ক" * 75
    res_long = calculate_sms_segments(long_bengali)
    assert res_long["encoding"] == "UCS-2"
    assert res_long["is_unicode"] is True
    assert res_long["segments"] == 2
    assert res_long["max_per_segment"] == 67
    assert res_long["chars_count"] == 75
    assert res_long["summary"] == "75/67 (2 SMS Unicode)"


# ---------------------------------------------------------------------------
# Freedesktop Desktop Notification
# ---------------------------------------------------------------------------

def test_send_desktop_notification_fallback():
    """Verify desktop notification dispatch via notify-send fallback when D-Bus is unavailable."""
    with patch.dict("sys.modules", {"dbus": None}), patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        ok = send_desktop_notification("Test Title", "Test Message Body")
        assert ok is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "notify-send" in args[0]
        assert "Test Title" in args
        assert "Test Message Body" in args


def test_send_desktop_notification_dbus():
    """Verify desktop notification dispatch via D-Bus interface."""
    mock_bus = MagicMock()
    mock_notify_iface = MagicMock()
    with patch("dbus.SessionBus", return_value=mock_bus), \
         patch("dbus.Interface", return_value=mock_notify_iface):
        ok = send_desktop_notification("D-Bus Title", "D-Bus Body")
        assert ok is True
        mock_notify_iface.Notify.assert_called_once()


# ---------------------------------------------------------------------------
# MisltyBridge SMS Slots & Signals
# ---------------------------------------------------------------------------

def test_mislty_bridge_sms_slots():
    """Verify MisltyBridge SMS-specific invokable slots."""
    mock_client = MagicMock()
    mock_client.active_transport = "direct"
    mock_client.delete_sms_thread.return_value = {"success": True, "thread_id": 42}
    mock_client.mark_sms_read.return_value = {"success": True, "thread_id": 42}
    mock_client.list_sms.return_value = [
        {"id": 1, "recipient_number": "+8801712345678", "snippet": "Hey", "unread_count": 0}
    ]

    bridge = MisltyBridge(client=mock_client)

    # 1. calculateSmsSegments
    seg = bridge.calculateSmsSegments("Hello World")
    assert seg["encoding"] == "GSM-7"
    assert seg["segments"] == 1

    # 2. deleteThread
    del_ok = bridge.deleteThread(42)
    assert del_ok is True
    mock_client.delete_sms_thread.assert_called_once_with(42)

    # 3. markAsRead
    read_ok = bridge.markAsRead(42)
    assert read_ok is True
    mock_client.mark_sms_read.assert_called_once_with(42)

    # 4. onSmsReceived hook
    received_events = []
    bridge.smsReceived.connect(lambda sender, body: received_events.append((sender, body)))
    with patch("mislty.gui.app.send_desktop_notification") as mock_notify:
        bridge.onSmsReceived("+8801999999999", "Test incoming text")
        assert len(received_events) == 1
        assert received_events[0] == ("+8801999999999", "Test incoming text")
        mock_notify.assert_called_once()


# ---------------------------------------------------------------------------
# Headless QML Integration Tests
# ---------------------------------------------------------------------------

def test_qml_chat_bubble_instantiation():
    """Verify ChatBubble.qml component instantiates cleanly offscreen with properties."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_NO_GLIB", "1")

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    engine = QQmlEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    bubble_qml = qml_dir / "components" / "ChatBubble.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(bubble_qml)))
    assert not component.isError(), f"ChatBubble QML errors: {component.errors()}"

    obj = component.create()
    assert obj is not None

    # Test incoming bubble
    obj.setProperty("direction", "IN")
    obj.setProperty("body", "Incoming test message from carrier")
    obj.setProperty("timestamp", 1725900000)
    obj.setProperty("status", "RECEIVED")
    assert obj.property("isOutgoing") is False
    assert obj.property("body") == "Incoming test message from carrier"

    # Test outgoing bubble
    obj.setProperty("direction", "OUT")
    obj.setProperty("status", "DELIVERED")
    assert obj.property("isOutgoing") is True
    assert obj.property("isFailed") is False


def test_qml_sms_view_instantiation():
    """Verify SmsView.qml instantiates cleanly offscreen and binds to bridge."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_NO_GLIB", "1")

    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])

    engine = QQmlEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    mock_client = MagicMock()
    mock_client.active_transport = "direct"
    mock_client.list_sms.return_value = [
        {
            "id": 10,
            "recipient_number": "+8801811111111",
            "contact_name": "Bob",
            "snippet": "Hello Bob",
            "unread_count": 2,
            "updated_at": 1725900000,
        }
    ]

    bridge = MisltyBridge(client=mock_client)
    engine.rootContext().setContextProperty("bridge", bridge)

    sms_qml = qml_dir / "views" / "SmsView.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(sms_qml)))
    assert not component.isError(), f"SmsView QML errors: {component.errors()}"

    obj = component.create()
    assert obj is not None
    assert obj.property("activeThreadId") == -1

    # Verify search query filter function in QML
    threads_js = obj.getFilteredThreads()
    threads = threads_js.toVariant() if hasattr(threads_js, "toVariant") else threads_js
    assert len(threads) == 1
    assert threads[0]["recipient_number"] == "+8801811111111"

    obj.setProperty("searchQuery", "NonExistent")
    filtered_js = obj.getFilteredThreads()
    filtered = filtered_js.toVariant() if hasattr(filtered_js, "toVariant") else filtered_js
    assert len(filtered) == 0
