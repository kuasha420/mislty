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
import time
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
        is_in_use=False,
        active_connection=None,
        supports_ap=True,
        is_candidate=True,
    )
    d = dev.as_dict()
    assert d["iface"] == "wlan1"
    assert d["is_candidate"] is True
    assert d["is_primary"] is False
    assert d["is_in_use"] is False
    assert d["active_connection"] is None


def test_get_active_wifi_devices_nmcli():
    mgr = WifiRelayManager()
    fake_nmcli_out = (
        "wlan0:wifi:connected:ECMAScript 69\n"
        "wlan1:wifi:connected:mislty-relay\n"
        "eth0:ethernet:connected:Wired Connection 1\n"
        "wlan2:wifi:disconnected:\n"
    )
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["nmcli"],
        returncode=0,
        stdout=fake_nmcli_out,
        stderr="",
    ))
    with patch("subprocess.run", mock_run):
        active = mgr.get_active_wifi_devices()
        assert "wlan0" in active
        assert active["wlan0"] == "ECMAScript 69"
        # mislty-relay must be ignored
        assert "wlan1" not in active
        # ethernet must be ignored
        assert "eth0" not in active
        # disconnected must not be present
        assert "wlan2" not in active
        assert mgr.get_primary_interface() == "wlan0"


def test_get_active_wifi_devices_empty_in_ppp_only():
    mgr = WifiRelayManager()
    fake_nmcli_out = (
        "wlan0:wifi:disconnected:\n"
        "wlan1:wifi:disconnected:\n"
        "ppp0:ppp:connected:mislty-ppp\n"
    )
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["nmcli"],
        returncode=0,
        stdout=fake_nmcli_out,
        stderr="",
    ))
    with patch("subprocess.run", mock_run):
        active = mgr.get_active_wifi_devices()
        assert len(active) == 0
        assert mgr.get_primary_interface() is None


def test_list_devices_dynamic_state_protection(tmp_path):
    # Setup fake /sys/class/net directory
    fake_net = tmp_path / "sys_net"
    fake_net.mkdir()

    # wlan0: built-in, AP capable
    w0 = fake_net / "wlan0"
    w0.mkdir()
    (w0 / "wireless").mkdir()
    (w0 / "address").write_text("64:79:f0:36:70:ae\n")
    (w0 / "operstate").write_text("up\n")

    # wlan1: secondary USB dongle, AP capable
    w1 = fake_net / "wlan1"
    w1.mkdir()
    (w1 / "wireless").mkdir()
    (w1 / "address").write_text("a6:7a:40:5f:c3:13\n")
    (w1 / "operstate").write_text("down\n")

    mgr = WifiRelayManager(sys_net_path=fake_net)

    # Case A: Host connected to Wi-Fi on wlan0 -> wlan0 protected, wlan1 candidate
    with patch.object(mgr, "get_active_wifi_devices", return_value={"wlan0": "ECMAScript 69"}), \
         patch.object(mgr, "_query_udev_info", side_effect=[
             ("iwlwifi", "Intel", "Wireless 8265"),
             ("rtw88_8822bu", "TP-Link", "Archer T4U"),
         ]), \
         patch.object(mgr, "_check_ap_support", return_value=True):
        devs = mgr.list_devices()

    assert len(devs) == 2
    dev_w0 = next(d for d in devs if d.iface == "wlan0")
    dev_w1 = next(d for d in devs if d.iface == "wlan1")

    assert dev_w0.is_in_use is True
    assert dev_w0.is_primary is True
    assert dev_w0.active_connection == "ECMAScript 69"
    assert dev_w0.is_candidate is False  # Protected!

    assert dev_w1.is_in_use is False
    assert dev_w1.is_candidate is True  # Candidate!

    # Case B: Standalone PPP-only mode (NO active Wi-Fi connection anywhere)
    # Both wlan0 and wlan1 are idle candidates!
    with patch.object(mgr, "get_active_wifi_devices", return_value={}), \
         patch.object(mgr, "_query_udev_info", side_effect=[
             ("iwlwifi", "Intel", "Wireless 8265"),
             ("rtw88_8822bu", "TP-Link", "Archer T4U"),
         ]), \
         patch.object(mgr, "_check_ap_support", return_value=True):
        devs_ppp = mgr.list_devices()

    w0_ppp = next(d for d in devs_ppp if d.iface == "wlan0")
    w1_ppp = next(d for d in devs_ppp if d.iface == "wlan1")

    assert w0_ppp.is_in_use is False
    assert w0_ppp.is_candidate is True  # Available as relay AP!
    assert w1_ppp.is_in_use is False
    assert w1_ppp.is_candidate is True  # Also available!

    # Case C: Host connected to Wi-Fi on wlan1 -> wlan1 protected, wlan0 candidate
    with patch.object(mgr, "get_active_wifi_devices", return_value={"wlan1": "Office-5G"}), \
         patch.object(mgr, "_query_udev_info", side_effect=[
             ("iwlwifi", "Intel", "Wireless 8265"),
             ("rtw88_8822bu", "TP-Link", "Archer T4U"),
         ]), \
         patch.object(mgr, "_check_ap_support", return_value=True):
        devs_rev = mgr.list_devices()

    w0_rev = next(d for d in devs_rev if d.iface == "wlan0")
    w1_rev = next(d for d in devs_rev if d.iface == "wlan1")

    assert w0_rev.is_in_use is False
    assert w0_rev.is_candidate is True  # Built-in is now candidate!
    assert w1_rev.is_in_use is True
    assert w1_rev.is_candidate is False  # USB dongle is protected!


def test_start_relay_protects_active_interface(mock_helper):
    mgr = WifiRelayManager(helper=mock_helper)
    with patch.object(mgr, "get_active_wifi_devices", return_value={"wlan0": "ECMAScript 69"}):
        with pytest.raises(ValueError, match="actively connected to 'ECMAScript 69'"):
            mgr.start_relay(interface="wlan0")


def test_start_relay_success_on_secondary(mock_helper):
    mgr = WifiRelayManager(helper=mock_helper)

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["nmcli"],
        returncode=0,
        stdout="Connection 'mislty-relay' successfully added and activated.\n",
        stderr="",
    ))

    with patch.object(mgr, "get_active_wifi_devices", return_value={"wlan0": "ECMAScript 69"}), \
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
    mock_helper.enable_nat.assert_called_once_with("ppp0", "wlan1")


def test_start_relay_in_ppp_only_mode_allows_wlan0(mock_helper):
    """In PPP-only mode (no host Wi-Fi active), wlan0 is idle and can be used as relay AP."""
    mgr = WifiRelayManager(helper=mock_helper)

    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["nmcli"],
        returncode=0,
        stdout="Connection 'mislty-relay' successfully added and activated.\n",
        stderr="",
    ))

    # In PPP-only mode, active_wifi is empty
    with patch.object(mgr, "get_active_wifi_devices", return_value={}), \
         patch("subprocess.run", mock_run), \
         patch.object(mgr, "_resolve_interface_ip", return_value="10.42.0.1"):
        stat = mgr.start_relay(
            interface="wlan0",
            ssid="MisLTy 4G Share",
            password="testpassword123",
            band="bg",
            channel=11,
            wan_iface="ppp0",
        )

    assert stat["active"] is True
    assert stat["interface"] == "wlan0"
    mock_helper.enable_nat.assert_called_once_with("ppp0", "wlan0")


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


def test_get_connected_clients_excludes_dropped_and_cleans_stale_arp():
    """Verify that when a client disconnects from AP, it is immediately excluded from clients."""
    mgr = WifiRelayManager()
    mgr._status = RelayStatus(active=True, interface="wlan1")

    # iw station dump returns empty stdout (meaning 0 stations associated)
    mock_run = MagicMock(return_value=subprocess.CompletedProcess(
        args=["iw", "dev", "wlan1", "station", "dump"],
        returncode=0,
        stdout="",
        stderr="",
    ))

    # /proc/net/arp still holds a stale entry for the dropped device
    stale_arp = {"dc:44:60:49:5c:41": "10.42.0.145"}

    with patch("subprocess.run", mock_run), \
         patch.object(mgr, "_get_arp_table", return_value=stale_arp):
        clients = mgr.get_connected_clients()

    # Dropped client MUST NOT be included!
    assert clients == []

    # Verify that ip neigh del was called to purge the stale ARP entry from the kernel
    del_calls = [
        call for call in mock_run.call_args_list
        if call.args and call.args[0] == ["ip", "neigh", "del", "10.42.0.145", "dev", "wlan1"]
    ]
    assert len(del_calls) == 1


def test_get_connected_clients_fallback_filters_stale():
    """Verify fallback to ip neigh nud reachable when iw is unavailable."""
    mgr = WifiRelayManager()
    mgr._status = RelayStatus(active=True, interface="wlan1")

    # iw returns returncode 1 (not supported)
    def fake_subprocess_run(args, **kwargs):
        if args[:4] == ["iw", "dev", "wlan1", "station"]:
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="Not supported")
        elif args[:6] == ["ip", "neigh", "show", "dev", "wlan1", "nud"]:
            # Only reachable neighbors returned
            output = "10.42.0.200 dev wlan1 lladdr aa:bb:cc:11:22:33 REACHABLE\n"
            return subprocess.CompletedProcess(args=args, returncode=0, stdout=output, stderr="")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=fake_subprocess_run), \
         patch.object(mgr, "_get_arp_table", return_value={"aa:bb:cc:11:22:33": "10.42.0.200"}):
        clients = mgr.get_connected_clients()

    assert len(clients) == 1
    assert clients[0].mac == "aa:bb:cc:11:22:33"
    assert clients[0].ip == "10.42.0.200"


def test_get_status_includes_clients():
    """Verify get_status returns updated clients inventory."""
    mgr = WifiRelayManager()
    mgr._status = RelayStatus(active=True, interface="wlan1", start_time=time.time() - 10)

    fake_client = RelayClient(mac="aa:bb:cc:dd:ee:ff", ip="10.42.0.10", signal_dbm=-50)
    with patch.object(mgr, "get_connected_clients", return_value=[fake_client]):
        stat = mgr.get_status()

    assert stat.client_count == 1
    assert len(stat.clients) == 1
    assert stat.clients[0]["mac"] == "aa:bb:cc:dd:ee:ff"
    assert stat.clients[0]["ip"] == "10.42.0.10"

