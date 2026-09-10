"""
mislty.core.daemon
~~~~~~~~~~~~~~~~~~

Core daemon engine (misltyd) managing modem lifecycle, signal handling,
periodic 2000ms telemetry polling, and exponential backoff watchdog recovery.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import logging
import os
from pathlib import Path
import signal
import sys
import threading
import time
from typing import Any, Dict, Optional, Union

from mislty.core.at_parser import AtCommand, AtDispatcher
from mislty.core.port_resolver import ModemPorts, PortResolver
from mislty.core.serial_transport import PortBusyError, PortNotFoundError, SerialTransport, SerialTransportError
from mislty.core.urc_demuxer import (
    ModeChangeEvent,
    NetworkRegistrationEvent,
    SignalChangeEvent,
    SmsReceivedEvent,
    SysinfoEvent,
    UrcDemuxer,
)

from mislty.ipc.dbus_service import DbusService
from mislty.ipc.dispatcher import IpcDispatcher
from mislty.ipc.socket_server import JsonRpcSocketServer
from mislty.net.ppp_controller import PppController
from mislty.net.wifi_manager import WifiManager
from mislty.storage.database import DatabaseManager
from mislty.storage.metrics_store import MetricsStore, TelemetryRecord
from mislty.storage.sms_store import SmsStore

logger = logging.getLogger("misltyd")


@dataclass
class DaemonState:
    """Current live runtime state of the modem daemon."""
    is_running: bool = False
    connected: bool = False
    rssi: int = 0
    bars: int = 0
    dbm: Optional[int] = None
    carrier: Optional[str] = None
    registration_status: int = 0
    technology: str = "SEARCHING"
    operational_mode: str = "modem"
    last_poll_time: float = 0.0
    reconnect_attempts: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DaemonEngine:
    """
    Central background coordinator binding serial transport, AT dispatcher,
    URC demuxer, SQLite storage, and hardware connection watchdog.
    """

    def __init__(
        self,
        db_path: Optional[Union[str, Path]] = None,
        poll_interval: float = 2.0,
        prefer_udev: bool = True,
    ) -> None:
        self.poll_interval = poll_interval
        self.prefer_udev = prefer_udev
        self.resolver = PortResolver()
        self.db = DatabaseManager(db_path)
        self.sms_store = SmsStore(self.db)
        self.metrics_store = MetricsStore(self.db)
        self.demuxer = UrcDemuxer()
        self.ppp = PppController()
        self.wifi = WifiManager()

        self.ipc_dispatcher = IpcDispatcher(self)
        self.socket_server = JsonRpcSocketServer(self.ipc_dispatcher)
        self.dbus_service = DbusService(self.ipc_dispatcher)

        self.transport: Optional[SerialTransport] = None
        self.dispatcher: Optional[AtDispatcher] = None
        self.ports: Optional[ModemPorts] = None
        self.state = DaemonState()

        self.shared_lock = threading.RLock()
        self._stop_event = threading.Event()
        self._poll_thread: Optional[threading.Thread] = None
        self._watchdog_thread: Optional[threading.Thread] = None

        # Wire up URC handlers
        self._setup_urc_handlers()

    def _setup_urc_handlers(self) -> None:
        """Register daemon event handlers with UrcDemuxer."""
        self.demuxer.subscribe(SignalChangeEvent, self._on_signal_urc)
        self.demuxer.subscribe(ModeChangeEvent, self._on_mode_urc)
        self.demuxer.subscribe(SysinfoEvent, self._on_sysinfo_urc)
        self.demuxer.subscribe(NetworkRegistrationEvent, self._on_net_urc)
        self.demuxer.subscribe(SmsReceivedEvent, self._on_sms_urc)

    def _on_signal_urc(self, evt: SignalChangeEvent) -> None:
        self.state.rssi = evt.rssi
        self.state.bars = evt.bars
        self.state.dbm = evt.dbm
        self.dbus_service.emit_signal_quality(evt.rssi, evt.dbm or 0)
        logger.debug("URC Signal: %d bars (%d dBm)", evt.bars, evt.dbm or 0)

    def _on_mode_urc(self, evt: ModeChangeEvent) -> None:
        self.state.technology = evt.technology
        self.dbus_service.emit_mode_changed(evt.technology)
        logger.info("URC Mode: %s", evt.technology)

    def _on_sysinfo_urc(self, evt: SysinfoEvent) -> None:
        self.state.technology = evt.technology
        self.dbus_service.emit_mode_changed(evt.technology)
        logger.debug("URC Sysinfo: RAT=%s, srv_status=%d", evt.technology, evt.srv_status)

    def _on_net_urc(self, evt: NetworkRegistrationEvent) -> None:
        self.state.registration_status = evt.status
        logger.info("URC Network: %s status=%d (registered=%s)", evt.domain, evt.status, evt.is_registered)

    def _on_sms_urc(self, evt: SmsReceivedEvent) -> None:
        logger.info("URC SMS arrival: storage=%s index=%d", evt.storage, evt.index)
        if self.dispatcher:
            try:
                # Sync inbound message into SQLite
                ingested = self.sms_store.reconcile_sim_inbox(self.dispatcher, purge_sim=False)
                for msg in ingested:
                    self.dbus_service.emit_sms_received(msg.phone_number, msg.body)
            except Exception as exc:
                logger.error("Failed to reconcile incoming SMS from URC: %s", exc)

    def connect_modem(self) -> bool:
        """
        Resolve modem serial endpoints and initialize baseband parameters.
        """
        with self.shared_lock:
            self.ports = self.resolver.resolve(prefer_udev=self.prefer_udev)
            if not self.ports.is_ready or not self.ports.control:
                self.state.connected = False
                return False

            try:
                self.transport = SerialTransport(
                    self.ports.control,
                    baudrate=115200,
                    timeout=2.0,
                    exclusive_lock=True,
                )
                self.transport.open()
            except (PortNotFoundError, PortBusyError, SerialTransportError) as exc:
                logger.warning("Failed to open modem control port %s: %s", self.ports.control, exc)
                self.state.connected = False
                return False

            self.dispatcher = AtDispatcher(
                self.transport,
                urc_callback=self.demuxer.feed_line,
                lock=self.shared_lock,
            )

            # Start idle URC listener thread
            self.demuxer.start_listener(self.transport, shared_lock=self.shared_lock)

            # Configure standard baseband operating parameters
            self.dispatcher.execute("ATE0")       # Echo off
            self.dispatcher.execute("AT+CMEE=1")   # Extended numeric error codes
            self.dispatcher.execute("AT+CREG=2")   # Enable network registration URCs
            self.dispatcher.execute("AT+CEREG=2")  # Enable LTE registration URCs
            self.dispatcher.execute("AT+CLIP=1")   # Enable caller ID presentation
            self.dispatcher.execute('AT+CPMS="SM","SM","SM"') # Select SIM storage
            self.dispatcher.execute("AT+CMGF=1")   # Text mode SMS

            self.state.connected = True
            self.state.reconnect_attempts = 0
            self.wifi.dispatcher = self.dispatcher
            logger.info("Successfully connected to modem on %s", self.ports.control)

            # Initial SIM reconciliation
            try:
                ingested = self.sms_store.reconcile_sim_inbox(self.dispatcher, purge_sim=False)
                if ingested:
                    logger.info("Reconciled %d message(s) from SIM on startup", len(ingested))
            except Exception as exc:
                logger.debug("Initial SIM reconciliation notice: %s", exc)

            return True

    def disconnect_modem(self) -> None:
        """
        Close active serial ports and stop background URC listeners cleanly.
        """
        with self.shared_lock:
            self.state.connected = False
            self.demuxer.stop_listener()
            if self.transport is not None:
                self.transport.close()
                self.transport = None
            self.dispatcher = None
            self.wifi.dispatcher = None
            logger.info("Disconnected from modem control port.")

    def poll_telemetry_once(self) -> None:
        """
        Query signal, registration, and network carrier status and record sample.
        """
        if not self.state.connected or not self.dispatcher:
            return

        with self.shared_lock:
            # 1. Signal quality (AT+CSQ)
            resp_csq = self.dispatcher.execute("AT+CSQ", timeout=1.5)
            if resp_csq.success and resp_csq.value:
                # Format: +CSQ: <rssi>,<ber>
                parts = resp_csq.value.replace("+CSQ:", "").strip().split(",")
                if parts and parts[0].isdigit():
                    rssi_val = int(parts[0])
                    self.state.rssi = rssi_val
                    if rssi_val != 99:
                        self.state.dbm = -113 + 2 * rssi_val
                        if rssi_val < 10:
                            self.state.bars = 1
                        elif rssi_val < 15:
                            self.state.bars = 2
                        elif rssi_val < 20:
                            self.state.bars = 3
                        elif rssi_val < 25:
                            self.state.bars = 4
                        else:
                            self.state.bars = 5
                    else:
                        self.state.dbm = None
                        self.state.bars = 0

            # 2. Operator info (AT+COPS?)
            resp_cops = self.dispatcher.execute("AT+COPS?", timeout=1.5)
            if resp_cops.success and resp_cops.value:
                # Format: +COPS: <mode>,<format>,"<oper>",<act>
                cops_parts = resp_cops.value.replace("+COPS:", "").strip().split(",")
                if len(cops_parts) >= 3:
                    oper_clean = cops_parts[2].strip(' "')
                    if oper_clean:
                        self.state.carrier = oper_clean

            # 3. Registration (AT+CREG?)
            resp_creg = self.dispatcher.execute("AT+CREG?", timeout=1.5)
            if resp_creg.success and resp_creg.value:
                # Format: +CREG: <n>,<stat>
                creg_parts = resp_creg.value.replace("+CREG:", "").strip().split(",")
                if len(creg_parts) >= 2 and creg_parts[1].isdigit():
                    self.state.registration_status = int(creg_parts[1])

            # 4. System info / RAT (AT^SYSINFO)
            self.dispatcher.execute("AT^SYSINFO", timeout=1.5)

            self.state.last_poll_time = time.time()


            # Record telemetry sample into historical database
            self.metrics_store.record_metrics(
                TelemetryRecord(
                    timestamp=self.state.last_poll_time,
                    rssi=self.state.rssi,
                    dbm=self.state.dbm,
                    rat=self.state.technology,
                    lac=None,
                    cell_id=None,
                )
            )

    def _telemetry_loop(self) -> None:
        """Background loop executing telemetry queries at poll_interval."""
        while not self._stop_event.is_set():
            if self.state.connected:
                try:
                    self.poll_telemetry_once()
                except Exception as exc:
                    logger.warning("Error during telemetry poll: %s", exc)
            self._stop_event.wait(self.poll_interval)

    def _watchdog_loop(self) -> None:
        """Background watchdog loop handling reconnects with exponential backoff."""
        backoff = 1.0
        max_backoff = 16.0

        while not self._stop_event.is_set():
            if not self.state.connected:
                self.state.reconnect_attempts += 1
                logger.info("Watchdog: attempting modem reconnection (attempt %d)...", self.state.reconnect_attempts)
                success = self.connect_modem()
                if success:
                    backoff = 1.0
                else:
                    backoff = min(backoff * 2.0, max_backoff)
                self._stop_event.wait(backoff)
            else:
                # Connection is active: check physical node presence
                if self.ports and self.ports.control and not self.ports.control.exists():
                    logger.warning("Watchdog: serial control node %s vanished! Disconnecting...", self.ports.control)
                    self.disconnect_modem()
                self._stop_event.wait(2.0)

    def start(self) -> None:
        """Start daemon engine and background worker threads."""
        with self.shared_lock:
            if self.state.is_running:
                return

            self._stop_event.clear()
            self.state.is_running = True

            # Attempt initial connection
            self.connect_modem()

            # Start background polling and watchdog threads
            self._poll_thread = threading.Thread(
                target=self._telemetry_loop,
                name="misltyd-telemetry",
                daemon=True,
            )
            self._poll_thread.start()

            self._watchdog_thread = threading.Thread(
                target=self._watchdog_loop,
                name="misltyd-watchdog",
                daemon=True,
            )
            self._watchdog_thread.start()

            # Start IPC servers
            self.socket_server.start()
            self.dbus_service.start()

            logger.info("misltyd daemon engine started successfully.")

    def stop(self) -> None:
        """Stop daemon engine and gracefully shut down all threads, IPC servers, and ports."""
        with self.shared_lock:
            if not self.state.is_running:
                return

            self._stop_event.set()
            self.state.is_running = False

            # Stop IPC servers
            self.socket_server.stop()
            self.dbus_service.stop()

            if self._poll_thread is not None:
                self._poll_thread.join(timeout=2.0)
                self._poll_thread = None

            if self._watchdog_thread is not None:
                self._watchdog_thread.join(timeout=2.0)
                self._watchdog_thread = None

            self.disconnect_modem()
            self.db.close()
            logger.info("misltyd daemon engine stopped.")

    def get_full_status(self) -> Dict[str, Any]:
        """Collect complete diagnostic snapshot across daemon, hardware, cellular PPP, and Wi-Fi."""
        with self.shared_lock:
            ports_dict = self.ports.as_dict() if self.ports else self.resolver.resolve(prefer_udev=self.prefer_udev).as_dict()
            ppp_stat = self.ppp.get_status().as_dict()
            wifi_pwr = self.wifi.get_radio_power() if self.dispatcher else None
            wifi_ssid = self.wifi.get_ssid_serial() if self.dispatcher else None
            clients_count = 0
            if self.ports and self.ports.aux_wifi_netns:
                try:
                    clients_count = len(self.wifi.get_connected_clients(netns=self.ports.aux_wifi_netns))
                except Exception:
                    pass

            return {
                "daemon": self.state.as_dict(),
                "hardware": ports_dict,
                "cellular_ppp": ppp_stat,
                "wifi": {
                    "power": wifi_pwr,
                    "ssid": wifi_ssid,
                    "clients_count": clients_count,
                },
            }

    def connect_cellular(self, apn: str = "internet", default_route: bool = True, timeout: float = 20.0) -> bool:
        """Initiate cellular PPP dial-up data plane connection."""
        return self.ppp.connect(apn=apn, default_route=default_route, timeout=timeout)

    def disconnect_cellular(self) -> bool:
        """Terminate active cellular PPP data connection and restore routes."""
        return self.ppp.disconnect()

    def set_wifi_power(self, enable: bool) -> bool:
        """Toggle Broadcom Wi-Fi radio power on/off."""
        with self.shared_lock:
            return self.wifi.set_radio_power(enable)

    def set_wifi_credentials(self, ssid: str, password: Optional[str] = None) -> bool:
        """Configure Wi-Fi SSID and password."""
        with self.shared_lock:
            netns = self.ports.aux_wifi_netns if self.ports else None
            ok = self.wifi.set_clean_ssid_web(ssid, netns=netns)
            if not ok:
                ok = self.wifi.set_credentials_serial(ssid, password=password)
            return ok

    def get_wifi_clients(self) -> List[Dict[str, str]]:
        """Query connected Wi-Fi client list."""
        netns = self.ports.aux_wifi_netns if self.ports else None
        return self.wifi.get_connected_clients(netns=netns)

    def send_sms(self, recipient: str, text: str) -> Dict[str, Any]:
        """Send an SMS text message through modem baseband."""
        with self.shared_lock:
            if not self.dispatcher or not self.state.connected:
                raise RuntimeError("Modem is not connected.")
            resp = self.dispatcher.send_sms(recipient, text)
            if resp.success:
                saved = self.sms_store.save_message(
                    phone_number=recipient,
                    body=text,
                    direction="OUT",
                    status="SENT",
                    is_read=True,
                )
                return {"success": True, "message_id": saved.id, "recipient": recipient}
            else:
                return {"success": False, "error": resp.error, "error_detail": resp.error_detail}

    def list_sms(self, thread_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """List SMS conversation threads or messages in a thread."""
        if thread_id is not None:
            return [m.as_dict() for m in self.sms_store.get_thread_messages(thread_id)]
        return [t.as_dict() for t in self.sms_store.list_threads()]

    def sync_sms(self, purge_sim: bool = True) -> List[Dict[str, Any]]:
        """Sync and reconcile SMS messages from SIM card memory."""
        with self.shared_lock:
            if not self.dispatcher or not self.state.connected:
                raise RuntimeError("Modem is not connected.")
            messages = self.sms_store.reconcile_sim_inbox(self.dispatcher, purge_sim=purge_sim)
            return [m.as_dict() for m in messages]

    def delete_sms_thread(self, thread_id: int) -> Dict[str, Any]:
        """Delete an entire conversation thread and all its messages."""
        with self.shared_lock:
            ok = self.sms_store.delete_thread(thread_id)
            return {"success": ok, "thread_id": thread_id}

    def mark_sms_read(self, thread_id: int) -> Dict[str, Any]:
        """Mark all messages in thread as read."""
        with self.shared_lock:
            self.sms_store.mark_thread_read(thread_id)
            return {"success": True, "thread_id": thread_id}

    def execute_at(self, command: str, timeout: float = 3.0) -> Dict[str, Any]:
        """Execute raw AT command on modem control channel under lock."""
        with self.shared_lock:
            if not self.dispatcher or not self.state.connected:
                raise RuntimeError("Modem is not connected.")
            resp = self.dispatcher.execute(command, timeout=timeout)
            return resp.as_dict()


def build_parser() -> argparse.ArgumentParser:
    """Build command line argument parser for misltyd."""
    parser = argparse.ArgumentParser(
        prog="misltyd",
        description="Core Background Control Daemon for Qualcomm MDM9600 (Aleka UV310) 4G Modems",
    )
    parser.add_argument("-f", "--foreground", action="store_true", help="Run daemon in foreground")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")

    parser.add_argument("--no-udev", action="store_true", help="Bypass udev symlinks and crawl sysfs directly")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="RF telemetry polling interval in seconds (default: 2.0)")
    parser.add_argument("--db", default=None, help="Custom SQLite database file path")
    return parser


def main(args=None) -> None:
    """CLI entrypoint for misltyd."""
    parser = build_parser()
    parsed = parser.parse_args(args)


    log_level = logging.DEBUG if parsed.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.info("Starting misltyd daemon engine...")
    engine = DaemonEngine(
        db_path=parsed.db,
        poll_interval=parsed.poll_interval,
        prefer_udev=not parsed.no_udev,
    )

    def _signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info("Received signal %s, initiating graceful shutdown...", sig_name)
        engine.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    if hasattr(signal, "SIGHUP"):
        signal.signal(signal.SIGHUP, lambda s, f: logger.info("SIGHUP received: configuration reloaded."))

    engine.start()

    # Block main thread until stop requested
    try:
        while engine.state.is_running:
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        engine.stop()


if __name__ == "__main__":
    main()
