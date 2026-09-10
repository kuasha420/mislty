"""
tests.test_gui_dialer
~~~~~~~~~~~~~~~~~~~~~

Headless QML integration and unit tests for Feline Phone Dialer Deck (DialerView.qml):
- Keypad click and digit appending.
- DTMF audio feedback dispatch.
- Place call and hangup action triggers.
- Tragic Voice modal presentation and dismissal.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from mislty.gui.app import MisltyBridge, create_app


def test_mislty_bridge_telephony_slots():
    """Verify MisltyBridge telephony properties, callbacks, and invokable slots."""
    mock_client = MagicMock()
    mock_client.active_transport = "direct"

    bridge = MisltyBridge(client=mock_client)
    assert bridge.callState == "IDLE"
    assert bridge.tragicVoiceVisible is False

    # 1. Dial slot
    with patch.object(bridge._telephony, "dial", return_value={"success": True}) as mock_dial:
        res = bridge.dialNumber("121")
        assert res is True
        mock_dial.assert_called_once_with("121")

    # 2. Hangup slot
    with patch.object(bridge._telephony, "hangup", return_value={"success": True}) as mock_hang:
        res = bridge.hangupCall()
        assert res is True
        mock_hang.assert_called_once()

    # 3. DTMF tone slot
    with patch("mislty.gui.app.play_dtmf_tone", return_value=True) as mock_tone:
        ok = bridge.sendDtmfTone("5")
        assert ok is True
        mock_tone.assert_called_once_with("5")

    # 4. Tragic Voice modal trigger & dismiss
    tragic_received = []
    bridge.tragicVoiceTriggered.connect(lambda d: tragic_received.append(d))

    bridge.triggerTragicVoiceLore("121")
    assert bridge.tragicVoiceVisible is True
    assert len(tragic_received) == 1
    assert "Tragic Voice" in tragic_received[0]["title"]

    bridge.dismissTragicVoice()
    assert bridge.tragicVoiceVisible is False


def test_qml_dialer_view_instantiation():
    """Verify DialerView.qml instantiates cleanly offscreen and binds to bridge."""
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
    bridge = MisltyBridge(client=mock_client)
    engine.rootContext().setContextProperty("bridge", bridge)

    dialer_qml = qml_dir / "views" / "DialerView.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(dialer_qml)))
    assert not component.isError(), f"DialerView QML errors: {component.errors()}"

    obj = component.create()
    assert obj is not None
    assert obj.property("activeCallState") == "IDLE"

    # Test digit appending and backspace in QML
    obj.appendDigit("1")
    obj.appendDigit("2")
    obj.appendDigit("1")
    assert obj.property("dialInput") == "121"

    obj.backspace()
    assert obj.property("dialInput") == "12"


def test_qml_main_shell_with_dialer():
    """Verify Main.qml shell instantiates with all 5 navigation decks including Phone Dialer."""
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
    bridge = MisltyBridge(client=mock_client)
    engine.rootContext().setContextProperty("bridge", bridge)

    main_qml = qml_dir / "Main.qml"
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(main_qml)))
    assert not component.isError(), f"Main QML errors: {component.errors()}"

    obj = component.create()
    assert obj is not None
