"""
tests.test_wifi_relay
~~~~~~~~~~~~~~~~~~~~~

Unit tests for the MisLTy Wi-Fi Hotspot Relay supervisor (Issue #22):
- Device enumeration and primary interface protection
- AP capability detection via iw phy
- NetworkManager softAP provisioning and teardown
- Packet forwarding and table 420 policy routing integration
- Connected station discovery and ARP IP resolution
"""

from pathlib import Path
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from mislty.net.helper_client import NetworkHelperClient
from mislty.net.wifi_relay import RelayClient, RelayStatus, WifiRelayManager, WlanDevice


@pytest.fixture
def mock_helper():
    helper = MagicMock(spec=NetworkHelperClient)
    helper.enable_nat.return_value = True
    helper.disable_nat.return_value = True
    return helper


def test_wlan_device_dataclass():
    dev = WlanDevice(
        iface="wlan1",
        phy="phy4",
        driver="rtw88_8822bu",
        vendor="TP-Link",
        model="Archer T4U",
        mac="00:11:22:33:44:55",
        state="down",
        is_primary=False,
        supports_ap=True,
        is_candidate=True,
    )
    d = dev.as_dict()
    assert d["iface"] == "wlan1"
    assert d["is_candidate"] is True
    assert d["is_primary"] is False


def test_get_primary_interface_ip_route():
    mgr = WifiRelayManager()
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["ip", "route", "show", "default"],
        returncode=0,
        stdout="default via 192.168.1.1 dev wlan0 proto dhcp metric 600\n",
        stderr="",
    ))
    with patch("subprocess.run", mock_run):
        primary = mgr.get_primary_interface()
        assert primary == "wlan0"


def test_get_primary_interface_nmcli_fallback():
    mgr = WifiRelayManager()

    def fake_run(cmd, **kwargs):
        if cmd[0] == "ip":
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="")
        elif cmd[0] == "nmcli":
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout="wlan0:wifi:connected\nwlan1:wifi:disconnected\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        primary = mgr.get_primary_interface()
        assert primary == "wlan0"


def test_list_devices_identifies_candidate_and_protects_primary(tmp_path):
    # Setup fake /sys/class/net directory
    fake_net = tmp_path / "sys_net"
    fake_net.mkdir()

    # wlan0: primary, AP capable
    w0 = fake_net / "wlan0"
    w0.mkdir()
    (w0 / "wireless").mkdir()
    (w0 / "address").write_text("64:79:f0:36:70:ae\n")
    (w0 / "operstate").write_text("up\n")

    # wlan1: secondary dongle, AP capable
    w1 = fake_net / "wlan1"
    w1.mkdir()
    (w1 / "wireless").mkdir()
    (w1 / "address").write_text("a6:7a:40:5f:c3:13\n")
    (w1 / "operstate").write_text("down\n")

    # eth0: ethernet (not wireless)
    e0 = fake_net / "eth0"
    e0.mkdir()

    mgr = WifiRelayManager(sys_net_path=fake_net)

    with patch.object(mgr, "get_primary_interface", return_value="wlan0"), \
         patch.object(mgr, "_query_udev_info", side_effect=[
             ("iwlwifi", "Intel", "Wireless 8265"),
             ("rtw88_8822bu", "TP-Link", "Archer T4U"),
         ]), \
         patch.object(mgr, "_check_ap_support", return_value=True):
        devs = mgr.list_devices()

    assert len(devs) == 2
    dev_w0 = next(d for d in devs if d.iface == "wlan0")
    dev_w1 = next(d for d in devs if d.iface == "wlan1")

    assert dev_w0.is_primary is True
    assert dev_w0.is_candidate is False  # Protected!

    assert dev_w1.is_primary is False
    assert dev_w1.supports_ap is True
    assert dev_w1.is_candidate is True  # Candidate!


def test_start_relay_protects_primary_interface(mock_helper):
    mgr = WifiRelayManager(helper=mock_helper)
    with patch.object(mgr, "get_primary_interface", return_value="wlan0"):
        with pytest.raises(ValueError, match="primary host Wi-Fi connection"):
            mgr.start_relay(interface="wlan0")


def test_start_relay_success(mock_helper):
    mgr = WifiRelayManager(helper=mock_helper)

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["nmcli"],
        returncode=0,
        stdout="Connection 'mislty-relay' successfully added and activated.\n",
        stderr="",
    ))

    with patch.object(mgr, "get_primary_interface", return_value="wlan0"), \
         patch("subprocess.run", mock_run), \
         patch.object(mgr, "_resolve_interface_ip", return_value="10.42.0.1"):
        stat = mgr.start_relay(
            interface="wlan1",
            ssid="MisLTy 4G Share",
            password="testpassword123",
            band="bg",
            channel=11,
            wan_iface="ppp0",
        )

    assert stat["active"] is True
    assert stat["interface"] == "wlan1"
    assert stat["ssid"] == "MisLTy 4G Share"
    assert stat["ip_address"] == "10.42.0.1"
    assert stat["wan_iface"] == "ppp0"

    # Verify helper enable_nat called with ppp0 and wlan1
    mock_helper.enable_nat.assert_called_once_with("ppp0", "wlan1")


def test_stop_relay_success(mock_helper):
    mgr = WifiRelayManager(helper=mock_helper)
    mgr._status = RelayStatus(
        active=True,
        interface="wlan1",
        ssid="MisLTy 4G Share",
        wan_iface="ppp0",
    )

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["nmcli"],
        returncode=0,
        stdout="",
        stderr="",
    ))

    with patch("subprocess.run", mock_run):
        stat = mgr.stop_relay()

    assert stat["active"] is False
    mock_helper.disable_nat.assert_called_once_with("ppp0", "wlan1")


def test_get_connected_clients_parsing():
    mgr = WifiRelayManager()
    mgr._status = RelayStatus(active=True, interface="wlan1")

    sample_station_dump = """Station b4:b0:24:aa:bb:cc (on wlan1)
\tinactive time:\t350 ms
\trx bytes:\t12345
\trx packets:\t80
\ttx bytes:\t67890
\ttx packets:\t110
\tsignal:\t-48 dBm
\tsignal avg:\t-47 dBm
\ttx bitrate:\t72.2 MBit/s
"""
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["iw", "dev", "wlan1", "station", "dump"],
        returncode=0,
        stdout=sample_station_dump,
        stderr="",
    ))

    with patch("subprocess.run", mock_run), \
         patch.object(mgr, "_get_arp_table", return_value={"b4:b0:24:aa:bb:cc": "10.42.0.52"}):
        clients = mgr.get_connected_clients()

    assert len(clients) == 1
    c = clients[0]
    assert c.mac == "b4:b0:24:aa:bb:cc"
    assert c.ip == "10.42.0.52"
    assert c.signal_dbm == -48
    assert c.rx_bytes == 12345
    assert c.tx_bytes == 67890
    assert c.inactive_ms == 350
