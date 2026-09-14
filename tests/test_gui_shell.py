"""
tests.test_gui_shell
~~~~~~~~~~~~~~~~~~~~

Unit tests for PySide6 application host, MisltyBridge, Theme tokens,
and QML application shell components under headless offscreen mode.
"""

import os
from pathlib import Path
import time
import pytest

# Ensure headless Qt offscreen platform
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QObject, Signal, Slot, Property, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from mislty.gui.app import MisltyBridge, create_app


@pytest.fixture(scope="session")
def qapp():
    """Session-wide QGuiApplication fixture."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


@pytest.fixture
def mock_client():
    """Mock MisltyClient for bridge testing."""
    class MockClient:
        def __init__(self):
            self.active_transport = "socket"
            self.connected = False
            self.wifi_power = True

        def get_status(self):
            return {
                "daemon": {
                    "is_running": True,
                    "connected": True,
                    "rssi": 22,
                    "bars": 4,
                    "dbm": -69,
                    "carrier": "Grameenphone",
                    "technology": "4G LTE",
                },
                "cellular_ppp": {
                    "is_connected": self.connected,
                    "ip_address": "10.64.12.34" if self.connected else None,
                    "rx_bytes": 1048576,
                    "tx_bytes": 524288,
                },
                "wifi": {
                    "power": self.wifi_power,
                    "ssid": "TypeScript 420",
                    "clients_count": 2,
                },
            }

        def connect(self, apn="internet", default_route=True, timeout=20.0):
            self.connected = True
            return {"success": True}

        def disconnect(self):
            self.connected = False
            return {"success": True}

        def set_wifi_power(self, enable: bool):
            self.wifi_power = enable
            return {"success": True, "power": enable}

        def set_wifi_credentials(self, ssid: str, password: str):
            return {"success": True, "ssid": ssid}

        def execute_at(self, command: str, timeout=3.0):
            return {"success": True, "command": command, "lines": ["+CSQ: 22,99"]}

        def send_sms(self, recipient: str, text: str):
            return {"success": True, "recipient": recipient, "message_id": 1}

        def list_sms(self, thread_id=None):
            if thread_id is not None:
                return [{"id": 1, "phone_number": "+8801700000000", "body": "Hello", "direction": "IN"}]
            return [{"id": 1, "phone_number": "+8801700000000", "last_message": "Hello", "updated_at": "2026-09-10 03:00:00"}]

        def sync_sms(self, purge_sim=True):
            return [{"id": 1, "phone_number": "+8801700000000", "body": "Synced msg"}]

    return MockClient()


def test_theme_qml_tokens(qapp):
    """Verify Theme.qml visual tokens and helper functions."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    comp = QQmlComponent(engine, str(qml_dir / "Theme.qml"))
    assert not comp.isError(), f"Theme.qml error: {[e.toString() for e in comp.errors()]}"
    theme = comp.create()
    assert theme is not None

    # Check Color Tokens
    assert theme.property("colorVoid").name().lower() == "#0c0e14"
    assert theme.property("colorObsidian").name().lower() == "#141721"
    assert theme.property("colorCyan").name().lower() == "#00f0ff"
    assert theme.property("colorGold").name().lower() == "#f39c12"
    assert theme.property("colorSuccess").name().lower() == "#00e676"

    # Check Helper Functions
    assert theme.formatBytes(500) == "500 B"
    assert theme.formatBytes(2048) == "2.0 KB"
    assert "MB" in theme.formatBytes(10485760)

    assert theme.csqToBars(25) == 5
    assert theme.csqToBars(18) == 4
    assert theme.csqToBars(13) == 3
    assert theme.csqToBars(8) == 2
    assert theme.csqToBars(3) == 1
    assert theme.csqToBars(99) == 0

    assert theme.csqToDbm(22) == "-69 dBm"
    assert theme.durationString(3665) == "01:01:05"


def test_reusable_components_load(qapp):
    """Verify reusable components (Card, StatusPill, SignalBars, FelineButton) instantiate cleanly."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    for name in ["Card.qml", "StatusPill.qml", "SignalBars.qml", "FelineButton.qml"]:
        comp_path = qml_dir / "components" / name
        comp = QQmlComponent(engine, str(comp_path))
        assert not comp.isError(), f"Component {name} error: {[e.toString() for e in comp.errors()]}"
        obj = comp.create()
        assert obj is not None


def test_mislty_bridge_properties_and_signals(qapp, mock_client):
    """Verify MisltyBridge properties, signal emissions, and state ingestion."""
    bridge = MisltyBridge(client=mock_client)

    # Verify initial status was ingested from mock
    assert bridge.isDaemonRunning is True
    assert bridge.operator == "Grameenphone"
    assert bridge.technology == "4G LTE"
    assert bridge.signalBars == 4
    assert bridge.signalCsq == 22
    assert bridge.signalDbm == -69
    assert bridge.wifiPower is True
    assert bridge.wifiSsid == "TypeScript 420"
    assert bridge.wifiClientsCount == 2
    assert bridge.transportMode == "socket"

    # Verify property mutation and signal emissions
    deck_changed = []
    bridge.activeDeckChanged.connect(lambda d: deck_changed.append(d))
    bridge.setActiveDeck(2)
    assert bridge.activeDeck == 2
    assert deck_changed == [2]

    # Test Wi-Fi toggle
    res = bridge.toggleWifi()
    assert res is False
    time.sleep(0.05)
    assert bridge.wifiPower is False

    # Test AT execution
    at_out = bridge.executeAt("AT+CSQ")
    assert "+CSQ: 22,99" in at_out
    assert "OK" in at_out

    # Test SMS operations
    threads = bridge.getSmsThreads()
    assert len(threads) == 1
    assert threads[0]["phone_number"] == "+8801700000000"

    msgs = bridge.getSmsMessages(1)
    assert len(msgs) == 1
    assert msgs[0]["body"] == "Hello"

    sent = bridge.sendSms("+8801700000000", "Test message")
    assert sent is True


def test_create_app_shell_load(qapp, mock_client):
    """Verify create_app instantiates QQmlApplicationEngine and loads Main.qml without errors."""
    app, engine, bridge = create_app(client=mock_client)
    assert app is not None
    assert engine is not None
    assert bridge is not None

    root_objs = engine.rootObjects()
    assert len(root_objs) == 1
    root = root_objs[0]
    assert root.property("title") == "MisLTy — Qualcomm MDM9600 Suite"

    # Check deck switching
    bridge.setActiveDeck(1)
    assert bridge.activeDeck == 1
    bridge.setActiveDeck(3)
    assert bridge.activeDeck == 3


def test_hardware_unplugged_state(qapp):
    """Verify GUI reflects unplugged modem state across bridge properties, guards, and QML decks."""
    class MockUnpluggedClient:
        def __init__(self):
            self.active_transport = "direct"

        def get_status(self):
            return {
                "daemon": {
                    "is_running": False,
                    "connected": False,
                },
                "hardware": {
                    "is_present": False,
                    "is_ready": False,
                    "is_zerocd": False,
                    "ports": {},
                },
                "cellular_ppp": {
                    "is_connected": False,
                },
                "wifi": {
                    "power": False,
                },
            }

        def connect(self, **kwargs):
            return {"success": False, "error": "Modem hardware is not connected"}

        def disconnect(self):
            return {"success": True}

        def execute_at(self, *args, **kwargs):
            return {"success": False, "error": "Modem hardware is not connected"}

        def send_sms(self, *args, **kwargs):
            return {"success": False, "error": "Modem hardware is not connected"}

        def list_sms(self, *args, **kwargs):
            return []

        def sync_sms(self, *args, **kwargs):
            return []

        def list_wlan_devices(self):
            return []

        def get_hotspot_relay_status(self):
            return {"active": False}

    unplugged_client = MockUnpluggedClient()
    bridge = MisltyBridge(client=unplugged_client)

    # Assert hardware-aware reactive properties
    assert bridge.modemPresent is False
    assert bridge.modemReady is False
    assert bridge.isZeroCd is False
    assert bridge.hardwareStateText == "DISCONNECTED"
    assert bridge.operator == "No Modem Detected"
    assert bridge.technology == "OFFLINE"
    assert bridge.signalBars == 0
    assert bridge.signalCsq == 0
    assert bridge.signalDbm == -113

    # Test hardware guards
    assert bridge.connectData() is False
    assert "disconnected" in bridge.statusMessage.lower() or "not connected" in bridge.statusMessage.lower()

    at_res = bridge.executeAt("AT")
    assert "ERROR" in at_res
    assert "disconnected" in at_res.lower()

    assert bridge.sendSms("+8801700000000", "test") is False
    assert "disconnected" in bridge.statusMessage.lower() or "not connected" in bridge.statusMessage.lower()

    # Verify create_app loads and all 5 decks render without errors in unplugged state
    app, engine, app_bridge = create_app(client=unplugged_client)
    assert app is not None
    assert engine is not None
    assert app_bridge.modemPresent is False

    root_objs = engine.rootObjects()
    assert len(root_objs) == 1

    # Cycle through all decks
    for deck_idx in range(5):
        app_bridge.setActiveDeck(deck_idx)
        assert app_bridge.activeDeck == deck_idx

