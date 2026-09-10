"""
tests.test_gui_wifi
~~~~~~~~~~~~~~~~~~~

Unit tests for MisLTy Wi-Fi deck, station inventory table,
and Smart Mode Switcher QML integration.
"""

import os
from pathlib import Path
import time
import pytest

# Ensure headless Qt offscreen platform
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ["QT_NO_GLIB"] = "1"

from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from mislty.gui.app import MisltyBridge


@pytest.fixture(scope="session")
def qapp():
    """Session-wide QGuiApplication fixture."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


@pytest.fixture
def mock_wifi_client():
    """Mock client returning Wi-Fi softAP telemetry."""
    class MockClient:
        def __init__(self):
            self.active_transport = "socket"
            self.wifi_power = True
            self.ssid = "TypeScript 420"

        def get_status(self):
            return {
                "daemon": {
                    "is_running": True,
                    "connected": True,
                    "rssi": 25,
                    "bars": 4,
                    "dbm": -63,
                    "carrier": "Grameenphone",
                    "technology": "4G LTE",
                },
                "cellular_ppp": {
                    "connected": True,
                    "ip_address": "10.64.120.45",
                    "rx_bytes": 1024,
                    "tx_bytes": 1024,
                },
                "wifi": {
                    "power": self.wifi_power,
                    "ssid": self.ssid,
                    "clients_count": 2,
                },
            }

        def set_wifi_power(self, enable: bool):
            self.wifi_power = enable
            return {"success": True, "power": enable}

        def set_wifi_credentials(self, ssid: str, password: str):
            self.ssid = ssid
            return {"success": True, "ssid": ssid}

        def connect(self, **kwargs): return {"success": True}
        def disconnect(self): return {"success": True}
        def execute_at(self, *args, **kwargs): return {"success": True, "lines": ["OK"]}
        def list_sms(self, *args, **kwargs): return []
        def send_sms(self, *args, **kwargs): return {"success": True}
        def sync_sms(self, *args, **kwargs): return []
        def list_wlan_devices(self):
            return [
                {"iface": "wlan0", "vendor": "Intel", "model": "8265", "is_primary": True, "is_candidate": False},
                {"iface": "wlan1", "vendor": "TP-Link", "model": "Archer T4U", "is_primary": False, "is_candidate": True},
            ]
        def start_hotspot_relay(self, **kwargs):
            return {
                "active": True,
                "interface": kwargs.get("interface", "wlan1"),
                "ssid": kwargs.get("ssid", "MisLTy 4G Share"),
                "ip_address": "10.42.0.1",
                "wan_iface": kwargs.get("wan_iface", "ppp0"),
            }
        def stop_hotspot_relay(self):
            return {"active": False}
        def get_hotspot_relay_status(self):
            return {"active": True, "interface": "wlan1", "ssid": "MisLTy 4G Share", "ip_address": "10.42.0.1", "wan_iface": "ppp0", "uptime_seconds": 42}
        def get_hotspot_relay_clients(self):
            return [{"mac": "AA:BB:CC:DD:EE:FF", "ip": "10.42.0.52", "signal_dbm": -45, "rx_bytes": 1000, "tx_bytes": 2000}]

    return MockClient()


def test_wifi_view_qml_instantiation(qapp, mock_wifi_client):
    """Verify WifiView.qml instantiates and binds to Wi-Fi properties."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    bridge = MisltyBridge(client=mock_wifi_client)
    bridge.wifiStations = [
        {"index": 1, "mac": "D2:6F:5B:13:A8:B5", "hostname": "Host / Aux Client"},
        {"index": 2, "mac": "E4:5F:01:23:45:67", "hostname": "Android Phone"},
    ]
    engine.rootContext().setContextProperty("bridge", bridge)

    comp = QQmlComponent(engine, str(qml_dir / "views" / "WifiView.qml"))
    assert not comp.isError(), f"WifiView.qml errors: {[e.toString() for e in comp.errors()]}"

    view = comp.create(engine.rootContext())
    assert view is not None

    # Verify Properties
    assert bridge.wifiPower is True
    assert bridge.wifiSsid == "TypeScript 420"
    assert len(bridge.wifiStations) == 2
    assert bridge.wifiStations[0]["mac"] == "D2:6F:5B:13:A8:B5"
    assert bridge.operationalMode == "usb_modem"


def test_wifi_deck_actions(qapp, mock_wifi_client):
    """Verify Wi-Fi credentials saving and mode switcher slot executions."""
    from unittest.mock import MagicMock
    mock_qcwebs = MagicMock()
    mock_qcwebs.set_wifi_basic.return_value = True
    mock_qcwebs.set_wifi_security.return_value = True
    mock_qcwebs.set_wan_connect.return_value = True
    mock_qcwebs.get_station_list.return_value = [
        {"index": 1, "mac": "D2:6F:5B:13:A8:B5", "hostname": "Station 1"}
    ]

    bridge = MisltyBridge(client=mock_wifi_client, qcwebs_client=mock_qcwebs)

    # Test saveWifiConfig
    saved = bridge.saveWifiConfig("NewSSID-5G", "Pass12345", 6)
    assert saved is True
    time.sleep(0.05)
    assert bridge.wifiSsid == "NewSSID-5G"
    mock_qcwebs.set_wifi_basic.assert_called_with(ssid="NewSSID-5G", channel=6)
    mock_qcwebs.set_wifi_security.assert_called_with(passphrase="Pass12345")

    # Test getWifiStations
    bridge.getWifiStations()
    time.sleep(0.05)
    assert len(bridge.wifiStations) == 1
    assert bridge.wifiStations[0]["mac"] == "D2:6F:5B:13:A8:B5"

    # Test switchMode to router
    switched = bridge.switchMode("pocket_router")
    assert switched is True
    time.sleep(0.05)
    assert bridge.operationalMode == "pocket_router"

    # Switch back to usb_modem
    switched_usb = bridge.switchMode("usb_modem")
    assert switched_usb is True
    time.sleep(0.05)
    assert bridge.operationalMode == "usb_modem"


def test_wifi_relay_deck_actions_and_properties(qapp, mock_wifi_client):
    """Verify assist Wi-Fi hotspot relay properties and slots in MisltyBridge."""
    bridge = MisltyBridge(client=mock_wifi_client)

    # 1. Device enumeration
    assert bridge.isScanningDevices is False
    bridge.refreshWlanDevices()
    time.sleep(0.05)
    assert bridge.isScanningDevices is False
    assert len(bridge.wlanDevices) == 2
    assert bridge.wlanDevices[0]["iface"] == "wlan0"
    assert bridge.wlanDevices[0]["is_primary"] is True
    assert bridge.wlanDevices[1]["iface"] == "wlan1"
    assert bridge.wlanDevices[1]["is_candidate"] is True

    # 2. Start relay
    assert bridge.relayBusy is False
    assert bridge.relayError == ""
    bridge.startHotspotRelay("wlan1", "MisLTy 4G Share", "mislty420", "bg", 11, "ppp0")
    time.sleep(0.05)
    assert bridge.relayBusy is False
    assert bridge.relayActive is True
    assert bridge.relayInterface == "wlan1"
    assert bridge.relaySsid == "MisLTy 4G Share"
    assert bridge.relayIpAddress == "10.42.0.1"
    assert bridge.relayError == ""

    # 3. Query relay clients
    bridge.getHotspotRelayClients()
    time.sleep(0.05)
    assert len(bridge.relayClients) == 1
    assert bridge.relayClients[0]["mac"] == "AA:BB:CC:DD:EE:FF"
    assert bridge.relayClients[0]["ip"] == "10.42.0.52"

    # 4. Stop relay
    bridge.stopHotspotRelay()
    time.sleep(0.05)
    assert bridge.relayBusy is False
    assert bridge.relayActive is False
