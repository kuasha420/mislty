"""
mislty.ipc.dispatcher
~~~~~~~~~~~~~~~~~~~~~

Central IPC command dispatcher bridging Unix Domain Socket JSON-RPC 2.0
and D-Bus session interfaces to the active DaemonEngine.
"""

from __future__ import annotations

import inspect
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Union

if TYPE_CHECKING:
    from mislty.core.daemon import DaemonEngine

logger = logging.getLogger("mislty.ipc.dispatcher")


class IpcError(Exception):
    """Base exception for IPC dispatch errors."""
    code: int = -32603

    def __init__(self, message: str, code: Optional[int] = None, data: Any = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code
        self.data = data


class MethodNotFoundError(IpcError):
    """Method does not exist / is not registered."""
    code: int = -32601


class InvalidParamsError(IpcError):
    """Invalid method parameter(s)."""
    code: int = -32602


class IpcDispatcher:
    """
    Unified command routing bridge for local IPC requests.
    """

    def __init__(self, engine: DaemonEngine) -> None:
        self.engine = engine
        self._methods: Dict[str, Callable[..., Any]] = {
            "status": self._handle_status,
            "connect": self._handle_connect,
            "disconnect": self._handle_disconnect,
            "wifi_power": self._handle_wifi_power,
            "wifi_config": self._handle_wifi_config,
            "wifi_clients": self._handle_wifi_clients,
            "send_sms": self._handle_send_sms,
            "list_sms": self._handle_list_sms,
            "sync_sms": self._handle_sync_sms,
            "delete_sms_thread": self._handle_delete_sms_thread,
            "mark_sms_read": self._handle_mark_sms_read,
            "at": self._handle_at,
            "ping": self._handle_ping,
            "relay_devices": self._handle_relay_devices,
            "relay_start": self._handle_relay_start,
            "relay_stop": self._handle_relay_stop,
            "relay_status": self._handle_relay_status,
            "relay_clients": self._handle_relay_clients,
        }

    def dispatch(
        self,
        method: str,
        params: Union[Dict[str, Any], List[Any], None] = None,
    ) -> Any:
        """
        Route and execute an incoming method invocation.
        """
        if method not in self._methods:
            raise MethodNotFoundError(f"Method '{method}' not found.")

        handler = self._methods[method]

        try:
            if params is None:
                return handler()
            elif isinstance(params, dict):
                return handler(**params)
            elif isinstance(params, (list, tuple)):
                return handler(*params)
            else:
                raise InvalidParamsError("Params must be an object, array, or null.")
        except TypeError as exc:
            raise InvalidParamsError(f"Invalid parameters for '{method}': {exc}") from exc
        except IpcError:
            raise
        except Exception as exc:
            logger.error("IPC execution error in '%s': %s", method, exc, exc_info=True)
            raise IpcError(str(exc)) from exc

    # Handlers
    def _handle_ping(self) -> str:
        return "pong"

    def _handle_status(self) -> Dict[str, Any]:
        return self.engine.get_full_status()

    def _handle_connect(
        self,
        apn: str = "internet",
        default_route: bool = True,
        timeout: float = 20.0,
    ) -> Dict[str, Any]:
        ok = self.engine.connect_cellular(apn=apn, default_route=default_route, timeout=timeout)
        stat = self.engine.ppp.get_status().as_dict()
        return {"success": ok, "status": stat}

    def _handle_disconnect(self) -> Dict[str, Any]:
        ok = self.engine.disconnect_cellular()
        return {"success": ok}

    def _handle_wifi_power(self, enable: bool) -> Dict[str, Any]:
        ok = self.engine.set_wifi_power(bool(enable))
        return {"success": ok, "power": enable}

    def _handle_wifi_config(self, ssid: str, password: Optional[str] = None) -> Dict[str, Any]:
        ok = self.engine.set_wifi_credentials(ssid, password=password)
        return {"success": ok, "ssid": ssid}

    def _handle_wifi_clients(self) -> List[Dict[str, str]]:
        return self.engine.get_wifi_clients()

    def _handle_send_sms(self, recipient: str, text: str) -> Dict[str, Any]:
        return self.engine.send_sms(recipient, text)

    def _handle_list_sms(self, thread_id: Optional[int] = None) -> List[Dict[str, Any]]:
        return self.engine.list_sms(thread_id=thread_id)

    def _handle_sync_sms(self, purge_sim: bool = True) -> List[Dict[str, Any]]:
        return self.engine.sync_sms(purge_sim=purge_sim)

    def _handle_delete_sms_thread(self, thread_id: int) -> Dict[str, Any]:
        return self.engine.delete_sms_thread(int(thread_id))

    def _handle_mark_sms_read(self, thread_id: int) -> Dict[str, Any]:
        return self.engine.mark_sms_read(int(thread_id))

    def _handle_at(self, command: str, timeout: float = 3.0) -> Dict[str, Any]:
        return self.engine.execute_at(command, timeout=timeout)

    def _handle_relay_devices(self) -> List[Dict[str, Any]]:
        return self.engine.list_wlan_devices()

    def _handle_relay_start(
        self,
        interface: str = "wlan1",
        ssid: str = "MisLTy 4G Share",
        password: Optional[str] = "mislty420",
        band: str = "bg",
        channel: int = 11,
        wan_iface: str = "ppp0",
    ) -> Dict[str, Any]:
        return self.engine.start_hotspot_relay(
            interface=str(interface),
            ssid=str(ssid),
            password=str(password) if password else None,
            band=str(band),
            channel=int(channel),
            wan_iface=str(wan_iface),
        )

    def _handle_relay_stop(self) -> Dict[str, Any]:
        return self.engine.stop_hotspot_relay()

    def _handle_relay_status(self) -> Dict[str, Any]:
        return self.engine.get_hotspot_relay_status()

    def _handle_relay_clients(self) -> List[Dict[str, Any]]:
        return self.engine.get_hotspot_relay_clients()
