"""
Unit tests for MisLTy networking components:
- RouteManager
- DnsManager
- WifiManager
- PppController
"""

from io import BytesIO
from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from mislty.core.at_parser import AtResponse
from mislty.net.dns_manager import DnsManager
from mislty.net.helper_client import NetworkHelperClient
from mislty.net.ppp_controller import PppController, PppStatus
from mislty.net.route_manager import RouteEntry, RouteManager
from mislty.net.wifi_manager import WifiManager


# ---------------------------------------------------------------------------
# RouteManager Tests
# ---------------------------------------------------------------------------

def test_route_manager_parse_default_routes():
    """Verify parsing of 'ip route show default' output."""
    sample_ip_route = (
        "default via 192.168.1.1 dev wlan0 proto dhcp src 192.168.1.105 metric 600\n"
        "default via 10.64.0.1 dev ppp0 metric 50\n"
    )
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["ip", "route", "show", "default"],
        returncode=0,
        stdout=sample_ip_route,
        stderr="",
    ))

    with patch("subprocess.run", mock_run):
        mgr = RouteManager(helper=MagicMock())
        routes = mgr.get_default_routes()

    assert len(routes) == 2
    assert routes[0].gateway == "192.168.1.1"
    assert routes[0].dev == "wlan0"
    assert routes[0].metric == 600
    assert routes[0].proto == "dhcp"
    assert routes[0].src == "192.168.1.105"

    assert routes[1].gateway == "10.64.0.1"
    assert routes[1].dev == "ppp0"
    assert routes[1].metric == 50


def test_route_manager_snapshot_and_restore():
    """Verify non-destructive snapshot and restoration of original routes."""
    mock_helper = MagicMock(spec=NetworkHelperClient)
    mock_helper.set_default_route.return_value = True
    mock_helper.restore_default_route.return_value = True

    mgr = RouteManager(helper=mock_helper)
    saved_route = RouteEntry(gateway="192.168.1.1", dev="wlan0", metric=600)

    with patch.object(mgr, "get_default_routes", return_value=[saved_route]):
        mgr.snapshot()
        assert len(mgr._saved_default_routes) == 1
        assert mgr._saved_default_routes[0].dev == "wlan0"

        # Apply cellular default
        assert mgr.set_cellular_default("ppp0", metric=50) is True
        mock_helper.set_default_route.assert_called_once_with("ppp0", metric=50)

        # Restore original route
        assert mgr.restore_routes() is True
        mock_helper.restore_default_route.assert_called_once_with("192.168.1.1", "wlan0", metric=600)
        assert len(mgr._saved_default_routes) == 0


# ---------------------------------------------------------------------------
# DnsManager Tests
# ---------------------------------------------------------------------------

def test_dns_manager_get_peer_dns(tmp_path, monkeypatch):
    """Verify extraction of carrier nameservers from resolv.conf."""
    fake_resolv = tmp_path / "resolv.conf"
    fake_resolv.write_text("nameserver 10.11.12.13\nnameserver 10.11.12.14\n# comment\n")

    monkeypatch.setattr("mislty.net.dns_manager.PPP_RESOLV_CONF", fake_resolv)

    dns_mgr = DnsManager()
    servers = dns_mgr.get_peer_dns()
    assert servers == ["10.11.12.13", "10.11.12.14"]


def test_dns_manager_resolved_interaction():
    """Verify invocation of resolvectl for DNS configuration."""
    dns_mgr = DnsManager()
    dns_mgr._using_resolved = True

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(args=[], returncode=0))
    with patch("subprocess.run", mock_run):
        ok = dns_mgr.apply_cellular_dns("ppp0", ["1.1.1.1", "8.8.8.8"])
        assert ok is True
        assert mock_run.call_count == 2
        mock_run.assert_any_call(["resolvectl", "dns", "ppp0", "1.1.1.1", "8.8.8.8"], check=True, capture_output=True, timeout=3.0)
        mock_run.assert_any_call(["resolvectl", "domain", "ppp0", "~."], check=True, capture_output=True, timeout=3.0)

        mock_run.reset_mock()
        dns_mgr.restore_dns("ppp0")
        mock_run.assert_called_once_with(["resolvectl", "revert", "ppp0"], capture_output=True, timeout=3.0)


# ---------------------------------------------------------------------------
# WifiManager Tests
# ---------------------------------------------------------------------------

def test_wifi_manager_radio_power():
    """Verify reading and writing Wi-Fi radio power via AT commands."""
    mock_dispatcher = MagicMock()
    mock_dispatcher.execute.side_effect = [
        AtResponse(command="AT+WIFI?", success=True, lines=["+WIFI: 1"], raw_text="+WIFI: 1\r\nOK"),
        AtResponse(command="AT+WIFI=0", success=True, lines=[], raw_text="OK"),
        AtResponse(command="AT+WRWIFI", success=True, lines=[], raw_text="OK"),
    ]

    wifi = WifiManager(mock_dispatcher)
    assert wifi.get_radio_power() is True
    assert wifi.set_radio_power(False) is True
    mock_dispatcher.execute.assert_any_call("AT+WIFI=0", timeout=3.0)
    mock_dispatcher.execute.assert_any_call("AT+WRWIFI", timeout=3.0)


def test_wifi_manager_set_credentials_serial():
    """Verify configuring SSID and WPA2 passphrase via serial AT commands."""
    mock_dispatcher = MagicMock()
    mock_dispatcher.execute.return_value = AtResponse(command="", success=True, lines=[], raw_text="OK")

    wifi = WifiManager(mock_dispatcher)
    assert wifi.set_credentials_serial("MyHotspot", "SecretPass123") is True
    mock_dispatcher.execute.assert_any_call('AT^SSID="MyHotspot"', timeout=3.0)
    mock_dispatcher.execute.assert_any_call('AT+WIFIWPAPSK="SecretPass123"', timeout=3.0)
    mock_dispatcher.execute.assert_any_call("AT+WRWIFI", timeout=3.0)


def test_wifi_manager_clean_ssid_web():
    """Verify clean SSID configuration via embedded QC-Webs GoForm API."""
    mock_dispatcher = MagicMock()
    mock_dispatcher.execute.return_value = AtResponse(command="AT+WRWIFI", success=True, lines=[], raw_text="OK")
    wifi = WifiManager(mock_dispatcher)

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ok = wifi.set_clean_ssid_web("Clean_SSID_NoSuffix")
        assert ok is True
        mock_dispatcher.execute.assert_called_once_with("AT+WRWIFI", timeout=3.0)


def test_wifi_manager_dhcp_client_table_parsing():
    """Verify parsing of connected client devices from dhcp_tbl.asp HTML."""
    sample_html = """
    <html>
    <body>
      <table border="1">
        <tr><th>Hostname</th><th>IP Address</th><th>MAC Address</th><th>Expiry</th></tr>
        <tr><td>iPhone-User</td><td>192.168.100.101</td><td>aa:bb:cc:dd:ee:ff</td><td>86400</td></tr>
        <tr><td>Android-Tab</td><td>192.168.100.102</td><td>11:22:33:44:55:66</td><td>43200</td></tr>
      </table>
    </body>
    </html>
    """
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = sample_html.encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    wifi = WifiManager()
    with patch("urllib.request.urlopen", return_value=mock_resp):
        clients = wifi.get_connected_clients()

    assert len(clients) == 2
    assert clients[0] == {"hostname": "iPhone-User", "ip": "192.168.100.101", "mac": "aa:bb:cc:dd:ee:ff"}
    assert clients[1] == {"hostname": "Android-Tab", "ip": "192.168.100.102", "mac": "11:22:33:44:55:66"}


# ---------------------------------------------------------------------------
# PppController Tests
# ---------------------------------------------------------------------------

def test_ppp_status_dataclass():
    """Verify PppStatus serialization and formatting."""
    stat = PppStatus(
        connected=True,
        interface="ppp0",
        ip_address="10.64.12.34",
        peer_ip="10.64.12.1",
        dns_servers=["1.1.1.1", "8.8.8.8"],
        rx_bytes=1048576,
        tx_bytes=524288,
    )
    d = stat.as_dict()
    assert d["connected"] is True
    assert d["interface"] == "ppp0"
    assert d["ip_address"] == "10.64.12.34"
    assert "10.64.12.34" in str(stat)


def test_ppp_controller_connect_and_disconnect(tmp_path):
    """Verify PppController orchestrating helper, route manager, and DNS manager."""
    mock_helper = MagicMock(spec=NetworkHelperClient)
    mock_helper.start_ppp.return_value = {"success": True, "pid": 12345}
    mock_helper.stop_ppp.return_value = {"success": True, "killed": True}

    mock_route = MagicMock(spec=RouteManager)
    mock_dns = MagicMock(spec=DnsManager)
    mock_dns.get_peer_dns.return_value = ["1.1.1.1"]

    dummy_port = tmp_path / "ttyData"
    dummy_port.touch()

    ctrl = PppController(
        data_port=dummy_port,
        helper=mock_helper,
        route_mgr=mock_route,
        dns_mgr=mock_dns,
    )

    # Mock get_status to return disconnected initially, then connected
    ctrl.get_status = MagicMock(side_effect=[
        PppStatus(connected=False),
        PppStatus(connected=True, interface="ppp0", ip_address="10.20.30.40"),
        PppStatus(connected=True, interface="ppp0", ip_address="10.20.30.40"),
    ])

    ok = ctrl.connect(apn="internet", default_route=True, timeout=2.0)
    assert ok is True
    mock_route.snapshot.assert_called_once()
    mock_helper.start_ppp.assert_called_once_with(str(dummy_port), apn="internet")
    mock_route.set_cellular_default.assert_called_once_with("ppp0", metric=50)
    mock_dns.apply_cellular_dns.assert_called_once_with("ppp0")

    # Disconnect
    ctrl.disconnect()
    mock_helper.stop_ppp.assert_called_once()
    mock_dns.restore_dns.assert_called_once_with("ppp0")
    mock_route.restore_routes.assert_called_once()
