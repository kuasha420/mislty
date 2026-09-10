"""
tests.test_tray
~~~~~~~~~~~~~~~

Unit tests for MisltyTray system tray controller:
- Dynamic feline 5-bar signal icon generation across all signal states.
- Tray context menu actions (Connect/Disconnect, Mode Switch, Web UI, Window toggle).
- Inbound SMS balloon notification dispatch.
- Window minimize/restore behavior.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication

from mislty.gui.tray import MisltyTray, create_feline_signal_icon


@pytest.fixture(scope="module")
def qapp():
    """Ensure QApplication instance is available for QSystemTrayIcon tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_NO_GLIB", "1")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_create_feline_signal_icon(qapp):
    """Verify dynamic feline signal icon generation for all signal bar states."""
    for bars in range(6):  # 0 to 5 bars
        for connected in (True, False):
            icon = create_feline_signal_icon(bars=bars, connected=connected, size=32)
            assert isinstance(icon, QIcon)
            assert not icon.isNull()
            pixmap = icon.pixmap(32, 32)
            assert not pixmap.isNull()
            assert pixmap.width() == 32
            assert pixmap.height() == 32


def test_mislty_tray_initialization_and_menu(qapp):
    """Verify MisltyTray initializes with all context actions and updates text on state changes."""
    mock_bridge = MagicMock()
    mock_bridge.signalBars = 4
    mock_bridge.connected = False
    mock_bridge.operator = "Grameenphone"
    mock_bridge.technology = "4G LTE"
    mock_bridge.operationalMode = "usb_modem"

    # Mock signals
    mock_bridge.connectedChanged = MagicMock()
    mock_bridge.signalBarsChanged = MagicMock()
    mock_bridge.operatorChanged = MagicMock()
    mock_bridge.technologyChanged = MagicMock()
    mock_bridge.operationalModeChanged = MagicMock()
    mock_bridge.smsReceived = MagicMock()

    tray = MisltyTray(bridge=mock_bridge, app=qapp)
    assert tray._tray_icon is not None

    # Verify context menu actions
    actions = [a.text() for a in tray._menu.actions() if not a.isSeparator()]
    assert any("Ready: Grameenphone" in a for a in actions)
    assert any("Connect Cellular Data" in a for a in actions)
    assert any("Switch to Pocket Router" in a for a in actions)
    assert any("Open Web Management UI" in a for a in actions)
    assert any("Show MisLTy" in a for a in actions)
    assert any("Quit MisLTy" in a for a in actions)

    # State update: connected
    mock_bridge.connected = True
    tray.update_icon()
    assert "Disconnect Cellular Data" in tray._connect_action.text()
    assert "Connected: Grameenphone" in tray._status_action.text()


def test_mislty_tray_action_triggers(qapp):
    """Verify tray menu actions trigger corresponding bridge operations."""
    mock_bridge = MagicMock()
    mock_bridge.connected = False
    mock_bridge.signalBars = 3
    mock_bridge.operator = "Banglalink"
    mock_bridge.technology = "4G LTE"

    mock_bridge.connectedChanged = MagicMock()
    mock_bridge.signalBarsChanged = MagicMock()
    mock_bridge.operatorChanged = MagicMock()
    mock_bridge.technologyChanged = MagicMock()
    mock_bridge.operationalModeChanged = MagicMock()
    mock_bridge.smsReceived = MagicMock()

    tray = MisltyTray(bridge=mock_bridge, app=qapp)

    # 1. Connect trigger
    tray._on_toggle_connect()
    mock_bridge.connectData.assert_called_once()

    # 2. Mode switch trigger
    tray._on_toggle_mode()
    mock_bridge.switchOperationalMode.assert_called_once()

    # 3. Web UI trigger
    tray._on_open_webui()
    mock_bridge.launchWebUi.assert_called_once()


def test_mislty_tray_window_toggle(qapp):
    """Verify toggle_window alternates visibility state."""
    mock_bridge = MagicMock()
    mock_bridge.signalBars = 0
    mock_bridge.connected = False
    mock_bridge.operator = ""
    mock_bridge.technology = ""

    mock_bridge.connectedChanged = MagicMock()
    mock_bridge.signalBarsChanged = MagicMock()
    mock_bridge.operatorChanged = MagicMock()
    mock_bridge.technologyChanged = MagicMock()
    mock_bridge.operationalModeChanged = MagicMock()
    mock_bridge.smsReceived = MagicMock()

    mock_window = MagicMock()
    mock_window.isVisible.return_value = False

    tray = MisltyTray(bridge=mock_bridge, app=qapp, window=mock_window)

    # Hidden -> Show
    tray.toggle_window()
    mock_window.show.assert_called_once()
    mock_window.raise_.assert_called_once()
    mock_window.requestActivate.assert_called_once()

    # Visible -> Hide
    mock_window.isVisible.return_value = True
    tray.toggle_window()
    mock_window.hide.assert_called_once()


def test_mislty_tray_sms_balloon_notification(qapp):
    """Verify inbound SMS triggers tray balloon message."""
    mock_bridge = MagicMock()
    mock_bridge.signalBars = 0
    mock_bridge.connected = False
    mock_bridge.operator = ""
    mock_bridge.technology = ""

    mock_bridge.connectedChanged = MagicMock()
    mock_bridge.signalBarsChanged = MagicMock()
    mock_bridge.operatorChanged = MagicMock()
    mock_bridge.technologyChanged = MagicMock()
    mock_bridge.operationalModeChanged = MagicMock()
    mock_bridge.smsReceived = MagicMock()

    tray = MisltyTray(bridge=mock_bridge, app=qapp)

    with patch.object(tray._tray_icon, "showMessage") as mock_show:
        tray._on_sms_received("+8801700000000", "Hello from cellular test")
        mock_show.assert_called_once()
        args = mock_show.call_args[0]
        assert "+8801700000000" in args[0]
        assert "Hello from cellular test" in args[1]
