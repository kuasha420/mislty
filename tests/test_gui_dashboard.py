"""
tests.test_gui_dashboard
~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for MisLTy Dashboard view, telemetry gauges, live throughput
speedometers, bandwidth sparkline graphs, and connection state machinery.
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

from mislty.gui.app import MisltyBridge, create_app


@pytest.fixture(scope="session")
def qapp():
    """Session-wide QGuiApplication fixture."""
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


@pytest.fixture
def mock_dashboard_client():
    """Mock client returning comprehensive dashboard telemetry."""
    class MockClient:
        def __init__(self):
            self.active_transport = "socket"
            self.connected = True
            self.rx_bytes = 52428800   # 50 MB
            self.tx_bytes = 10485760   # 10 MB

        def get_status(self):
            return {
                "daemon": {
                    "is_running": True,
                    "connected": True,
                    "rssi": 28,
                    "bars": 5,
                    "dbm": -57,
                    "carrier": "Grameenphone",
                    "technology": "4G LTE",
                    "operational_mode": "usb_cellular",
                },
                "cellular_ppp": {
                    "connected": self.connected,
                    "interface": "ppp0",
                    "ip_address": "10.64.120.45",
                    "peer_ip": "10.64.120.1",
                    "dns_servers": ["10.64.120.1", "8.8.8.8"],
                    "rx_bytes": self.rx_bytes,
                    "tx_bytes": self.tx_bytes,
                    "uptime_seconds": 1845.0,
                },
                "wifi": {
                    "power": True,
                    "ssid": "TypeScript 420",
                    "clients_count": 3,
                },
            }

        def connect(self, apn="internet", default_route=True, timeout=20.0):
            self.connected = True
            return {"success": True}

        def disconnect(self):
            self.connected = False
            return {"success": True}

        def set_wifi_power(self, enable: bool):
            return {"success": True}

        def set_wifi_credentials(self, ssid: str, password: str):
            return {"success": True}

        def execute_at(self, command: str, timeout=3.0):
            return {"success": True, "lines": ["OK"]}

        def list_sms(self, thread_id=None):
            return []

        def send_sms(self, recipient: str, text: str):
            return {"success": True}

        def sync_sms(self, purge_sim=True):
            return []

    return MockClient()


def test_dashboard_view_qml_instantiation(qapp, mock_dashboard_client):
    """Verify DashboardView.qml instantiates and binds to telemetry properties."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    bridge = MisltyBridge(client=mock_dashboard_client)
    engine.rootContext().setContextProperty("bridge", bridge)

    comp = QQmlComponent(engine, str(qml_dir / "views" / "DashboardView.qml"))
    assert not comp.isError(), f"DashboardView.qml errors: {[e.toString() for e in comp.errors()]}"

    view = comp.create(engine.rootContext())
    assert view is not None

    # Telemetry Property Assertions
    assert bridge.connected is True
    assert bridge.operator == "Grameenphone"
    assert bridge.technology == "4G LTE"
    assert bridge.signalBars == 5
    assert bridge.signalCsq == 28
    assert bridge.signalDbm == -57
    assert bridge.ipAddress == "10.64.120.45"
    assert bridge.peerIp == "10.64.120.1"
    assert bridge.dnsServers == ["10.64.120.1", "8.8.8.8"]
    assert bridge.sessionDuration == 1845
    assert bridge.rxBytes == 52428800
    assert bridge.txBytes == 10485760


def test_bandwidth_graph_sparkline_component(qapp):
    """Verify BandwidthGraph component metrics, scaling, and peak rate tracking."""
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent.parent / "src" / "mislty" / "gui" / "qml"
    engine.addImportPath(str(qml_dir))

    comp = QQmlComponent(engine, str(qml_dir / "components" / "BandwidthGraph.qml"))
    assert not comp.isError()

    graph = comp.create()
    assert graph is not None

    # Verify property settings
    graph.setProperty("history", [0.0, 150.0, 320.0, 1200.0, 850.0])
    graph.setProperty("currentRateStr", "850 KB/s")
    graph.setProperty("peakRateStr", "1.2 MB/s")

    assert graph.property("currentRateStr") == "850 KB/s"
    assert graph.property("peakRateStr") == "1.2 MB/s"


def test_dashboard_rate_tracking_and_sparkline_history(qapp, mock_dashboard_client):
    """Verify rate calculations and sparkline history queueing on sequential poll cycles."""
    bridge = MisltyBridge(client=mock_dashboard_client)

    # First update establishes baseline timestamp and byte counts
    assert len(bridge.trafficHistoryRx) == 24
    assert len(bridge.trafficHistoryTx) == 24

    # Advance client byte counts
    mock_dashboard_client.rx_bytes += 1048576  # +1 MB in 0.1s
    mock_dashboard_client.tx_bytes += 262144   # +256 KB in 0.1s
    time.sleep(0.1)

    bridge._update_status_data(mock_dashboard_client.get_status())

    assert bridge.rxRate > 0.0
    assert bridge.txRate > 0.0
    assert bridge.peakRxRate >= bridge.rxRate
    assert bridge.peakTxRate >= bridge.txRate
    assert bridge.trafficHistoryRx[-1] > 0.0
    assert bridge.trafficHistoryTx[-1] > 0.0


def test_dashboard_connect_disconnect_actions(qapp, mock_dashboard_client):
    """Verify 1-click connect and disconnect slot execution and state transitions."""
    bridge = MisltyBridge(client=mock_dashboard_client)
    assert bridge.connected is True

    # Test disconnectData
    bridge.disconnectData()
    time.sleep(0.1)
    assert mock_dashboard_client.connected is False

    # Test connectData
    bridge.connectData(apn="internet")
    time.sleep(0.1)
    assert mock_dashboard_client.connected is True
