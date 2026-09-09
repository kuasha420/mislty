"""
Unit tests for unified MisltyClient:
- Automatic transport negotiation (socket vs direct fallback)
- JSON-RPC over Unix domain socket
- Direct serial / SQLite fallback execution
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from mislty.core.at_parser import AtResponse
from mislty.core.daemon import DaemonEngine, DaemonState
from mislty.ipc.client import ClientIpcError, MisltyClient
from mislty.ipc.dispatcher import IpcDispatcher
from mislty.ipc.socket_server import JsonRpcSocketServer


@pytest.fixture
def mock_engine():
    """Simulated DaemonEngine for socket testing."""
    engine = MagicMock(spec=DaemonEngine)
    engine.state = DaemonState(is_running=True, connected=True, rssi=31, dbm=-51)
    engine.ports = MagicMock()
    engine.ports.as_dict.return_value = {"control": "/dev/mislty/control", "data": "/dev/mislty/data"}
    engine.ppp = MagicMock()
    engine.ppp.get_status.return_value = MagicMock(as_dict=lambda: {"connected": False})
    engine.wifi = MagicMock()
    engine.wifi.get_radio_power.return_value = True
    engine.wifi.get_ssid_serial.return_value = "TypeScript 420"
    engine.wifi.get_connected_clients.return_value = [{"hostname": "Phone", "ip": "192.168.100.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    engine.get_full_status.return_value = {
        "daemon": engine.state.as_dict(),
        "hardware": engine.ports.as_dict(),
        "cellular_ppp": {"connected": False},
        "wifi": {"power": True, "ssid": "TypeScript 420", "clients_count": 1},
    }
    engine.connect_cellular.return_value = True
    engine.disconnect_cellular.return_value = True
    engine.set_wifi_power.return_value = True
    engine.set_wifi_credentials.return_value = True
    engine.get_wifi_clients.return_value = [{"hostname": "Phone", "ip": "192.168.100.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    engine.send_sms.return_value = {"success": True, "message_id": 99, "recipient": "+1234567890"}
    engine.list_sms.return_value = [{"id": 1, "recipient_number": "+1234567890", "snippet": "Hello"}]
    engine.sync_sms.return_value = [{"id": 10, "phone_number": "+1234567890", "body": "SIM Msg"}]
    engine.execute_at.return_value = {"command": "AT", "success": True, "lines": ["OK"]}
    return engine


def test_client_socket_transport(tmp_path, mock_engine):
    """Verify MisltyClient operations when connecting to active JSON-RPC socket."""
    sock_path = tmp_path / "test_client.sock"
    dispatcher = IpcDispatcher(mock_engine)
    server = JsonRpcSocketServer(dispatcher, socket_path=sock_path)
    server.start()

    with MisltyClient(socket_path=sock_path) as client:
        assert client.active_transport == MisltyClient.TRANSPORT_SOCKET
        assert client.ping() == "pong"

        # Status
        status = client.get_status()
        assert status["daemon"]["rssi"] == 31
        assert status["wifi"]["ssid"] == "TypeScript 420"

        # Cellular connect / disconnect
        assert client.connect(apn="my.apn")["success"] is True
        assert client.disconnect()["success"] is True

        # Wi-Fi controls
        assert client.set_wifi_power(True)["success"] is True
        assert client.set_wifi_credentials("Hotspot", "pass123")["success"] is True
        clients = client.get_wifi_clients()
        assert len(clients) == 1
        assert clients[0]["hostname"] == "Phone"

        # SMS operations
        assert client.send_sms("+1234567890", "Hi")["message_id"] == 99
        assert len(client.list_sms()) == 1
        assert len(client.sync_sms()) == 1

        # AT command execution
        assert client.execute_at("AT")["success"] is True

    server.stop()


def test_client_direct_fallback_negotiation(tmp_path):
    """Verify fallback to direct transport when socket does not exist."""
    non_existent_sock = tmp_path / "absent.sock"
    with patch.object(MisltyClient, "_try_connect_dbus", return_value=False):
        client = MisltyClient(socket_path=non_existent_sock)
        assert client.active_transport == MisltyClient.TRANSPORT_DIRECT
        assert client.ping() == "pong (direct)"
        client.close()


def test_client_direct_status(tmp_path):
    """Verify get_status in direct fallback mode."""
    with patch.object(MisltyClient, "_try_connect_dbus", return_value=False):
        client = MisltyClient(socket_path=tmp_path / "absent.sock", prefer_transport="direct")
        assert client.active_transport == MisltyClient.TRANSPORT_DIRECT

        with patch("mislty.core.port_resolver.PortResolver.resolve") as mock_res:
            mock_ports = MagicMock()
            mock_ports.is_ready = False
            mock_ports.control = None
            mock_ports.aux_wifi_netns = None
            mock_ports.as_dict.return_value = {"control": None, "data": None}
            mock_res.return_value = mock_ports

            status = client.get_status()
            assert status["daemon"]["operational_mode"] == "direct_fallback"
            assert status["hardware"]["control"] is None
        client.close()


def test_client_direct_at_execution(tmp_path):
    """Verify execute_at in direct fallback mode with mocked transport."""
    with patch.object(MisltyClient, "_try_connect_dbus", return_value=False):
        client = MisltyClient(socket_path=tmp_path / "absent.sock", prefer_transport="direct")

        mock_disp = MagicMock()
        mock_disp.execute.return_value = AtResponse(
            command="AT+CSQ",
            success=True,
            lines=["+CSQ: 28,99"],
            raw_text="+CSQ: 28,99\r\nOK",
        )

        with patch.object(client, "_direct_execute", side_effect=lambda cb: cb(MagicMock(), mock_disp)):
            res = client.execute_at("AT+CSQ")
            assert res["success"] is True
            assert res["lines"] == ["+CSQ: 28,99"]

        client.close()


def test_client_socket_error_handling(tmp_path, mock_engine):
    """Verify exception handling when server returns error response."""
    sock_path = tmp_path / "err.sock"
    dispatcher = IpcDispatcher(mock_engine)
    server = JsonRpcSocketServer(dispatcher, socket_path=sock_path)
    server.start()

    with MisltyClient(socket_path=sock_path) as client:
        # Invalid params call
        with pytest.raises(ClientIpcError) as exc_info:
            client._call_socket("send_sms", {"invalid_param": "val"})
        assert exc_info.value.code == -32602

    server.stop()
