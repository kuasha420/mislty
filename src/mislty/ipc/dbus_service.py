"""
mislty.ipc.dbus_service
~~~~~~~~~~~~~~~~~~~~~~~

D-Bus Session Bus interface exposing org.mislty.Modem for desktop environments,
system tray applets, and desktop notification services.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Dict, Optional

from mislty.ipc.dispatcher import IpcDispatcher

logger = logging.getLogger("mislty.ipc.dbus")

# Detect D-Bus availability
DBUS_AVAILABLE = False
try:
    import dbus
    import dbus.service
    from dbus.mainloop.glib import DBusGMainLoop
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    pass


class DbusService:
    """
    Manager for the org.mislty.Modem D-Bus Session Bus service.
    """

    BUS_NAME = "org.mislty.Modem"
    OBJECT_PATH = "/org/mislty/Modem"
    INTERFACE_NAME = "org.mislty.Modem"

    def __init__(
        self,
        dispatcher: IpcDispatcher,
        bus_name: str = BUS_NAME,
        object_path: str = OBJECT_PATH,
    ) -> None:
        self.dispatcher = dispatcher
        self.bus_name = bus_name
        self.object_path = object_path
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[Any] = None
        self._dbus_object: Optional[Any] = None
        self._is_running = False
        self._ready_event = threading.Event()
        self._lock = threading.Lock()
        self._bus: Optional[Any] = None

    @property
    def is_available(self) -> bool:
        return DBUS_AVAILABLE

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self, timeout: float = 3.0) -> bool:
        """Launch D-Bus service loop in a dedicated background thread."""
        if not DBUS_AVAILABLE:
            logger.info("D-Bus Python bindings not available; skipping D-Bus service.")
            return False

        with self._lock:
            if self._is_running:
                return True

            self._ready_event.clear()
            self._thread = threading.Thread(
                target=self._run_service,
                name="mislty-dbus",
                daemon=True,
            )
            self._thread.start()

        if self._ready_event.wait(timeout=timeout):
            logger.info("D-Bus service registered successfully as %s", self.bus_name)
            return True
        else:
            logger.warning("Timed out waiting for D-Bus service registration.")
            return False

    def stop(self) -> None:
        """Stop D-Bus service loop."""
        with self._lock:
            if not self._is_running:
                return

            self._is_running = False

            if self._dbus_object is not None:
                try:
                    self._dbus_object.remove_from_connection()
                except Exception:
                    pass
                self._dbus_object = None

            if self._bus and self.bus_name:
                try:
                    self._bus.release_name(self.bus_name)
                except Exception:
                    pass
                self._bus = None

            if self._loop:
                try:
                    self._loop.quit()
                except Exception:
                    pass

            if self._thread:
                self._thread.join(timeout=2.0)
                self._thread = None

            logger.info("D-Bus service stopped.")

    def emit_signal_quality(self, rssi: int, dbm: int) -> None:
        """Emit SignalQualityChanged D-Bus signal."""
        if self._dbus_object:
            try:
                self._dbus_object.SignalQualityChanged(int(rssi), int(dbm))
            except Exception as exc:
                logger.debug("Failed to emit SignalQualityChanged signal: %s", exc)

    def emit_sms_received(self, sender: str, body: str) -> None:
        """Emit SmsReceived D-Bus signal."""
        if self._dbus_object:
            try:
                self._dbus_object.SmsReceived(str(sender), str(body))
            except Exception as exc:
                logger.debug("Failed to emit SmsReceived signal: %s", exc)

    def emit_mode_changed(self, technology: str) -> None:
        """Emit ModeChanged D-Bus signal."""
        if self._dbus_object:
            try:
                self._dbus_object.ModeChanged(str(technology))
            except Exception as exc:
                logger.debug("Failed to emit ModeChanged signal: %s", exc)

    def emit_state_changed(self, state: str) -> None:
        """Emit StateChanged D-Bus signal."""
        if self._dbus_object:
            try:
                self._dbus_object.StateChanged(str(state))
            except Exception as exc:
                logger.debug("Failed to emit StateChanged signal: %s", exc)

    def _run_service(self) -> None:
        """Internal worker method executed within background thread."""
        try:
            DBusGMainLoop(set_as_default=True)
            bus = dbus.SessionBus()
            self._bus = bus
            bus_name = dbus.service.BusName(self.bus_name, bus, replace_existing=True, allow_replacement=True, do_not_queue=True)

            class _ModemObject(dbus.service.Object):
                def __init__(inner_self, bus, path, dispatcher: IpcDispatcher):
                    super().__init__(bus, path)
                    inner_self.dispatcher = dispatcher

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def Ping(inner_self) -> str:
                    return inner_self.dispatcher.dispatch("ping")

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def GetStatus(inner_self) -> str:
                    res = inner_self.dispatcher.dispatch("status")
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="sb", out_signature="b")
                def Connect(inner_self, apn: str, default_route: bool) -> bool:
                    res = inner_self.dispatcher.dispatch("connect", {
                        "apn": str(apn),
                        "default_route": bool(default_route),
                    })
                    return bool(res.get("success"))

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="b")
                def Disconnect(inner_self) -> bool:
                    res = inner_self.dispatcher.dispatch("disconnect")
                    return bool(res.get("success"))

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="b", out_signature="b")
                def SetWifiPower(inner_self, enable: bool) -> bool:
                    res = inner_self.dispatcher.dispatch("wifi_power", {"enable": bool(enable)})
                    return bool(res.get("success"))

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="ss", out_signature="b")
                def SetWifiCredentials(inner_self, ssid: str, password: str) -> bool:
                    pwd = str(password) if password else None
                    res = inner_self.dispatcher.dispatch("wifi_config", {"ssid": str(ssid), "password": pwd})
                    return bool(res.get("success"))

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def GetWifiClients(inner_self) -> str:
                    res = inner_self.dispatcher.dispatch("wifi_clients")
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="ss", out_signature="s")
                def SendSms(inner_self, recipient: str, text: str) -> str:
                    res = inner_self.dispatcher.dispatch("send_sms", {"recipient": str(recipient), "text": str(text)})
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="x", out_signature="s")
                def ListSms(inner_self, thread_id: int) -> str:
                    tid = int(thread_id) if thread_id > 0 else None
                    res = inner_self.dispatcher.dispatch("list_sms", {"thread_id": tid})
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="b", out_signature="s")
                def SyncSms(inner_self, purge_sim: bool) -> str:
                    res = inner_self.dispatcher.dispatch("sync_sms", {"purge_sim": bool(purge_sim)})
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="x", out_signature="s")
                def DeleteThread(inner_self, thread_id: int) -> str:
                    res = inner_self.dispatcher.dispatch("delete_sms_thread", {"thread_id": int(thread_id)})
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="x", out_signature="s")
                def MarkThreadRead(inner_self, thread_id: int) -> str:
                    res = inner_self.dispatcher.dispatch("mark_sms_read", {"thread_id": int(thread_id)})
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="s", out_signature="s")
                def ExecuteAt(inner_self, command: str) -> str:
                    res = inner_self.dispatcher.dispatch("at", {"command": str(command)})
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def ListWlanDevices(inner_self) -> str:
                    res = inner_self.dispatcher.dispatch("relay_devices")
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, in_signature="ssssis", out_signature="s")
                def StartHotspotRelay(
                    inner_self,
                    interface: str,
                    ssid: str,
                    password: str,
                    band: str,
                    channel: int,
                    wan_iface: str,
                ) -> str:
                    res = inner_self.dispatcher.dispatch("relay_start", {
                        "interface": str(interface),
                        "ssid": str(ssid),
                        "password": str(password) if password else None,
                        "band": str(band),
                        "channel": int(channel),
                        "wan_iface": str(wan_iface),
                    })
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def StopHotspotRelay(inner_self) -> str:
                    res = inner_self.dispatcher.dispatch("relay_stop")
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def GetHotspotRelayStatus(inner_self) -> str:
                    res = inner_self.dispatcher.dispatch("relay_status")
                    return json.dumps(res)

                @dbus.service.method(DbusService.INTERFACE_NAME, out_signature="s")
                def GetHotspotRelayClients(inner_self) -> str:
                    res = inner_self.dispatcher.dispatch("relay_clients")
                    return json.dumps(res)

                @dbus.service.signal(DbusService.INTERFACE_NAME, signature="ii")
                def SignalQualityChanged(inner_self, rssi: int, dbm: int) -> None:
                    pass

                @dbus.service.signal(DbusService.INTERFACE_NAME, signature="ss")
                def SmsReceived(inner_self, sender: str, body: str) -> None:
                    pass

                @dbus.service.signal(DbusService.INTERFACE_NAME, signature="s")
                def ModeChanged(inner_self, technology: str) -> None:
                    pass

                @dbus.service.signal(DbusService.INTERFACE_NAME, signature="s")
                def StateChanged(inner_self, state: str) -> None:
                    pass

            self._dbus_object = _ModemObject(bus, self.object_path, self.dispatcher)
            self._loop = GLib.MainLoop()
            self._is_running = True
            self._ready_event.set()
            self._loop.run()

        except Exception as exc:
            logger.error("Failed to initialize D-Bus service: %s", exc)
            self._is_running = False
            self._ready_event.set()
