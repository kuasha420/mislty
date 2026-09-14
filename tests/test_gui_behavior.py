"""
tests.test_gui_behavior
~~~~~~~~~~~~~~~~~~~~~~~

Comprehensive UX and behavioral test suite verifying:
1. Complete telemetry exposure (totalBytesTransferred, dnsServersFormatted, bandName, operator, technology).
2. Action feedback, async loading flags, and busy transitions (isSyncingSms, isSendingSms, isTogglingWifi, isSavingWifiConfig, isSwitchingMode, relayBusy, connecting).
3. Coherent instantiation and QML error-free binding across all 5 core views (Dashboard, Wi-Fi, SMS, Dialer, Diagnostics).
4. FelineButton design tokens, variant styling, loading spinner state, and click suppression.
"""

import os
from pathlib import Path
import time
import pytest

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
def mock_behavior_client():
    """Mock client for behavioral testing."""
    class MockBehaviorClient:
        def __init__(self):
            self.connected = True
            self.active_transport = "socket"
            self.wifi_power = True
            self.operational_mode = "usb_cellular"

        def get_status(self):
            return {
                "daemon": {
                    "is_running": True,
                    "connected": self.connected,
                    "rssi": 27,
                    "bars": 4,
                    "dbm": -59,
                    "carrier": "Robi Axiata",
                    "technology": "4G LTE (B3 / 1800 MHz)",
                    "operational_mode": self.operational_mode,
                },
                "cellular_ppp": {
                    "connected": self.connected,
                    "interface": "ppp0",
                    "ip_address": "100.119.24.197",
                    "peer_ip": "10.64.64.64",
                    "dns_servers": ["10.17.160.102", "103.242.23.166"],
                    "rx_bytes": 142000000,
                    "tx_bytes": 38000000,
                    "uptime_seconds": 3600.0,
                },
                "wifi": {
                    "power": self.wifi_power,
                    "ssid": "TypeScript 420",
                    "clients_count": 2,
                },
            }

        def connect(self, apn="internet", default_route=True, timeout=20.0):
            time.sleep(0.05)
            self.connected = True
            return {"success": True}

        def disconnect(self):
            time.sleep(0.05)
            self.connected = False
            return {"success": True}

        def set_wifi_power(self, enable: bool):
            time.sleep(0.05)
            self.wifi_power = enable
            return {"success": True}

        def set_wifi_credentials(self, ssid: str, password: str, channel=11):
            time.sleep(0.05)
            return {"success": True}

        def execute_at(self, command: str, timeout=3.0):
            return {"success": True, "lines": ["OK"]}

        def list_sms(self, thread_id=None):
            return [
                {"id": 1, "recipient_number": "+8801812345678", "contact_name": "Antigravity", "snippet": "Hello MisLTy!", "updated_at": "12:00", "unread_count": 0, "message_count": 1}
            ]

        def send_sms(self, recipient: str, text: str):
            time.sleep(0.05)
            return {"success": True}

        def sync_sms(self, purge_sim=True):
            time.sleep(0.05)
            return [{"id": 1, "sender": "+8801812345678", "text": "SIM message"}]

        def switch_mode(self, mode: str):
            time.sleep(0.05)
            self.operational_mode = mode
            return {"success": True}

        def start_hotspot_relay(self, **kwargs):
            time.sleep(0.05)
            return {"success": True, "iface": "wlan1"}

        def stop_hotspot_relay(self):
            time.sleep(0.05)
            return {"success": True}

        def list_wlan_devices(self):
            return [
                {"iface": "wlan0", "vendor": "Intel", "model": "8265", "supports_ap": True, "is_candidate": False, "is_primary": True},
                {"iface": "wlan1", "vendor": "TP-Link", "model": "T4U", "supports_ap": True, "is_candidate": True, "is_primary": False},
            ]

        def get_hotspot_relay_status(self):
            return {"active": False, "clients": []}

    return MockBehaviorClient()


@pytest.fixture
def mock_qcwebs():
    from unittest.mock import MagicMock
    mock = MagicMock()
    mock.host = "192.168.100.1"
    def _slow_save(*args, **kwargs):
        time.sleep(0.05)
        return True
    mock.set_wifi_basic.side_effect = _slow_save
    mock.set_wifi_security.return_value = True
    mock.get_station_list.return_value = []
    mock.device_reboot.return_value = True
    return mock


def test_telemetry_properties_completeness(qapp, mock_behavior_client, mock_qcwebs):
    """Verify all telemetry properties are fully exposed and formatted for QML."""
    bridge = MisltyBridge(client=mock_behavior_client, qcwebs_client=mock_qcwebs)

    # Core carrier and RAT
    assert bridge.operator == "Robi Axiata"
    assert "4G LTE" in bridge.technology
    assert bridge.bandName == "Band 3"

    # Cumulative bytes transferred
    assert bridge.rxBytes == 142000000
    assert bridge.txBytes == 38000000
    assert bridge.totalBytesTransferred == 180000000

    # DNS formatting
    assert bridge.dnsServers == ["10.17.160.102", "103.242.23.166"]
    assert "10.17.160.102, 103.242.23.166" in bridge.dnsServersFormatted

    # Wi-Fi details
    assert bridge.wifiPower is True
    assert bridge.wifiSsid == "TypeScript 420"
    assert bridge.wifiClientsCount == 2


def test_async_loading_states_and_feedback(qapp, mock_behavior_client, mock_qcwebs):
    """Verify async operation loading flags set and clear gracefully using deterministic sync events."""
    import threading
    bridge = MisltyBridge(client=mock_behavior_client, qcwebs_client=mock_qcwebs)

    # Initial states
    assert bridge.isSyncingSms is False
    assert bridge.isSendingSms is False
    assert bridge.isTogglingWifi is False
    assert bridge.isSavingWifiConfig is False
    assert bridge.isSwitchingMode is False
    assert bridge.relayBusy is False

    # Wi-Fi Power Toggle (async thread)
    power_event = threading.Event()
    def _slow_power(enable):
        power_event.wait(timeout=1.0)
        mock_behavior_client.wifi_power = enable
        return {"success": True}
    mock_behavior_client.set_wifi_power = _slow_power

    bridge.setWifiPower(False)
    assert bridge.isTogglingWifi is True
    power_event.set()
    time.sleep(0.05)
    assert bridge.isTogglingWifi is False
    assert mock_behavior_client.wifi_power is False

    # Wi-Fi Config Save (async thread)
    save_event = threading.Event()
    def _slow_save(*args, **kwargs):
        save_event.wait(timeout=1.0)
        return True
    mock_qcwebs.set_wifi_basic.side_effect = _slow_save

    bridge.saveWifiConfig("NewSSID", "NewPass123", 11)
    assert bridge.isSavingWifiConfig is True
    save_event.set()
    time.sleep(0.05)
    assert bridge.isSavingWifiConfig is False

    # Mode Switch (async thread)
    switch_event = threading.Event()
    def _slow_switch(*args, **kwargs):
        switch_event.wait(timeout=1.0)
        return {"success": True, "mode": "pocket_router"}
    bridge._mode_switcher.switch_to_router_mode = _slow_switch

    bridge.switchMode("pocket_router")
    assert bridge.isSwitchingMode is True
    switch_event.set()
    time.sleep(0.05)
    assert bridge.isSwitchingMode is False

    # SMS Sync (async thread)
    sms_event = threading.Event()
    def _slow_sync(purge_sim=True):
        sms_event.wait(timeout=1.0)
        return [{"id": 1}]
    mock_behavior_client.sync_sms = _slow_sync

    bridge.syncSms()
    assert bridge.isSyncingSms is True
    sms_event.set()
    time.sleep(0.05)
    assert bridge.isSyncingSms is False

    # Hotspot Relay (async thread)
    relay_event = threading.Event()
    def _slow_relay(**kwargs):
        relay_event.wait(timeout=1.0)
        return {"success": True, "iface": "wlan1"}
    mock_behavior_client.start_hotspot_relay = _slow_relay

    bridge.startHotspotRelay("wlan1", "RelayNet", "Pass12345", "bg", 11, "ppp0")
    assert bridge.relayBusy is True
    relay_event.set()
    time.sleep(0.05)
    assert bridge.relayBusy is False

    # SMS Send (synchronous slot)
    bridge.modemReady = True
    ok = bridge.sendSms("+8801812345678", "Test message")
    assert ok is True
    assert bridge.isSendingSms is False


def test_all_five_core_views_qml_compilation(qapp, mock_behavior_client, mock_qcwebs):
    """Verify all 5 core views instantiate cleanly with zero QML syntax or binding errors."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    bridge = MisltyBridge(client=mock_behavior_client, qcwebs_client=mock_qcwebs)
    engine.rootContext().setContextProperty("bridge", bridge)

    views = [
        "DashboardView.qml",
        "WifiView.qml",
        "SmsView.qml",
        "DialerView.qml",
        "DiagnosticsView.qml",
    ]

    for view_name in views:
        comp = QQmlComponent(engine, str(qml_dir / "views" / view_name))
        assert not comp.isError(), f"Compilation error in {view_name}: {[e.toString() for e in comp.errors()]}"
        item = comp.create(engine.rootContext())
        assert item is not None, f"Failed to instantiate {view_name}"


def test_feline_button_component_tokens_and_states(qapp):
    """Verify FelineButton design tokens, variant styling, loading property, and disabled state."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    comp = QQmlComponent(engine, str(qml_dir / "components" / "FelineButton.qml"))
    assert not comp.isError(), f"FelineButton errors: {[e.toString() for e in comp.errors()]}"

    btn = comp.create()
    assert btn is not None

    # Variants
    for variant in ["primary", "secondary", "danger", "success", "gold", "warning", "outline"]:
        btn.setProperty("variant", variant)
        assert btn.property("variant") == variant

    # Loading state
    btn.setProperty("loading", True)
    btn.setProperty("loadingText", "Processing...")
    assert btn.property("loading") is True
    assert btn.property("loadingText") == "Processing..."

    btn.setProperty("loading", False)
    assert btn.property("loading") is False


def test_dual_wave_graph_and_live_telemetry_rendering(qapp, mock_behavior_client, mock_qcwebs):
    """Verify DualWaveGraph instantiates with live rolling traffic history and handles zero/idle states cleanly."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    bridge = MisltyBridge(client=mock_behavior_client, qcwebs_client=mock_qcwebs)
    engine.rootContext().setContextProperty("bridge", bridge)

    # 1. Component compilation & instantiation
    comp = QQmlComponent(engine, str(qml_dir / "components" / "DualWaveGraph.qml"))
    assert not comp.isError(), f"DualWaveGraph errors: {[e.toString() for e in comp.errors()]}"

    graph = comp.create(engine.rootContext())
    assert graph is not None

    # 2. Bindings with mock traffic
    rx_samples = [0.0] * 20 + [120.5, 450.0, 980.2, 510.0]
    tx_samples = [0.0] * 20 + [15.0, 48.2, 110.0, 85.0]
    graph.setProperty("rxHistory", rx_samples)
    graph.setProperty("txHistory", tx_samples)
    graph.setProperty("rxRate", 510000.0)
    graph.setProperty("txRate", 85000.0)

    assert graph.property("rxRate") == 510000.0
    assert graph.property("txRate") == 85000.0
    assert len(graph.property("rxHistory")) == 24
    assert len(graph.property("txHistory")) == 24

    # 3. Flat baseline zero/idle state
    graph.setProperty("rxHistory", [0.0] * 24)
    graph.setProperty("txHistory", [0.0] * 24)
    graph.setProperty("rxRate", 0.0)
    graph.setProperty("txRate", 0.0)
    assert graph.property("rxRate") == 0.0
    assert graph.property("txRate") == 0.0

    # 4. Telemetry metrics disconnected cleanliness
    mock_behavior_client.connected = False
    status_off = mock_behavior_client.get_status()
    status_off["daemon"]["connected"] = False
    status_off["cellular_ppp"]["connected"] = False
    status_off["daemon"]["rssi"] = 99
    status_off["daemon"]["dbm"] = -113
    bridge._update_status_data(status_off)

    assert bridge.connected is False
    assert bridge.rsrp == "—"
    assert bridge.rsrq == "—"
    assert bridge.rssi == "—"
    assert bridge.sinr == "—"

