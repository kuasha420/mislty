"""
mislty.gui.app
~~~~~~~~~~~~~~

PySide6 / QML Application Host and MisltyBridge for the MisLTy Desktop Suite.
Connects QML UI decks to MisltyClient IPC and hardware subsystems with
reactive property bindings, background telemetry polling, and smooth feline UI tokens.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    Property,
    QObject,
    QTimer,
    QUrl,
    Signal,
    Slot,
)
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine

from mislty.audio.pcm_bridge import TelephonyEngine, play_dtmf_tone, TRAGIC_VOICE_LORE
from mislty.core.sms import calculate_sms_segments, send_desktop_notification
from mislty.ipc.client import MisltyClient

logger = logging.getLogger("mislty.gui")


class MisltyBridge(QObject):
    """
    QObject Bridge communicating between QML UI layers and the MisLTy
    daemon / client IPC backend.
    """

    # Property Change Notification Signals
    connectedChanged = Signal(bool)
    connectingChanged = Signal(bool)
    operatorChanged = Signal(str)
    technologyChanged = Signal(str)
    signalBarsChanged = Signal(int)
    signalCsqChanged = Signal(int)
    signalDbmChanged = Signal(int)
    wifiPowerChanged = Signal(bool)
    wifiSsidChanged = Signal(str)
    wifiClientsCountChanged = Signal(int)
    rxBytesChanged = Signal(int)
    txBytesChanged = Signal(int)
    rxRateChanged = Signal(float)
    txRateChanged = Signal(float)
    ipAddressChanged = Signal(str)
    sessionDurationChanged = Signal(int)
    activeDeckChanged = Signal(int)
    isDaemonRunningChanged = Signal(bool)
    transportModeChanged = Signal(str)
    statusMessageChanged = Signal(str)
    dnsServersChanged = Signal(list)
    peerIpChanged = Signal(str)
    trafficHistoryRxChanged = Signal(list)
    trafficHistoryTxChanged = Signal(list)
    peakRxRateChanged = Signal(float)
    peakTxRateChanged = Signal(float)
    wifiStationsChanged = Signal(list)
    operationalModeChanged = Signal(str)
    isSwitchingModeChanged = Signal(bool)
    smsThreadsChanged = Signal(list)
    smsMessagesChanged = Signal(list)
    smsReceived = Signal(str, str)
    callStateChanged = Signal(str)
    activeCallNumberChanged = Signal(str)
    callDurationChanged = Signal(int)
    tragicVoiceVisibleChanged = Signal(bool)
    tragicVoiceTriggered = Signal("QVariant")
    wlanDevicesChanged = Signal(list)
    relayActiveChanged = Signal(bool)
    relayInterfaceChanged = Signal(str)
    relaySsidChanged = Signal(str)
    relayIpAddressChanged = Signal(str)
    relayUptimeChanged = Signal(int)
    relayClientsChanged = Signal(list)
    relayWanInterfaceChanged = Signal(str)
    relayBusyChanged = Signal(bool)
    relayErrorChanged = Signal(str)
    isScanningDevicesChanged = Signal(bool)

    def __init__(
        self,
        client: Optional[MisltyClient] = None,
        qcwebs_client: Optional[Any] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._client: MisltyClient = client if client is not None else MisltyClient()
        self._poll_timer: Optional[QTimer] = None
        self._poll_lock = threading.Lock()

        # Telemetry State Properties
        self._connected: bool = False
        self._connecting: bool = False
        self._operator: str = "Searching..."
        self._technology: str = "4G LTE"
        self._signal_bars: int = 0
        self._signal_csq: int = 0
        self._signal_dbm: int = -113
        self._wifi_power: bool = False
        self._wifi_ssid: str = ""
        self._wifi_clients_count: int = 0
        self._rx_bytes: int = 0
        self._tx_bytes: int = 0
        self._rx_rate: float = 0.0
        self._tx_rate: float = 0.0
        self._ip_address: str = ""
        self._session_duration: int = 0
        self._active_deck: int = 0
        self._is_daemon_running: bool = False
        self._transport_mode: str = self._client.active_transport
        self._status_message: str = "Ready"
        self._dns_servers: List[str] = []
        self._peer_ip: str = ""
        self._traffic_history_rx: List[float] = [0.0] * 24
        self._traffic_history_tx: List[float] = [0.0] * 24
        self._peak_rx_rate: float = 0.0
        self._peak_tx_rate: float = 0.0
        self._wifi_stations: List[Dict[str, Any]] = []
        self._operational_mode: str = "usb_modem"
        self._is_switching_mode: bool = False
        self._sms_threads: List[Dict[str, Any]] = []
        self._sms_messages: List[Dict[str, Any]] = []
        self._wlan_devices: List[Dict[str, Any]] = []
        self._relay_active: bool = False
        self._relay_interface: str = "wlan1"
        self._relay_ssid: str = "MisLTy 4G Share"
        self._relay_ip_address: str = "10.42.0.1"
        self._relay_uptime: int = 0
        self._relay_clients: List[Dict[str, Any]] = []
        self._relay_wan_interface: str = "ppp0"
        self._relay_busy: bool = False
        self._relay_error: str = ""
        self._is_scanning_devices: bool = False

        # QC-Webs Embedded Client and Mode Switcher
        from mislty.net.qcwebs_client import QcWebsClient, SmartModeSwitcher
        if qcwebs_client is not None:
            self._qcwebs = qcwebs_client
        else:
            aux_netns = self._get_aux_netns()
            self._qcwebs = QcWebsClient(netns=aux_netns)
        self._mode_switcher = SmartModeSwitcher(qcwebs_client=self._qcwebs)

        # Telephony Engine State
        self._call_state: str = "IDLE"
        self._active_call_number: str = ""
        self._call_duration: int = 0
        self._tragic_voice_visible: bool = False
        self._telephony = TelephonyEngine(
            on_state_change=self._on_call_state_change,
            on_tragic_voice=self._on_tragic_voice,
        )

        # Internal Rate Tracking State
        self._last_poll_time: float = 0.0
        self._last_rx_bytes: int = 0
        self._last_tx_bytes: int = 0
        self._connected_start_time: float = 0.0

        # Perform initial synchronous status check
        try:
            self._update_status_data(self._client.get_status())
            self.refreshWlanDevices()
        except Exception as exc:
            logger.debug("Initial status probe failed: %s", exc)

    # -----------------------------------------------------------------------
    # QML Properties
    # -----------------------------------------------------------------------

    @Property(bool, notify=connectedChanged)
    def connected(self) -> bool:
        return self._connected

    @connected.setter
    def connected(self, value: bool) -> None:
        if self._connected != value:
            self._connected = value
            self.connectedChanged.emit(value)

    @Property(bool, notify=connectingChanged)
    def connecting(self) -> bool:
        return self._connecting

    @connecting.setter
    def connecting(self, value: bool) -> None:
        if self._connecting != value:
            self._connecting = value
            self.connectingChanged.emit(value)

    @Property(str, notify=operatorChanged)
    def operator(self) -> str:
        return self._operator

    @operator.setter
    def operator(self, value: str) -> None:
        if self._operator != value:
            self._operator = value
            self.operatorChanged.emit(value)

    @Property(str, notify=technologyChanged)
    def technology(self) -> str:
        return self._technology

    @technology.setter
    def technology(self, value: str) -> None:
        if self._technology != value:
            self._technology = value
            self.technologyChanged.emit(value)

    @Property(int, notify=signalBarsChanged)
    def signalBars(self) -> int:
        return self._signal_bars

    @signalBars.setter
    def signalBars(self, value: int) -> None:
        if self._signal_bars != value:
            self._signal_bars = value
            self.signalBarsChanged.emit(value)

    @Property(int, notify=signalCsqChanged)
    def signalCsq(self) -> int:
        return self._signal_csq

    @signalCsq.setter
    def signalCsq(self, value: int) -> None:
        if self._signal_csq != value:
            self._signal_csq = value
            self.signalCsqChanged.emit(value)

    @Property(int, notify=signalDbmChanged)
    def signalDbm(self) -> int:
        return self._signal_dbm

    @signalDbm.setter
    def signalDbm(self, value: int) -> None:
        if self._signal_dbm != value:
            self._signal_dbm = value
            self.signalDbmChanged.emit(value)

    @Property(bool, notify=wifiPowerChanged)
    def wifiPower(self) -> bool:
        return self._wifi_power

    @wifiPower.setter
    def wifiPower(self, value: bool) -> None:
        if self._wifi_power != value:
            self._wifi_power = value
            self.wifiPowerChanged.emit(value)

    @Property(str, notify=wifiSsidChanged)
    def wifiSsid(self) -> str:
        return self._wifi_ssid

    @wifiSsid.setter
    def wifiSsid(self, value: str) -> None:
        if self._wifi_ssid != value:
            self._wifi_ssid = value
            self.wifiSsidChanged.emit(value)

    @Property(int, notify=wifiClientsCountChanged)
    def wifiClientsCount(self) -> int:
        return self._wifi_clients_count

    @wifiClientsCount.setter
    def wifiClientsCount(self, value: int) -> None:
        if self._wifi_clients_count != value:
            self._wifi_clients_count = value
            self.wifiClientsCountChanged.emit(value)

    @Property(int, notify=rxBytesChanged)
    def rxBytes(self) -> int:
        return self._rx_bytes

    @rxBytes.setter
    def rxBytes(self, value: int) -> None:
        if self._rx_bytes != value:
            self._rx_bytes = value
            self.rxBytesChanged.emit(value)

    @Property(int, notify=txBytesChanged)
    def txBytes(self) -> int:
        return self._tx_bytes

    @txBytes.setter
    def txBytes(self, value: int) -> None:
        if self._tx_bytes != value:
            self._tx_bytes = value
            self.txBytesChanged.emit(value)

    @Property(float, notify=rxRateChanged)
    def rxRate(self) -> float:
        return self._rx_rate

    @rxRate.setter
    def rxRate(self, value: float) -> None:
        if self._rx_rate != value:
            self._rx_rate = value
            self.rxRateChanged.emit(value)

    @Property(float, notify=txRateChanged)
    def txRate(self) -> float:
        return self._tx_rate

    @txRate.setter
    def txRate(self, value: float) -> None:
        if self._tx_rate != value:
            self._tx_rate = value
            self.txRateChanged.emit(value)

    @Property(str, notify=ipAddressChanged)
    def ipAddress(self) -> str:
        return self._ip_address

    @ipAddress.setter
    def ipAddress(self, value: str) -> None:
        if self._ip_address != value:
            self._ip_address = value
            self.ipAddressChanged.emit(value)

    @Property(int, notify=sessionDurationChanged)
    def sessionDuration(self) -> int:
        return self._session_duration

    @sessionDuration.setter
    def sessionDuration(self, value: int) -> None:
        if self._session_duration != value:
            self._session_duration = value
            self.sessionDurationChanged.emit(value)

    @Property(int, notify=activeDeckChanged)
    def activeDeck(self) -> int:
        return self._active_deck

    @activeDeck.setter
    def activeDeck(self, value: int) -> None:
        if self._active_deck != value:
            self._active_deck = value
            self.activeDeckChanged.emit(value)

    @Property(bool, notify=isDaemonRunningChanged)
    def isDaemonRunning(self) -> bool:
        return self._is_daemon_running

    @isDaemonRunning.setter
    def isDaemonRunning(self, value: bool) -> None:
        if self._is_daemon_running != value:
            self._is_daemon_running = value
            self.isDaemonRunningChanged.emit(value)

    @Property(str, notify=transportModeChanged)
    def transportMode(self) -> str:
        return self._transport_mode

    @transportMode.setter
    def transportMode(self, value: str) -> None:
        if self._transport_mode != value:
            self._transport_mode = value
            self.transportModeChanged.emit(value)

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @statusMessage.setter
    def statusMessage(self, value: str) -> None:
        if self._status_message != value:
            self._status_message = value
            self.statusMessageChanged.emit(value)

    @Property(list, notify=smsThreadsChanged)
    def smsThreads(self) -> list:
        return self._sms_threads

    @smsThreads.setter
    def smsThreads(self, value: list) -> None:
        if self._sms_threads != value:
            self._sms_threads = value
            self.smsThreadsChanged.emit(value)

    @Property(list, notify=smsMessagesChanged)
    def smsMessages(self) -> list:
        return self._sms_messages

    @smsMessages.setter
    def smsMessages(self, value: list) -> None:
        if self._sms_messages != value:
            self._sms_messages = value
            self.smsMessagesChanged.emit(value)

    @Property(list, notify=dnsServersChanged)
    def dnsServers(self) -> list:
        return self._dns_servers

    @dnsServers.setter
    def dnsServers(self, value: list) -> None:
        if self._dns_servers != value:
            self._dns_servers = value
            self.dnsServersChanged.emit(value)

    @Property(str, notify=peerIpChanged)
    def peerIp(self) -> str:
        return self._peer_ip

    @peerIp.setter
    def peerIp(self, value: str) -> None:
        if self._peer_ip != value:
            self._peer_ip = value
            self.peerIpChanged.emit(value)

    @Property(list, notify=trafficHistoryRxChanged)
    def trafficHistoryRx(self) -> list:
        return self._traffic_history_rx

    @trafficHistoryRx.setter
    def trafficHistoryRx(self, value: list) -> None:
        if self._traffic_history_rx != value:
            self._traffic_history_rx = value
            self.trafficHistoryRxChanged.emit(value)

    @Property(list, notify=trafficHistoryTxChanged)
    def trafficHistoryTx(self) -> list:
        return self._traffic_history_tx

    @trafficHistoryTx.setter
    def trafficHistoryTx(self, value: list) -> None:
        if self._traffic_history_tx != value:
            self._traffic_history_tx = value
            self.trafficHistoryTxChanged.emit(value)

    @Property(float, notify=peakRxRateChanged)
    def peakRxRate(self) -> float:
        return self._peak_rx_rate

    @peakRxRate.setter
    def peakRxRate(self, value: float) -> None:
        if self._peak_rx_rate != value:
            self._peak_rx_rate = value
            self.peakRxRateChanged.emit(value)

    @Property(float, notify=peakTxRateChanged)
    def peakTxRate(self) -> float:
        return self._peak_tx_rate

    @peakTxRate.setter
    def peakTxRate(self, value: float) -> None:
        if self._peak_tx_rate != value:
            self._peak_tx_rate = value
            self.peakTxRateChanged.emit(value)

    @Property(list, notify=wifiStationsChanged)
    def wifiStations(self) -> list:
        return self._wifi_stations

    @wifiStations.setter
    def wifiStations(self, value: list) -> None:
        if self._wifi_stations != value:
            self._wifi_stations = value
            self.wifiStationsChanged.emit(value)

    @Property(str, notify=operationalModeChanged)
    def operationalMode(self) -> str:
        return self._operational_mode

    @operationalMode.setter
    def operationalMode(self, value: str) -> None:
        if self._operational_mode != value:
            self._operational_mode = value
            self.operationalModeChanged.emit(value)

    @Property(bool, notify=isSwitchingModeChanged)
    def isSwitchingMode(self) -> bool:
        return self._is_switching_mode

    @isSwitchingMode.setter
    def isSwitchingMode(self, value: bool) -> None:
        if self._is_switching_mode != value:
            self._is_switching_mode = value
            self.isSwitchingModeChanged.emit(value)

    @Property(str, notify=callStateChanged)
    def callState(self) -> str:
        return self._call_state

    @callState.setter
    def callState(self, value: str) -> None:
        if self._call_state != value:
            self._call_state = value
            self.callStateChanged.emit(value)

    @Property(str, notify=activeCallNumberChanged)
    def activeCallNumber(self) -> str:
        return self._active_call_number

    @activeCallNumber.setter
    def activeCallNumber(self, value: str) -> None:
        if self._active_call_number != value:
            self._active_call_number = value
            self.activeCallNumberChanged.emit(value)

    @Property(int, notify=callDurationChanged)
    def callDuration(self) -> int:
        return self._call_duration

    @callDuration.setter
    def callDuration(self, value: int) -> None:
        if self._call_duration != value:
            self._call_duration = value
            self.callDurationChanged.emit(value)

    @Property(bool, notify=tragicVoiceVisibleChanged)
    def tragicVoiceVisible(self) -> bool:
        return self._tragic_voice_visible

    @tragicVoiceVisible.setter
    def tragicVoiceVisible(self, value: bool) -> None:
        if self._tragic_voice_visible != value:
            self._tragic_voice_visible = value
            self.tragicVoiceVisibleChanged.emit(value)

    @Property(list, notify=wlanDevicesChanged)
    def wlanDevices(self) -> list:
        return self._wlan_devices

    @wlanDevices.setter
    def wlanDevices(self, value: list) -> None:
        if self._wlan_devices != value:
            self._wlan_devices = value
            self.wlanDevicesChanged.emit(value)

    @Property(bool, notify=relayActiveChanged)
    def relayActive(self) -> bool:
        return self._relay_active

    @relayActive.setter
    def relayActive(self, value: bool) -> None:
        if self._relay_active != value:
            self._relay_active = value
            self.relayActiveChanged.emit(value)

    @Property(str, notify=relayInterfaceChanged)
    def relayInterface(self) -> str:
        return self._relay_interface

    @relayInterface.setter
    def relayInterface(self, value: str) -> None:
        if self._relay_interface != value:
            self._relay_interface = value
            self.relayInterfaceChanged.emit(value)

    @Property(str, notify=relaySsidChanged)
    def relaySsid(self) -> str:
        return self._relay_ssid

    @relaySsid.setter
    def relaySsid(self, value: str) -> None:
        if self._relay_ssid != value:
            self._relay_ssid = value
            self.relaySsidChanged.emit(value)

    @Property(str, notify=relayIpAddressChanged)
    def relayIpAddress(self) -> str:
        return self._relay_ip_address

    @relayIpAddress.setter
    def relayIpAddress(self, value: str) -> None:
        if self._relay_ip_address != value:
            self._relay_ip_address = value
            self.relayIpAddressChanged.emit(value)

    @Property(int, notify=relayUptimeChanged)
    def relayUptime(self) -> int:
        return self._relay_uptime

    @relayUptime.setter
    def relayUptime(self, value: int) -> None:
        if self._relay_uptime != value:
            self._relay_uptime = value
            self.relayUptimeChanged.emit(value)

    @Property(list, notify=relayClientsChanged)
    def relayClients(self) -> list:
        return self._relay_clients

    @relayClients.setter
    def relayClients(self, value: list) -> None:
        if self._relay_clients != value:
            self._relay_clients = value
            self.relayClientsChanged.emit(value)

    @Property(str, notify=relayWanInterfaceChanged)
    def relayWanInterface(self) -> str:
        return self._relay_wan_interface

    @relayWanInterface.setter
    def relayWanInterface(self, value: str) -> None:
        if self._relay_wan_interface != value:
            self._relay_wan_interface = value
            self.relayWanInterfaceChanged.emit(value)

    @Property(bool, notify=relayBusyChanged)
    def relayBusy(self) -> bool:
        return self._relay_busy

    @relayBusy.setter
    def relayBusy(self, value: bool) -> None:
        if self._relay_busy != value:
            self._relay_busy = value
            self.relayBusyChanged.emit(value)

    @Property(str, notify=relayErrorChanged)
    def relayError(self) -> str:
        return self._relay_error

    @relayError.setter
    def relayError(self, value: str) -> None:
        if self._relay_error != value:
            self._relay_error = value
            self.relayErrorChanged.emit(value)

    @Property(bool, notify=isScanningDevicesChanged)
    def isScanningDevices(self) -> bool:
        return self._is_scanning_devices

    @isScanningDevices.setter
    def isScanningDevices(self, value: bool) -> None:
        if self._is_scanning_devices != value:
            self._is_scanning_devices = value
            self.isScanningDevicesChanged.emit(value)

    def _get_aux_netns(self) -> Optional[str]:
        """Detect if auxiliary Wi-Fi interface is configured in an isolated network namespace."""
        from mislty.core.port_resolver import PortResolver
        try:
            ports = PortResolver().resolve()
            return ports.aux_wifi_netns
        except Exception:
            return None

    # -----------------------------------------------------------------------
    # Status Ingestion & Telemetry Processing
    # -----------------------------------------------------------------------

    def _update_status_data(self, stat: Dict[str, Any]) -> None:
        """Parse status dictionary and update reactive properties."""
        daemon = stat.get("daemon", {})
        cellular = stat.get("cellular_ppp", {})
        wifi = stat.get("wifi", {})

        is_connected = bool(cellular.get("connected", cellular.get("is_connected", False)))
        self.connected = is_connected
        self.isDaemonRunning = bool(daemon.get("is_running", False))
        self.transportMode = self._client.active_transport

        # Cellular details
        ip = cellular.get("ip_address") or ""
        self.ipAddress = ip
        self.peerIp = cellular.get("peer_ip") or ""
        self.dnsServers = cellular.get("dns_servers") or []

        # Carrier & RF Signal
        csq = daemon.get("rssi") or 0
        dbm = daemon.get("dbm") or (-113 + (csq * 2) if csq > 0 and csq != 99 else -113)
        bars = daemon.get("bars") or 0
        carrier = daemon.get("carrier") or ("Active Network" if is_connected else "Searching Carrier...")
        tech = daemon.get("technology") or "4G LTE"

        self.signalCsq = csq
        self.signalDbm = dbm
        self.signalBars = bars
        self.operator = carrier
        self.technology = tech

        # Wi-Fi details
        self.wifiPower = bool(wifi.get("power", False))
        self.wifiSsid = wifi.get("ssid") or ""
        self.wifiClientsCount = wifi.get("clients_count") or 0

        # Throughput & Traffic Rates
        now = time.time()
        rx = cellular.get("rx_bytes") or 0
        tx = cellular.get("tx_bytes") or 0

        if self._last_poll_time > 0 and is_connected:
            dt = now - self._last_poll_time
            if dt > 0:
                delta_rx = max(0, rx - self._last_rx_bytes)
                delta_tx = max(0, tx - self._last_tx_bytes)
                self.rxRate = delta_rx / dt
                self.txRate = delta_tx / dt
        else:
            self.rxRate = 0.0
            self.txRate = 0.0

        if self.rxRate > self.peakRxRate:
            self.peakRxRate = self.rxRate
        if self.txRate > self.peakTxRate:
            self.peakTxRate = self.txRate

        # Append to sparkline traffic history (in KB/s)
        self._traffic_history_rx.append(self.rxRate / 1024.0)
        if len(self._traffic_history_rx) > 24:
            self._traffic_history_rx.pop(0)
        self.trafficHistoryRx = list(self._traffic_history_rx)

        self._traffic_history_tx.append(self.txRate / 1024.0)
        if len(self._traffic_history_tx) > 24:
            self._traffic_history_tx.pop(0)
        self.trafficHistoryTx = list(self._traffic_history_tx)

        self._last_poll_time = now
        self._last_rx_bytes = rx
        self._last_tx_bytes = tx
        self.rxBytes = rx
        self.txBytes = tx

        # Session Uptime Duration
        uptime = cellular.get("uptime_seconds", 0)
        if is_connected and uptime > 0:
            self.sessionDuration = int(uptime)
        elif is_connected:
            if self._connected_start_time == 0.0:
                self._connected_start_time = now
            self.sessionDuration = int(now - self._connected_start_time)
        else:
            self._connected_start_time = 0.0
            self.sessionDuration = 0

        # Wi-Fi Relay details
        relay = stat.get("wifi_relay", {})
        self.relayActive = bool(relay.get("active", False))
        if relay.get("interface"):
            self.relayInterface = relay.get("interface")
        if relay.get("ssid"):
            self.relaySsid = relay.get("ssid")
        if relay.get("ip_address"):
            self.relayIpAddress = relay.get("ip_address")
        self.relayUptime = int(relay.get("uptime_seconds", 0))
        if relay.get("wan_iface"):
            self.relayWanInterface = relay.get("wan_iface")

    # -----------------------------------------------------------------------
    # Public Invokable Slots
    # -----------------------------------------------------------------------

    @Slot(result=list)
    def refreshWlanDevices(self) -> list:
        """Enumerate host WLAN devices and update wlanDevices property."""
        self.isScanningDevices = True

        def _worker():
            try:
                devs = self._client.list_wlan_devices()
                self.wlanDevices = devs
            except Exception as exc:
                logger.debug("Failed to list WLAN devices: %s", exc)
            finally:
                self.isScanningDevices = False

        threading.Thread(target=_worker, daemon=True).start()
        return self._wlan_devices

    @Slot(str, str, str, str, int, str, result=bool)
    def startHotspotRelay(
        self,
        interface: str = "wlan1",
        ssid: str = "MisLTy 4G Share",
        password: str = "mislty420",
        band: str = "bg",
        channel: int = 11,
        wan_iface: str = "ppp0",
    ) -> bool:
        """Start assist softAP and route via cellular modem WAN."""
        self.relayBusy = True
        self.relayError = ""
        self.statusMessage = f"Starting Hotspot Relay on {interface}..."

        def _worker():
            try:
                res = self._client.start_hotspot_relay(
                    interface=interface,
                    ssid=ssid,
                    password=password if password else None,
                    band=band,
                    channel=channel,
                    wan_iface=wan_iface,
                )
                if res.get("active"):
                    self.statusMessage = f"Hotspot Relay ACTIVE on {interface} ({ssid})"
                    self.relayActive = True
                    self.relayInterface = interface
                    self.relaySsid = ssid
                    self.relayIpAddress = res.get("ip_address", "10.42.0.1")
                    self.relayError = ""
                else:
                    err = res.get("error", "Activation failed")
                    self.relayActive = False
                    self.relayError = err
                    self.statusMessage = f"Failed to start Hotspot Relay: {err}"
            except Exception as exc:
                logger.error("startHotspotRelay error: %s", exc)
                self.relayActive = False
                self.relayError = str(exc)
                self.statusMessage = f"Relay error: {exc}"
            finally:
                self.relayBusy = False

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(result=bool)
    def stopHotspotRelay(self) -> bool:
        """Deactivate assist hotspot and restore clean network routing."""
        self.relayBusy = True
        self.relayError = ""
        self.statusMessage = "Stopping Hotspot Relay..."

        def _worker():
            try:
                self._client.stop_hotspot_relay()
                self.relayActive = False
                self.relayError = ""
                self.statusMessage = "Hotspot Relay stopped."
            except Exception as exc:
                logger.error("stopHotspotRelay error: %s", exc)
                self.relayError = str(exc)
                self.statusMessage = f"Stop relay error: {exc}"
            finally:
                self.relayBusy = False

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(result=list)
    def getHotspotRelayClients(self) -> list:
        """Query stations associated with assist hotspot."""
        def _worker():
            try:
                clients = self._client.get_hotspot_relay_clients()
                self.relayClients = clients
            except Exception as exc:
                logger.debug("Failed to get hotspot relay clients: %s", exc)

        threading.Thread(target=_worker, daemon=True).start()
        return self._relay_clients

    @Slot(int)
    def setActiveDeck(self, deck: int) -> None:
        """Switch active UI deck."""
        self.activeDeck = deck

    @Slot()
    def refreshStatus(self) -> None:
        """Trigger asynchronous status refresh."""
        def _worker():
            if not self._poll_lock.acquire(blocking=False):
                return
            try:
                stat = self._client.get_status()
                self._update_status_data(stat)
            except Exception as exc:
                logger.debug("Status poll failed: %s", exc)
            finally:
                self._poll_lock.release()

        threading.Thread(target=_worker, daemon=True).start()

    @Slot(str, result=bool)
    @Slot(result=bool)
    def connectData(self, apn: str = "internet") -> bool:
        """Initiate cellular data connection in background worker thread."""
        self.connecting = True
        self.statusMessage = f"Connecting cellular data via APN '{apn}'..."

        def _worker():
            try:
                res = self._client.connect(apn=apn, default_route=True, timeout=20.0)
                success = res.get("success", False)
                self.statusMessage = "Connected successfully." if success else "Connection failed."
            except Exception as exc:
                logger.error("Data connection failed: %s", exc)
                self.statusMessage = f"Connection error: {exc}"
            finally:
                self.connecting = False
                try:
                    self._update_status_data(self._client.get_status())
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(result=bool)
    def disconnectData(self) -> bool:
        """Terminate cellular data connection."""
        self.connecting = True
        self.statusMessage = "Disconnecting cellular session..."

        def _worker():
            try:
                self._client.disconnect()
                self.statusMessage = "Disconnected."
            except Exception as exc:
                logger.error("Data disconnect failed: %s", exc)
                self.statusMessage = f"Disconnect error: {exc}"
            finally:
                self.connecting = False
                try:
                    self._update_status_data(self._client.get_status())
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(result=bool)
    def toggleWifi(self) -> bool:
        """Toggle Broadcom Wi-Fi radio power."""
        new_power = not self._wifi_power
        self.setWifiPower(new_power)
        return new_power

    @Slot(bool, result=bool)
    def setWifiPower(self, enable: bool) -> bool:
        """Set Broadcom Wi-Fi radio power state."""
        def _worker():
            try:
                res = self._client.set_wifi_power(enable)
                if res.get("success"):
                    self.wifiPower = enable
            except Exception as exc:
                logger.error("Failed to set Wi-Fi power: %s", exc)

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(str, str, result=bool)
    def setWifiCredentials(self, ssid: str, password: str) -> bool:
        """Configure Wi-Fi SSID and WPA2 security passphrase."""
        def _worker():
            try:
                res = self._client.set_wifi_credentials(ssid, password)
                if res.get("success"):
                    self.wifiSsid = ssid
                    self.statusMessage = f"Wi-Fi credentials updated: {ssid}"
            except Exception as exc:
                logger.error("Failed to set Wi-Fi credentials: %s", exc)
                self.statusMessage = f"Wi-Fi config error: {exc}"

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(str, str, int, result=bool)
    @Slot(str, str, result=bool)
    def saveWifiConfig(self, ssid: str, password: str, channel: int = 11) -> bool:
        """Configure clean SSID and WPA2 passphrase via QC-Webs and commit to NVRAM."""
        def _worker():
            try:
                ok_basic = self._qcwebs.set_wifi_basic(ssid=ssid, channel=channel)
                ok_sec = True
                if password:
                    ok_sec = self._qcwebs.set_wifi_security(passphrase=password)
                if not ok_basic or not ok_sec:
                    self._client.set_wifi_credentials(ssid, password)
                self.wifiSsid = ssid
                self.statusMessage = f"Wi-Fi configured: {ssid} (Ch {channel})"
            except Exception as exc:
                logger.error("Failed to save Wi-Fi config: %s", exc)
                self.statusMessage = f"Wi-Fi config failed: {exc}"

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(str, result=bool)
    def switchMode(self, target_mode: str) -> bool:
        """Switch between USB Cellular Modem (ppp0) and Standalone Pocket Router."""
        self.isSwitchingMode = True
        self.statusMessage = f"Switching operational mode to {target_mode}..."

        def _worker():
            try:
                if target_mode == "pocket_router":
                    res = self._mode_switcher.switch_to_router_mode()
                else:
                    res = self._mode_switcher.switch_to_usb_mode()
                self.operationalMode = res.get("mode", target_mode)
                self.statusMessage = res.get("message", "Mode switched.")
            except Exception as exc:
                logger.error("Mode switch error: %s", exc)
                self.statusMessage = f"Mode switch failed: {exc}"
            finally:
                self.isSwitchingMode = False
                try:
                    self._update_status_data(self._client.get_status())
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(result=list)
    def getWifiStations(self) -> list:
        """Scrape active connected stations from QC-Webs station_list.asp."""
        def _worker():
            try:
                stations = self._qcwebs.get_station_list()
                self.wifiStations = stations
                self.wifiClientsCount = len(stations)
            except Exception as exc:
                logger.debug("Failed to scrape station list: %s", exc)

        threading.Thread(target=_worker, daemon=True).start()
        return self._wifi_stations

    @Slot(result=bool)
    def openWebUi(self) -> bool:
        """Open QC-Webs WebUI at http://192.168.100.1 in desktop browser."""
        import subprocess
        try:
            subprocess.Popen(["xdg-open", f"http://{self._qcwebs.host}"])
            return True
        except Exception as exc:
            logger.debug("xdg-open failed: %s", exc)
            return False

    @Slot(result=bool)
    def rebootModem(self) -> bool:
        """Trigger baseband hardware restart."""
        def _worker():
            try:
                self._qcwebs.device_reboot()
                self.statusMessage = "Modem reboot signal sent."
            except Exception as exc:
                logger.error("Reboot failed: %s", exc)
                self.statusMessage = f"Reboot failed: {exc}"

        threading.Thread(target=_worker, daemon=True).start()
        return True

    @Slot(str, result=str)
    def executeAt(self, command: str) -> str:
        """Execute raw AT command transaction."""
        try:
            res = self._client.execute_at(command, timeout=3.0)
            lines = res.get("lines", [])
            output = "\n".join(lines)
            status = "OK" if res.get("success") else f"ERROR ({res.get('error', '')})"
            return f"{output}\n{status}".strip()
        except Exception as exc:
            return f"ERROR: {exc}"

    @Slot(str, str, result=bool)
    def sendSms(self, recipient: str, text: str) -> bool:
        """Send an SMS text message."""
        try:
            res = self._client.send_sms(recipient, text)
            if res.get("success"):
                self.statusMessage = f"SMS sent to {recipient}."
                self.getSmsThreads()
                return True
            else:
                self.statusMessage = f"Failed to send SMS: {res.get('error', 'Error')}"
                return False
        except Exception as exc:
            self.statusMessage = f"SMS error: {exc}"
            return False

    @Slot(result=list)
    def getSmsThreads(self) -> list:
        """Fetch indexed SMS conversation threads."""
        try:
            threads = self._client.list_sms()
            self.smsThreads = threads
            return threads
        except Exception as exc:
            logger.debug("Failed to list SMS threads: %s", exc)
            return []

    @Slot(int, result=list)
    def getSmsMessages(self, thread_id: int) -> list:
        """Fetch messages for a specific SMS thread."""
        try:
            msgs = self._client.list_sms(thread_id=thread_id)
            self.smsMessages = msgs
            return msgs
        except Exception as exc:
            logger.debug("Failed to list thread messages: %s", exc)
            return []

    @Slot(result=list)
    def syncSms(self) -> list:
        """Reconcile SMS from SIM card storage into local database."""
        def _worker():
            try:
                ingested = self._client.sync_sms(purge_sim=True)
                self.statusMessage = f"Synced {len(ingested)} message(s) from SIM."
                self.getSmsThreads()
            except Exception as exc:
                logger.error("SMS sync failed: %s", exc)
                self.statusMessage = f"SMS sync error: {exc}"

        threading.Thread(target=_worker, daemon=True).start()
        return []

    @Slot(str, result="QVariant")
    def calculateSmsSegments(self, text: str) -> dict:
        """Calculate character usage, multi-part segments, and GSM/UCS-2 encoding."""
        return calculate_sms_segments(text)

    @Slot(int, result=bool)
    def deleteThread(self, thread_id: int) -> bool:
        """Delete an entire SMS conversation thread and its messages."""
        try:
            res = self._client.delete_sms_thread(thread_id)
            if res.get("success"):
                self.statusMessage = f"Conversation #{thread_id} deleted."
                self.getSmsThreads()
                self.smsMessages = []
                return True
            return False
        except Exception as exc:
            logger.error("Failed to delete SMS thread: %s", exc)
            self.statusMessage = f"Delete error: {exc}"
            return False

    @Slot(int, result=bool)
    def markAsRead(self, thread_id: int) -> bool:
        """Mark SMS conversation thread messages as read."""
        try:
            res = self._client.mark_sms_read(thread_id)
            if res.get("success"):
                self.getSmsThreads()
                return True
            return False
        except Exception as exc:
            logger.debug("Failed to mark SMS thread as read: %s", exc)
            return False

    @Slot(str)
    def copyToClipboard(self, text: str) -> None:
        """Copy arbitrary string to desktop clipboard."""
        try:
            clipboard = QGuiApplication.clipboard()
            if clipboard:
                clipboard.setText(text)
        except Exception as exc:
            logger.error("Failed to copy text to clipboard: %s", exc)

    @Slot(str, str, result=bool)
    def sendNotification(self, title: str, message: str) -> bool:
        """Dispatch a Freedesktop desktop notification."""
        return send_desktop_notification(title=title, message=message)

    @Slot(str, str)
    def onSmsReceived(self, sender: str, body: str) -> None:
        """Handle spontaneous inbound SMS arrival."""
        logger.info("Inbound SMS received from %s: %s", sender, body[:30])
        send_desktop_notification(
            title=f"New SMS from {sender}",
            message=body[:140],
            icon="mail-unread",
        )
        self.smsReceived.emit(sender, body)
        self.getSmsThreads()

    # -----------------------------------------------------------------------
    # Telephony & Audio Bridge Slots
    # -----------------------------------------------------------------------

    def _on_call_state_change(self, state: str, session: Any) -> None:
        """Handle internal telephony engine state transition."""
        self.callState = state
        self.activeCallNumber = session.number
        self.callDuration = session.duration

    def _on_tragic_voice(self, details: dict) -> None:
        """Handle Tragic Voice CSFB rejection event."""
        self.tragicVoiceVisible = True
        self.tragicVoiceTriggered.emit(details)

    @Slot(str, result=bool)
    def dialNumber(self, number: str) -> bool:
        """Initiate outbound voice call via baseband."""
        res = self._telephony.dial(number)
        return res.get("success", False)

    @Slot(result=bool)
    def hangupCall(self) -> bool:
        """Terminate active or pending call session."""
        res = self._telephony.hangup()
        return res.get("success", False)

    @Slot(str, result=bool)
    def sendDtmfTone(self, digit: str) -> bool:
        """Synthesize and play audible DTMF tone for dialer keypad."""
        return play_dtmf_tone(digit)

    @Slot()
    def dismissTragicVoice(self) -> None:
        """Dismiss Tragic Voice narrative modal."""
        self.tragicVoiceVisible = False

    @Slot(str)
    def triggerTragicVoiceLore(self, number: str = "") -> None:
        """Trigger the Tragic Voice modal presentation for lore inspection."""
        self.tragicVoiceVisible = True
        target_number = number if number else (self.activeCallNumber or "121")
        self.tragicVoiceTriggered.emit({
            "title": TRAGIC_VOICE_LORE["title"],
            "subtitle": TRAGIC_VOICE_LORE["subtitle"],
            "number": target_number,
            "reason": "Pure-LTE CSFB Handover Refused (Manual Lore Inspection)",
            "narrative": TRAGIC_VOICE_LORE["narrative"],
            "timestamp": time.time(),
        })

    # -----------------------------------------------------------------------
    # Polling Control
    # -----------------------------------------------------------------------

    def start_polling(self, interval_ms: int = 1500) -> None:
        """Start periodic background telemetry sampling timer."""
        if self._poll_timer is None:
            self._poll_timer = QTimer(self)
            self._poll_timer.setInterval(interval_ms)
            self._poll_timer.timeout.connect(self.refreshStatus)
            self._poll_timer.start()

    def stop_polling(self) -> None:
        """Stop periodic background telemetry sampling timer."""
        if self._poll_timer is not None:
            self._poll_timer.stop()
            self._poll_timer = None


def create_app(
    client: Optional[MisltyClient] = None,
    argv: Optional[List[str]] = None,
) -> tuple[QApplication, QQmlApplicationEngine, MisltyBridge]:
    """
    Bootstrap the PySide6 application engine, bridge, and QML view stack.
    """
    if argv is None:
        argv = sys.argv

    # High-DPI scaling configuration and GLib isolation
    os.environ.setdefault("QT_NO_GLIB", "1")
    app = QApplication.instance()
    if app is None:
        app = QApplication(argv)
        app.setOrganizationName("Purrfect Software Limited")
        app.setOrganizationDomain("purrfect.software")
        app.setApplicationName("MisLTy")

    # Locate QML assets
    qml_dir = Path(__file__).resolve().parent / "qml"
    main_qml = qml_dir / "Main.qml"

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))

    bridge = MisltyBridge(client=client)
    engine.rootContext().setContextProperty("bridge", bridge)

    engine.load(QUrl.fromLocalFile(str(main_qml)))
    root_objects = engine.rootObjects()
    if not root_objects:
        raise RuntimeError("Failed to load QML root object from Main.qml")

    try:
        from mislty.gui.tray import MisltyTray
        tray = MisltyTray(bridge=bridge, app=app, window=root_objects[0])
        tray.show()
        bridge._tray = tray
    except Exception as exc:
        logger.warning("Could not initialize system tray: %s", exc)

    return app, engine, bridge


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for MisLTy Desktop GUI."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    app, engine, bridge = create_app(argv=argv)
    bridge.start_polling(interval_ms=1500)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
