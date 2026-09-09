"""
Unit tests for MisLTy IPC layer:
- IpcDispatcher
- JsonRpcSocketServer
- DbusService
"""

import json
from pathlib import Path
import socket
import threading
import time
from unittest.mock import MagicMock, patch
import pytest

from mislty.core.daemon import DaemonEngine, DaemonState
from mislty.ipc.dbus_service import DbusService
from mislty.ipc.dispatcher import (
    InvalidParamsError,
    IpcDispatcher,
    IpcError,
    MethodNotFoundError,
)
from mislty.ipc.socket_server import JsonRpcSocketServer, get_default_socket_path


@pytest.fixture
def mock_engine():
    """Create a mock DaemonEngine with simulated subsystems."""
    engine = MagicMock(spec=DaemonEngine)
    engine.state = DaemonState(is_running=True, connected=True, rssi=31, dbm=-51)
    engine.ports = MagicMock()
    engine.ports.as_dict.return_value = {"data": "/dev/mislty/data", "control": "/dev/mislty/control"}
    engine.ppp = MagicMock()
    engine.ppp.get_status.return_value = MagicMock(as_dict=lambda: {"connected": False})
    engine.wifi = MagicMock()
    engine.wifi.get_radio_power.return_value = True
    engine.wifi.get_ssid_serial.return_value = "TypeScript 420"
    engine.wifi.get_connected_clients.return_value = []
    engine.get_full_status.return_value = {
        "daemon": engine.state.as_dict(),
        "hardware": engine.ports.as_dict(),
        "cellular_ppp": {"connected": False},
        "wifi": {"power": True, "ssid": "TypeScript 420", "clients_count": 0},
    }
    engine.connect_cellular.return_value = True
    engine.disconnect_cellular.return_value = True
    engine.set_wifi_power.return_value = True
    engine.set_wifi_credentials.return_value = True
    engine.get_wifi_clients.return_value = [{"hostname": "Device1", "ip": "192.168.100.2", "mac": "aa:bb:cc:dd:ee:ff"}]
    engine.send_sms.return_value = {"success": True, "message_id": 42, "recipient": "+1234567890"}
    engine.list_sms.return_value = [{"id": 1, "recipient_number": "+1234567890", "snippet": "Hello"}]
    engine.sync_sms.return_value = [{"id": 10, "phone_number": "+1234567890", "body": "SIM Message"}]
    engine.execute_at.return_value = {"command": "AT+CSQ", "success": True, "lines": ["+CSQ: 31,99"]}
    return engine


# ---------------------------------------------------------------------------
# IpcDispatcher Tests
# ---------------------------------------------------------------------------

def test_dispatcher_ping(mock_engine):
    """Verify ping method."""
    dispatcher = IpcDispatcher(mock_engine)
    assert dispatcher.dispatch("ping") == "pong"


def test_dispatcher_status(mock_engine):
    """Verify status method."""
    dispatcher = IpcDispatcher(mock_engine)
    res = dispatcher.dispatch("status")
    assert res["daemon"]["rssi"] == 31
    assert res["wifi"]["ssid"] == "TypeScript 420"
    mock_engine.get_full_status.assert_called_once()


def test_dispatcher_connect_disconnect(mock_engine):
    """Verify connect and disconnect methods."""
    dispatcher = IpcDispatcher(mock_engine)
    conn_res = dispatcher.dispatch("connect", {"apn": "test.apn", "default_route": False})
    assert conn_res["success"] is True
    mock_engine.connect_cellular.assert_called_once_with(apn="test.apn", default_route=False, timeout=20.0)

    disc_res = dispatcher.dispatch("disconnect")
    assert disc_res["success"] is True
    mock_engine.disconnect_cellular.assert_called_once()


def test_dispatcher_wifi_controls(mock_engine):
    """Verify Wi-Fi power, config, and clients methods."""
    dispatcher = IpcDispatcher(mock_engine)
    assert dispatcher.dispatch("wifi_power", {"enable": True})["success"] is True
    mock_engine.set_wifi_power.assert_called_once_with(True)

    assert dispatcher.dispatch("wifi_config", {"ssid": "NewSSID", "password": "pass"})["success"] is True
    mock_engine.set_wifi_credentials.assert_called_once_with("NewSSID", password="pass")

    clients = dispatcher.dispatch("wifi_clients")
    assert len(clients) == 1
    assert clients[0]["hostname"] == "Device1"


def test_dispatcher_sms_and_at(mock_engine):
    """Verify SMS operations and raw AT command execution."""
    dispatcher = IpcDispatcher(mock_engine)
    sent = dispatcher.dispatch("send_sms", {"recipient": "+1234567890", "text": "Test"})
    assert sent["message_id"] == 42
    mock_engine.send_sms.assert_called_once_with("+1234567890", "Test")

    messages = dispatcher.dispatch("list_sms", {"thread_id": 1})
    assert len(messages) == 1
    mock_engine.list_sms.assert_called_once_with(thread_id=1)

    synced = dispatcher.dispatch("sync_sms", {"purge_sim": True})
    assert len(synced) == 1
    mock_engine.sync_sms.assert_called_once_with(purge_sim=True)

    at_res = dispatcher.dispatch("at", {"command": "AT+CSQ"})
    assert at_res["success"] is True
    mock_engine.execute_at.assert_called_once_with("AT+CSQ", timeout=3.0)


def test_dispatcher_error_handling(mock_engine):
    """Verify error codes for missing methods and invalid parameters."""
    dispatcher = IpcDispatcher(mock_engine)

    with pytest.raises(MethodNotFoundError) as exc_info:
        dispatcher.dispatch("non_existent_method")
    assert exc_info.value.code == -32601

    with pytest.raises(InvalidParamsError) as exc_info:
        dispatcher.dispatch("send_sms", {"wrong_param": 123})
    assert exc_info.value.code == -32602


# ---------------------------------------------------------------------------
# JsonRpcSocketServer Tests
# ---------------------------------------------------------------------------

def test_json_rpc_socket_lifecycle(tmp_path, mock_engine):
    """Verify Unix socket creation, request processing, and cleanup."""
    sock_path = tmp_path / "test.sock"
    dispatcher = IpcDispatcher(mock_engine)
    server = JsonRpcSocketServer(dispatcher, socket_path=sock_path)

    assert not server.is_running
    server.start()
    assert server.is_running
    assert sock_path.exists()

    # 1. Connect client and perform JSON-RPC call
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.connect(str(sock_path))

    req = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 101}) + "\n"
    client.sendall(req.encode("utf-8"))

    resp_data = client.recv(4096).decode("utf-8")
    resp = json.loads(resp_data.strip())
    assert resp["jsonrpc"] == "2.0"
    assert resp["result"] == "pong"
    assert resp["id"] == 101

    # 2. Test invalid method
    req_err = json.dumps({"jsonrpc": "2.0", "method": "invalid_cmd", "id": 102}) + "\n"
    client.sendall(req_err.encode("utf-8"))
    resp_err = json.loads(client.recv(4096).decode("utf-8").strip())
    assert resp_err["error"]["code"] == -32601
    assert resp_err["id"] == 102

    # 3. Test parse error
    client.sendall(b"not a valid json string\n")
    resp_parse_err = json.loads(client.recv(4096).decode("utf-8").strip())
    assert resp_parse_err["error"]["code"] == -32700

    client.close()

    # 4. Stop server
    server.stop()
    assert not server.is_running
    assert not sock_path.exists()


def test_json_rpc_socket_concurrent_clients(tmp_path, mock_engine):
    """Verify handling of multiple concurrent client connections."""
    sock_path = tmp_path / "concurrent.sock"
    dispatcher = IpcDispatcher(mock_engine)
    server = JsonRpcSocketServer(dispatcher, socket_path=sock_path)
    server.start()

    num_clients = 5
    results = [None] * num_clients

    def worker(idx):
        c = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        c.connect(str(sock_path))
        req = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": idx}) + "\n"
        c.sendall(req.encode("utf-8"))
        res = json.loads(c.recv(4096).decode("utf-8").strip())
        results[idx] = res
        c.close()

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_clients)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=3.0)

    for i in range(num_clients):
        assert results[i] is not None
        assert results[i]["result"] == "pong"
        assert results[i]["id"] == i

    server.stop()


# ---------------------------------------------------------------------------
# DbusService Tests
# ---------------------------------------------------------------------------

def test_dbus_service_availability_and_signals(mock_engine):
    """Verify DbusService initialization and signal emission methods."""
    dispatcher = IpcDispatcher(mock_engine)
    service = DbusService(dispatcher)

    # Calling emit methods before start should not raise exceptions
    service.emit_signal_quality(31, -51)
    service.emit_sms_received("+1234567890", "Test signal")
    service.emit_mode_changed("LTE")
    service.emit_state_changed("CONNECTED")


def test_dbus_service_live_start_and_call(mock_engine):
    """Verify DbusService registration and call via busctl if desktop D-Bus is running."""
    dispatcher = IpcDispatcher(mock_engine)
    service = DbusService(dispatcher)

    if not service.is_available:
        pytest.skip("dbus module not available on system.")

    started = service.start(timeout=2.0)
    if not started:
        pytest.skip("D-Bus Session Bus not available in this environment.")

    assert service.is_running

    import subprocess
    cmd = [
        "busctl", "--user", "call",
        "org.mislty.Modem",
        "/org/mislty/Modem",
        "org.mislty.Modem",
        "Ping",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=3.0)
    assert res.returncode == 0
    assert "pong" in res.stdout

    service.stop()
    assert not service.is_running
