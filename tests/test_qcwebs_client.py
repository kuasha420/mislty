"""
tests.test_qcwebs_client
~~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for embedded QC-Webs client, station table scraper,
and SmartModeSwitcher state engine.
"""

import json
from unittest.mock import MagicMock, patch
import pytest

from mislty.net.qcwebs_client import QcWebsClient, SmartModeSwitcher


SAMPLE_REFRESH_DATA_JSON = json.dumps({
    "network_type": "LTE",
    "realtime_statistics": "1024,2048,1048576,524288,3600,61732223,898445230,57521",
    "ppp_status": "ppp_connected",
    "cardstate": "modem_init_complete",
    "roam": "roam_off",
})

SAMPLE_STATION_LIST_HTML = """
<!DOCTYPE html>
<html>
<head><title>4G Router</title></head>
<body>
<div class="wrap">
    <table class="list">
        <tr><th colspan="2" class="title" id="ui_wireless_network">Wireless Network</th></tr>
        <tr>
            <th align="center" width="50%" id="ui_station">Station</th>
            <th align="center" id="ui_mac_address">MAC Address</th>
        </tr>
        <tr><td align="center" width="40%" class="head">1</td><td align="center" width="60%" class="tail">D2:6F:5B:13:A8:B5</td></tr>
        <tr><td align="center" width="40%" class="head">2</td><td align="center" width="60%" class="tail">AC:DE:48:00:11:22</td></tr>
    </table>
</div>
</body>
</html>
"""


def test_qcwebs_realtime_statistics_parsing():
    """Verify realtime telemetry parsing from /json/refresh_data.asp."""
    client = QcWebsClient()

    with patch.object(client, "_request", return_value=(200, SAMPLE_REFRESH_DATA_JSON)):
        stats = client.get_realtime_statistics()
        assert stats is not None
        assert stats["network_type"] == "LTE"
        assert stats["ppp_status"] == "ppp_connected"
        assert stats["speed_up"] == 1024
        assert stats["speed_down"] == 2048
        assert stats["current_tx_bytes"] == 1048576
        assert stats["current_rx_bytes"] == 524288
        assert stats["session_duration"] == 3600
        assert stats["total_tx_bytes"] == 61732223
        assert stats["total_rx_bytes"] == 898445230
        assert stats["total_uptime"] == 57521


def test_qcwebs_station_list_scraping():
    """Verify HTML scraping of active wireless stations from station_list.asp."""
    client = QcWebsClient()

    with patch.object(client, "_request", return_value=(200, SAMPLE_STATION_LIST_HTML)):
        stations = client.get_station_list()
        assert len(stations) == 2
        assert stations[0]["index"] == 1
        assert stations[0]["mac"] == "D2:6F:5B:13:A8:B5"
        assert stations[1]["index"] == 2
        assert stations[1]["mac"] == "AC:DE:48:00:11:22"


def test_qcwebs_form_payloads():
    """Verify form parameters dispatched to /goform/goform_process."""
    client = QcWebsClient()

    # Test WIFI_BASIC
    with patch.object(client, "_request", return_value=(200, "OK")) as mock_req:
        res = client.set_wifi_basic(ssid="MisLTy-Ultra", broadcast=True, mode=0, channel=6, max_stas=5)
        assert res is True
        mock_req.assert_called_once()
        _, kwargs = mock_req.call_args
        data = kwargs["data"]
        assert data["goformId"] == "WIFI_BASIC"
        assert data["ssid"] == "MisLTy-Ultra"
        assert data["broadcastssid"] == "1"
        assert data["channel"] == "6"
        assert data["Allow_MAX_STAs"] == "5"

    # Test WIFI_SECURITY
    with patch.object(client, "_request", return_value=(200, "OK")) as mock_req:
        res = client.set_wifi_security(passphrase="SecretPassword420")
        assert res is True
        _, kwargs = mock_req.call_args
        data = kwargs["data"]
        assert data["goformId"] == "WIFI_SECURITY"
        assert data["passphrase"] == "SecretPassword420"
        assert data["cipher"] == "2"


def test_smart_mode_switcher():
    """Verify mode handover between USB Modem and Pocket Router."""
    mock_qcwebs = MagicMock()
    mock_qcwebs.set_wan_connect.return_value = True

    mock_ppp = MagicMock()
    mock_ppp.connect.return_value = True
    mock_ppp.disconnect.return_value = True

    mock_disp = MagicMock()
    mock_disp.execute.return_value = MagicMock(success=True)

    switcher = SmartModeSwitcher(
        qcwebs_client=mock_qcwebs,
        ppp_controller=mock_ppp,
        dispatcher=mock_disp,
    )

    # Switch to Router Mode
    res_router = switcher.switch_to_router_mode()
    assert res_router["success"] is True
    assert res_router["mode"] == SmartModeSwitcher.MODE_ROUTER
    assert switcher.current_mode == SmartModeSwitcher.MODE_ROUTER
    mock_ppp.disconnect.assert_called_once()
    mock_qcwebs.set_wan_connect.assert_called_with(connect=True)

    # Switch back to USB Mode
    res_usb = switcher.switch_to_usb_mode(apn="internet")
    assert res_usb["success"] is True
    assert res_usb["mode"] == SmartModeSwitcher.MODE_USB
    assert switcher.current_mode == SmartModeSwitcher.MODE_USB
    mock_qcwebs.set_wan_connect.assert_called_with(connect=False)
    mock_ppp.connect.assert_called_once()
