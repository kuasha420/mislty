"""
mislty.ipc.client
~~~~~~~~~~~~~~~~~

Unified IPC client for the MisLTy suite.
Transparently communicates with misltyd via Unix Domain Socket JSON-RPC 2.0
or D-Bus Session Bus, with automatic fallback to direct serial AT commands
and local SQLite storage if the daemon is offline.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import socket
import time
from typing import Any, Dict, List, Optional, Union

from mislty.ipc.socket_server import get_default_socket_path

logger = logging.getLogger("mislty.ipc.client")

# Detect D-Bus availability
DBUS_AVAILABLE = False
try:
    import dbus
    DBUS_AVAILABLE = True
except ImportError:
    pass


class ClientIpcError(Exception):
    """Exception raised by MisLTy client when an IPC request fails."""
    def __init__(self, message: str, code: Optional[int] = None, data: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = data


class MisltyClient:
    """
    Unified client providing a consistent programmatic API across socket,
    D-Bus, and direct-to-hardware fallback modes.
    """

    TRANSPORT_SOCKET = "socket"
    TRANSPORT_DBUS = "dbus"
    TRANSPORT_DIRECT = "direct"

    def __init__(
        self,
        socket_path: Optional[Union[str, Path]] = None,
        prefer_transport: Optional[str] = None,
    ) -> None:
        self.socket_path = Path(socket_path) if socket_path else get_default_socket_path()
        self.prefer_transport = prefer_transport
        self._active_transport: Optional[str] = None
        self._socket_conn: Optional[socket.socket] = None
        self._dbus_object: Optional[Any] = None
        self._direct_resolver: Optional[Any] = None

        # Determine and initialize active transport
        self._negotiate_transport()

    @property
    def active_transport(self) -> str:
        """The currently active communication backend ('socket', 'dbus', or 'direct')."""
        return self._active_transport or self.TRANSPORT_DIRECT

    def _negotiate_transport(self) -> None:
        """Probe backends in order of preference to select active transport."""
        if self.prefer_transport == self.TRANSPORT_DIRECT:
            self._active_transport = self.TRANSPORT_DIRECT
            return

        # 1. Probe Unix domain socket
        if self.prefer_transport in (None, self.TRANSPORT_SOCKET):
            if self._try_connect_socket():
                self._active_transport = self.TRANSPORT_SOCKET
                logger.debug("MisltyClient connected via Unix domain socket (%s)", self.socket_path)
                return

        # 2. Probe D-Bus Session Bus
        if self.prefer_transport in (None, self.TRANSPORT_DBUS) and DBUS_AVAILABLE:
            if self._try_connect_dbus():
                self._active_transport = self.TRANSPORT_DBUS
                logger.debug("MisltyClient connected via D-Bus session bus (org.mislty.Modem)")
                return

        # 3. Fallback to direct hardware access
        self._active_transport = self.TRANSPORT_DIRECT
        logger.debug("Daemon not detected; MisltyClient using direct serial fallback.")

    def _try_connect_socket(self) -> bool:
        """Attempt connection to Unix domain socket server."""
        if not self.socket_path.exists():
            return False

        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(2.0)
            sock.connect(str(self.socket_path))
            # Test ping
            req = json.dumps({"jsonrpc": "2.0", "method": "ping", "id": 1}) + "\n"
            sock.sendall(req.encode("utf-8"))
            resp_line = sock.recv(4096).decode("utf-8").strip()
            resp = json.loads(resp_line)
            if resp.get("result") == "pong":
                self._socket_conn = sock
                return True
            sock.close()
        except Exception:
            pass
        return False

    def _try_connect_dbus(self) -> bool:
        """Attempt connection to D-Bus session bus service."""
        try:
            bus = dbus.SessionBus()
            obj = bus.get_object("org.mislty.Modem", "/org/mislty/Modem")
            # Probe Ping
            res = obj.Ping(dbus_interface="org.mislty.Modem")
            if str(res) == "pong":
                self._dbus_object = obj
                return True
        except Exception:
            pass
        return False

    def close(self) -> None:
        """Close client connections."""
        if self._socket_conn:
            try:
                self._socket_conn.close()
            except OSError:
                pass
            self._socket_conn = None

    def __enter__(self) -> MisltyClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # -----------------------------------------------------------------------
    # RPC Dispatch Helpers
    # -----------------------------------------------------------------------

    def _call_socket(
        self,
        method: str,
        params: Optional[Union[Dict[str, Any], List[Any]]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """Dispatch JSON-RPC call over active Unix domain socket."""
        if not self._socket_conn:
            if not self._try_connect_socket():
                raise ClientIpcError("Socket connection to misltyd lost.")

        req_id = int(time.time() * 1000)
        req = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params is not None:
            req["params"] = params

        payload = (json.dumps(req) + "\n").encode("utf-8")
        try:
            self._socket_conn.settimeout(timeout if timeout is not None else 10.0)
            self._socket_conn.sendall(payload)
            buffer = ""
            while "\n" not in buffer:
                chunk = self._socket_conn.recv(4096).decode("utf-8")
                if not chunk:
                    raise ClientIpcError("Socket closed prematurely by misltyd.")
                buffer += chunk

            line, _ = buffer.split("\n", 1)
            resp = json.loads(line.strip())
            if "error" in resp:
                err = resp["error"]
                raise ClientIpcError(err.get("message", "IPC error"), code=err.get("code"), data=err.get("data"))
            return resp.get("result")
        except socket.error as exc:
            self.close()
            raise ClientIpcError(f"Socket communication error: {exc}") from exc

    def _call_dbus(self, method_name: str, *args) -> Any:
        """Dispatch call via D-Bus object."""
        if not self._dbus_object:
            if not self._try_connect_dbus():
                raise ClientIpcError("D-Bus connection to org.mislty.Modem lost.")

        try:
            method = getattr(self._dbus_object, method_name)
            res = method(*args, dbus_interface="org.mislty.Modem")
            # Decode D-Bus primitives
            if isinstance(res, (str, dbus.String)):
                try:
                    return json.loads(str(res))
                except (json.JSONDecodeError, ValueError):
                    return str(res)
            elif isinstance(res, (bool, dbus.Boolean)):
                return bool(res)
            elif isinstance(res, (int, dbus.Int32, dbus.Int64)):
                return int(res)
            return res
        except Exception as exc:
            raise ClientIpcError(f"D-Bus invocation error: {exc}") from exc

    # -----------------------------------------------------------------------
    # Direct Fallback Implementations
    # -----------------------------------------------------------------------

    def _direct_execute(self, callback) -> Any:
        """Helper to run AT transactions with PortResolver and SerialTransport under lock."""
        from mislty.core.at_parser import AtDispatcher
        from mislty.core.port_resolver import PortResolver
        from mislty.core.serial_transport import SerialTransport

        resolver = PortResolver()
        ports = resolver.resolve()
        if not ports.control or not ports.control.exists():
            raise ClientIpcError("Modem control port not found on system.")

        transport = SerialTransport(ports.control, timeout=3.0, exclusive_lock=True)
        try:
            transport.open()
            dispatcher = AtDispatcher(transport)
            return callback(ports, dispatcher)
        finally:
            transport.close()

    # -----------------------------------------------------------------------
    # High-Level API Methods
    # -----------------------------------------------------------------------

    def ping(self) -> str:
        """Probe daemon connectivity."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("ping")
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("Ping")
        return "pong (direct)"

    def get_status(self) -> Dict[str, Any]:
        """Query full status across modem hardware, radio, Wi-Fi, and PPP."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("status")
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("GetStatus")

        # Direct fallback
        from mislty.core.port_resolver import PortResolver
        from mislty.net.ppp_controller import PppController
        from mislty.net.wifi_manager import WifiManager

        resolver = PortResolver()
        ports = resolver.resolve()
        ppp_mgr = PppController()
        ppp_stat = ppp_mgr.get_status().as_dict()

        status_data = {
            "daemon": {
                "is_running": False,
                "connected": ports.is_ready,
                "rssi": 0,
                "bars": 0,
                "dbm": None,
                "carrier": None,
                "technology": "UNKNOWN",
                "operational_mode": "direct_fallback",
            },
            "hardware": ports.as_dict(),
            "cellular_ppp": ppp_stat,
            "wifi": {
                "power": None,
                "ssid": None,
                "clients_count": 0,
            },
        }

        if ports.control and ports.control.exists():
            def _query_status(pts, disp):
                csq = disp.execute("AT+CSQ", timeout=2.0)
                if csq.success and csq.lines:
                    for line in csq.lines:
                        if "+CSQ:" in line:
                            val = line.split(":")[-1].strip().split(",")[0]
                            try:
                                raw_csq = int(val)
                                status_data["daemon"]["rssi"] = raw_csq
                                if raw_csq != 99:
                                    status_data["daemon"]["dbm"] = -113 + (raw_csq * 2)
                                    status_data["daemon"]["bars"] = min(4, max(1, raw_csq // 7))
                            except ValueError:
                                pass

                cops = disp.execute("AT+COPS?", timeout=2.0)
                if cops.success and cops.lines:
                    for line in cops.lines:
                        if "+COPS:" in line and '"' in line:
                            status_data["daemon"]["carrier"] = line.split('"')[1]

                wifi = WifiManager(disp)
                status_data["wifi"]["power"] = wifi.get_radio_power()
                status_data["wifi"]["ssid"] = wifi.get_ssid_serial()

            try:
                self._direct_execute(_query_status)
            except Exception:
                pass

        if ports.aux_wifi_netns:
            try:
                wifi = WifiManager()
                clients = wifi.get_connected_clients(netns=ports.aux_wifi_netns)
                status_data["wifi"]["clients_count"] = len(clients)
            except Exception:
                pass

        return status_data

    def connect(self, apn: str = "internet", default_route: bool = True, timeout: float = 20.0) -> Dict[str, Any]:
        """Establish cellular data connection."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("connect", {"apn": apn, "default_route": default_route, "timeout": timeout}, timeout=timeout + 5.0)
        elif self.active_transport == self.TRANSPORT_DBUS:
            ok = self._call_dbus("Connect", apn, default_route)
            return {"success": ok}

        # Direct fallback
        from mislty.net.ppp_controller import PppController
        controller = PppController()
        ok = controller.connect(apn=apn, default_route=default_route, timeout=timeout)
        stat = controller.get_status().as_dict()
        return {"success": ok, "status": stat}

    def disconnect(self) -> Dict[str, Any]:
        """Terminate active cellular connection and restore routing."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("disconnect")
        elif self.active_transport == self.TRANSPORT_DBUS:
            ok = self._call_dbus("Disconnect")
            return {"success": ok}

        # Direct fallback
        from mislty.net.ppp_controller import PppController
        controller = PppController()
        ok = controller.disconnect()
        return {"success": ok}

    def set_wifi_power(self, enable: bool) -> Dict[str, Any]:
        """Toggle Broadcom Wi-Fi radio power on/off."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("wifi_power", {"enable": enable})
        elif self.active_transport == self.TRANSPORT_DBUS:
            ok = self._call_dbus("SetWifiPower", enable)
            return {"success": ok, "power": enable}

        # Direct fallback
        from mislty.net.wifi_manager import WifiManager

        def _set_power(pts, disp):
            mgr = WifiManager(disp)
            ok = mgr.set_radio_power(enable)
            return {"success": ok, "power": enable}

        return self._direct_execute(_set_power)

    def set_wifi_credentials(self, ssid: str, password: Optional[str] = None) -> Dict[str, Any]:
        """Configure Wi-Fi SSID and WPA2 passphrase."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("wifi_config", {"ssid": ssid, "password": password})
        elif self.active_transport == self.TRANSPORT_DBUS:
            ok = self._call_dbus("SetWifiCredentials", ssid, password or "")
            return {"success": ok, "ssid": ssid}

        # Direct fallback
        from mislty.net.wifi_manager import WifiManager

        def _set_creds(pts, disp):
            mgr = WifiManager(disp)
            netns = pts.aux_wifi_netns if pts else None
            ok = mgr.set_clean_ssid_web(ssid, netns=netns)
            if not ok:
                ok = mgr.set_credentials_serial(ssid, password=password)
            return {"success": ok, "ssid": ssid}

        return self._direct_execute(_set_creds)

    def get_wifi_clients(self) -> List[Dict[str, str]]:
        """Query connected Wi-Fi client devices."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("wifi_clients")
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("GetWifiClients")

        # Direct fallback
        from mislty.core.port_resolver import PortResolver
        from mislty.net.wifi_manager import WifiManager

        ports = PortResolver().resolve()
        mgr = WifiManager()
        netns = ports.aux_wifi_netns if ports else None
        return mgr.get_connected_clients(netns=netns)

    def send_sms(self, recipient: str, text: str) -> Dict[str, Any]:
        """Send an SMS text message."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("send_sms", {"recipient": recipient, "text": text})
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("SendSms", recipient, text)

        # Direct fallback
        from mislty.storage.database import DatabaseManager
        from mislty.storage.sms_store import SmsStore

        def _send(pts, disp):
            resp = disp.send_sms(recipient, text)
            if resp.success:
                db = DatabaseManager()
                sms = SmsStore(db)
                saved = sms.save_message(
                    phone_number=recipient,
                    body=text,
                    direction="OUT",
                    status="SENT",
                    is_read=True,
                )
                db.close()
                return {"success": True, "message_id": saved.id, "recipient": recipient}
            return {"success": False, "error": resp.error, "error_detail": resp.error_detail}

        return self._direct_execute(_send)

    def list_sms(self, thread_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List SMS conversation threads or messages."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("list_sms", {"thread_id": thread_id})
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("ListSms", thread_id or 0)

        # Direct fallback
        from mislty.storage.database import DatabaseManager
        from mislty.storage.sms_store import SmsStore

        db = DatabaseManager()
        sms = SmsStore(db)
        try:
            if thread_id is not None:
                return [m.as_dict() for m in sms.get_thread_messages(thread_id)]
            return [t.as_dict() for t in sms.list_threads()]
        finally:
            db.close()

    def sync_sms(self, purge_sim: bool = True) -> List[Dict[str, Any]]:
        """Reconcile SMS from SIM card memory."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("sync_sms", {"purge_sim": purge_sim})
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("SyncSms", purge_sim)

        # Direct fallback
        from mislty.storage.database import DatabaseManager
        from mislty.storage.sms_store import SmsStore

        def _sync(pts, disp):
            db = DatabaseManager()
            sms = SmsStore(db)
            try:
                ingested = sms.reconcile_sim_inbox(disp, purge_sim=purge_sim)
                return [m.as_dict() for m in ingested]
            finally:
                db.close()

        return self._direct_execute(_sync)

    def delete_sms_thread(self, thread_id: int) -> Dict[str, Any]:
        """Delete an entire SMS conversation thread."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("delete_sms_thread", {"thread_id": thread_id})
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("DeleteThread", int(thread_id))

        # Direct fallback
        from mislty.storage.database import DatabaseManager
        from mislty.storage.sms_store import SmsStore

        db = DatabaseManager()
        sms = SmsStore(db)
        try:
            ok = sms.delete_thread(thread_id)
            return {"success": ok, "thread_id": thread_id}
        finally:
            db.close()

    def mark_sms_read(self, thread_id: int) -> Dict[str, Any]:
        """Mark SMS thread messages as read."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("mark_sms_read", {"thread_id": thread_id})
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("MarkThreadRead", int(thread_id))

        # Direct fallback
        from mislty.storage.database import DatabaseManager
        from mislty.storage.sms_store import SmsStore

        db = DatabaseManager()
        sms = SmsStore(db)
        try:
            sms.mark_thread_read(thread_id)
            return {"success": True, "thread_id": thread_id}
        finally:
            db.close()

    def execute_at(self, command: str, timeout: float = 3.0) -> Dict[str, Any]:
        """Execute raw AT command transaction."""
        if self.active_transport == self.TRANSPORT_SOCKET:
            return self._call_socket("at", {"command": command, "timeout": timeout})
        elif self.active_transport == self.TRANSPORT_DBUS:
            return self._call_dbus("ExecuteAt", command)

        # Direct fallback
        def _at(pts, disp):
            return disp.execute(command, timeout=timeout).as_dict()

        return self._direct_execute(_at)
