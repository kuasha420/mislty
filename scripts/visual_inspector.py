"""
scripts.visual_inspector
~~~~~~~~~~~~~~~~~~~~~~~~

Automated visual inspection tool for MisLTy Qt/QML Desktop Suite.
Renders all views at standard, large, and compact viewport dimensions,
populates rich state data, captures pixel-perfect high-DPI screenshots,
and saves them for visual analysis.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
import time

from PySide6.QtCore import Property, QEventLoop, QObject, QPoint, QRect, QTimer, QUrl, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPixmap
from PySide6.QtQuick import QQuickWindow, QQuickItem
from PySide6.QtQuickControls2 import *
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication

# GLib isolation
os.environ["QT_NO_GLIB"] = "1"


class MockVisualBridge(QObject):
    """Bridge pre-populated with realistic, rich telemetry for visual inspection."""

    # Notification Signals
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
    peerIpChanged = Signal(str)
    dnsServersChanged = Signal(list)
    uptimeSecondsChanged = Signal(float)
    operationalModeChanged = Signal(str)
    activeDeckChanged = Signal(int)
    callStatusChanged = Signal(str)
    callDurationSecondsChanged = Signal(int)
    tragicVoiceVisibleChanged = Signal(bool)
    tragicVoiceModalVisibleChanged = Signal(bool)
    smsThreadsChanged = Signal()
    smsMessagesChanged = Signal()
    wifiStationsChanged = Signal()

    modemPresentChanged = Signal(bool)
    modemReadyChanged = Signal(bool)
    isZeroCdChanged = Signal(bool)
    hardwarePortsChanged = Signal(dict)
    hardwareStateTextChanged = Signal(str)

    wlanDevicesChanged = Signal(list)
    relayActiveChanged = Signal(bool)
    relayInterfaceChanged = Signal(str)
    relaySsidChanged = Signal(str)
    relayIpAddressChanged = Signal(str)
    relayUptimeChanged = Signal(int)
    relayClientsChanged = Signal(list)
    relayWanInterfaceChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._modem_present = True
        self._modem_ready = True
        self._is_zero_cd = False
        self._hardware_ports = {
            "control": "/dev/mislty/control",
            "data": "/dev/mislty/data",
            "voice": "/dev/mislty/voice",
            "diag": "/dev/mislty/diag"
        }
        self._hardware_state_text = "READY"
        self._connected = True
        self._connecting = False
        self._operator = "Robi Axiata"
        self._technology = "4G LTE (B3 / 1800 MHz)"
        self._signal_bars = 4
        self._signal_csq = 28
        self._signal_dbm = -57
        self._wifi_power = True
        self._wifi_ssid = "TypeScript 420"
        self._wifi_clients_count = 3
        self._rx_bytes = 142000000       # 142 MB
        self._tx_bytes = 38000000        # 38 MB
        self._rx_rate = 1760000.0       # 1.76 MB/s
        self._tx_rate = 421000.0        # 421 KB/s
        self._ip_address = "100.119.24.197"
        self._peer_ip = "10.64.64.64"
        self._dns_servers = ["10.17.160.102", "103.242.23.166"]
        self._uptime_seconds = 4218.0
        self._operational_mode = "modem"
        self._active_deck = 0
        self._call_status = "IDLE"
        self._call_duration = 0
        self._tragic_modal = False

        # Bandwidth rolling history
        self._rx_history = [120, 340, 560, 890, 1200, 1500, 1300, 900, 1100, 1400, 1800, 2100,
                            1900, 1600, 1400, 1200, 1100, 1500, 1750, 1850, 1600, 1450, 1845, 1800]
        self._tx_history = [40, 80, 120, 160, 210, 300, 280, 250, 220, 290, 350, 420,
                            390, 310, 290, 240, 260, 310, 340, 380, 400, 410, 421, 390]

        # Station table mock
        self._wifi_clients = [
            {"mac": "64:79:f0:36:70:ae", "ip": "192.168.100.101", "hostname": "thinkpad-x1", "tx_rate": "72.2 Mbps", "rx_rate": "65.0 Mbps", "connected_time": "01:24:12"},
            {"mac": "aa:bb:cc:dd:ee:01", "ip": "192.168.100.102", "hostname": "pixel-9-pro", "tx_rate": "54.0 Mbps", "rx_rate": "48.0 Mbps", "connected_time": "00:45:30"},
            {"mac": "12:34:56:78:9a:bc", "ip": "192.168.100.103", "hostname": "ipad-air-m2", "tx_rate": "65.0 Mbps", "rx_rate": "54.0 Mbps", "connected_time": "00:12:05"},
        ]

        # SMS threads mock matching SmsStore database schema
        self._sms_threads = [
            {"id": 1, "recipient_number": "Robi", "contact_name": "Robi", "snippet": "Special Offer: 10GB for 7 Days at 99 BDT! Dial *4#", "updated_at": "18:45", "unread_count": 2, "message_count": 14},
            {"id": 2, "recipient_number": "+8801812345678", "contact_name": "Antigravity Core", "snippet": "Did you test the PipeWire audio bridge on MI_02?", "updated_at": "17:30", "unread_count": 0, "message_count": 6},
            {"id": 3, "recipient_number": "121", "contact_name": "Customer Care", "snippet": "Your current balance is 142.50 BDT. Valid until 30-Nov-2026.", "updated_at": "Yesterday", "unread_count": 0, "message_count": 2},
        ]

        self._sms_messages = [
            {"id": 101, "thread_id": 2, "direction": "IN", "phone_number": "+8801812345678", "body": "Hey, is the MDM9600 cellular modem working under Linux now?", "timestamp": "2026-09-10 17:20:00", "status": "RECEIVED", "is_read": True},
            {"id": 102, "thread_id": 2, "direction": "OUT", "phone_number": "+8801812345678", "body": "Yes! MisLTy is online with ppp0 dial-up and Broadcom Wi-Fi co-processor supervisor.", "timestamp": "2026-09-10 17:25:00", "status": "DELIVERED", "is_read": True},
            {"id": 103, "thread_id": 2, "direction": "IN", "phone_number": "+8801812345678", "body": "Did you test the PipeWire audio bridge on MI_02?", "timestamp": "2026-09-10 17:30:00", "status": "RECEIVED", "is_read": True},
        ]

        self._active_thread_id = 2

        # Wi-Fi Hotspot Relay Mock Data
        self._wlan_devices = [
            {"iface": "wlan0", "vendor": "Intel Corporation", "model": "Wireless 8265 / 8275", "driver": "iwlwifi", "mac": "64:79:f0:36:70:ae", "is_primary": True, "supports_ap": True, "is_candidate": False},
            {"iface": "wlan1", "vendor": "TP-Link", "model": "Archer T4U ver.3", "driver": "rtw88_8822bu", "mac": "92:b8:bf:75:a5:fe", "is_primary": False, "supports_ap": True, "is_candidate": True},
        ]
        self._relay_active = True
        self._relay_interface = "wlan1"
        self._relay_ssid = "MisLTy 4G Share"
        self._relay_ip_address = "10.42.0.1"
        self._relay_uptime = 1240
        self._relay_clients = [
            {"mac": "b4:b0:24:aa:bb:cc", "ip": "10.42.0.52", "signal_dbm": -48, "rx_bytes": 14200000, "tx_bytes": 3500000},
            {"mac": "e4:5f:01:42:00:88", "ip": "10.42.0.105", "signal_dbm": -62, "rx_bytes": 8900000, "tx_bytes": 1200000},
        ]
        self._relay_wan_interface = "ppp0"

    # QML Properties
    @Property(list, notify=wlanDevicesChanged)
    def wlanDevices(self): return self._wlan_devices

    @Property(bool, notify=relayActiveChanged)
    def relayActive(self): return self._relay_active

    @Property(str, notify=relayInterfaceChanged)
    def relayInterface(self): return self._relay_interface

    @Property(str, notify=relaySsidChanged)
    def relaySsid(self): return self._relay_ssid

    @Property(str, notify=relayIpAddressChanged)
    def relayIpAddress(self): return self._relay_ip_address

    @Property(int, notify=relayUptimeChanged)
    def relayUptime(self): return self._relay_uptime

    @Property(list, notify=relayClientsChanged)
    def relayClients(self): return self._relay_clients

    @Property(str, notify=relayWanInterfaceChanged)
    def relayWanInterface(self): return self._relay_wan_interface

    @Property(bool, notify=connectedChanged)
    def connected(self): return self._connected

    @Property(bool, notify=connectingChanged)
    def connecting(self): return self._connecting

    @Property(str, notify=operatorChanged)
    def operator(self): return self._operator

    @Property(str, notify=technologyChanged)
    def technology(self): return self._technology

    @Property(int, notify=signalBarsChanged)
    def signalBars(self): return self._signal_bars

    @Property(int, notify=signalCsqChanged)
    def signalCsq(self): return self._signal_csq

    @Property(int, notify=signalDbmChanged)
    def signalDbm(self): return self._signal_dbm

    @Property(bool, notify=wifiPowerChanged)
    def wifiPower(self): return self._wifi_power

    @Property(str, notify=wifiSsidChanged)
    def wifiSsid(self): return self._wifi_ssid

    @Property(int, notify=wifiClientsCountChanged)
    def wifiClientsCount(self): return self._wifi_clients_count

    @Property(int, notify=rxBytesChanged)
    def rxBytes(self): return self._rx_bytes

    @Property(int, notify=txBytesChanged)
    def txBytes(self): return self._tx_bytes

    @Property(float, notify=rxRateChanged)
    def rxRate(self): return self._rx_rate

    @Property(float, notify=txRateChanged)
    def txRate(self): return self._tx_rate

    @Property(str, notify=ipAddressChanged)
    def ipAddress(self): return self._ip_address

    @Property(str, notify=peerIpChanged)
    def peerIp(self): return self._peer_ip

    @Property(list, notify=dnsServersChanged)
    def dnsServers(self): return self._dns_servers

    @Property(float, notify=uptimeSecondsChanged)
    def uptimeSeconds(self): return self._uptime_seconds

    @Property(str, notify=operationalModeChanged)
    def operationalMode(self): return self._operational_mode

    @Property(int, notify=activeDeckChanged)
    def activeDeck(self): return self._active_deck

    @Property(str, notify=callStatusChanged)
    def callStatus(self): return self._call_status

    @Property(int, notify=callDurationSecondsChanged)
    def callDurationSeconds(self): return self._call_duration

    @Property(bool, notify=tragicVoiceModalVisibleChanged)
    def tragicVoiceVisible(self): return self._tragic_modal

    @Property(bool, notify=tragicVoiceModalVisibleChanged)
    def tragicVoiceModalVisible(self): return self._tragic_modal

    @Property(list, notify=smsThreadsChanged)
    def smsThreads(self): return self._sms_threads

    @Property(list, notify=smsMessagesChanged)
    def smsMessages(self): return self._sms_messages

    @Property(list, notify=wifiStationsChanged)
    def wifiStations(self): return self._wifi_clients

    @Property(bool, notify=modemPresentChanged)
    def modemPresent(self): return self._modem_present

    @Property(bool, notify=modemReadyChanged)
    def modemReady(self): return self._modem_ready

    @Property(bool, notify=isZeroCdChanged)
    def isZeroCd(self): return self._is_zero_cd

    @Property(dict, notify=hardwarePortsChanged)
    def hardwarePorts(self): return self._hardware_ports

    @Property(str, notify=hardwareStateTextChanged)
    def hardwareStateText(self): return self._hardware_state_text

    # Slots called from QML
    @Slot(int)
    def setActiveDeck(self, index: int):
        self._active_deck = index
        self.activeDeckChanged.emit(index)

    @Slot()
    def toggleConnect(self):
        self._connected = not self._connected
        self.connectedChanged.emit(self._connected)

    @Slot()
    def refreshStatus(self): pass

    @Slot(result=list)
    def getRxHistory(self): return self._rx_history

    @Slot(result=list)
    def getTxHistory(self): return self._tx_history

    @Slot(result=list)
    def getWifiClients(self): return self._wifi_clients

    @Slot(result=list)
    def refreshWlanDevices(self): return self._wlan_devices

    @Slot(str, str, str, str, int, str, result=bool)
    def startHotspotRelay(self, *args):
        self._relay_active = True
        self.relayActiveChanged.emit(True)
        return True

    @Slot(result=bool)
    def stopHotspotRelay(self):
        self._relay_active = False
        self.relayActiveChanged.emit(False)
        return True

    @Slot(result=list)
    def getHotspotRelayClients(self): return self._relay_clients

    @Slot(result=list)
    def getSmsThreads(self): return self._sms_threads

    @Slot(int, result=list)
    def getThreadMessages(self, thread_id: int):
        return self._sms_messages

    @Slot(str, str, result=dict)
    def sendSms(self, recipient: str, text: str):
        return {"success": True, "message_id": 999}

    @Slot(str, result=dict)
    def calculateSms(self, text: str):
        from mislty.core.sms import calculate_sms_segments
        segs = calculate_sms_segments(text)
        return {"encoding": segs.encoding, "chars": segs.character_count, "max_chars": segs.max_characters, "segments": segs.segments}

    @Slot(str)
    def dialNumber(self, number: str): pass

    @Slot()
    def hangupCall(self): pass

    @Slot(str)
    def sendDtmf(self, digit: str): pass

    @Slot()
    def openWebUi(self): pass

    @Slot(str)
    def setSsid(self, ssid: str):
        self._wifi_ssid = ssid
        self.wifiSsidChanged.emit(ssid)

    @Slot(str)
    def setOperationalMode(self, mode: str):
        self._operational_mode = mode
        self.operationalModeChanged.emit(mode)

    @Slot(str, result=dict)
    def executeAt(self, cmd: str):
        return {"success": True, "lines": ["OK"]}

    @Slot(result=dict)
    def getPorts(self):
        return {"data": "/dev/mislty/data", "control": "/dev/mislty/control", "voice": "/dev/mislty/voice", "diag": "/dev/mislty/diag"}


def render_inspection(output_dir: Path, live: bool = False):
    output_dir.mkdir(parents=True, exist_ok=True)

    app = QApplication.instance()
    if app is None:
        app = QApplication(["--platform", "offscreen"])

    # Locate QML
    repo_root = Path(__file__).resolve().parent.parent
    qml_dir = repo_root / "src" / "mislty" / "gui" / "qml"
    main_qml = qml_dir / "Main.qml"

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))

    if live:
        from mislty.gui.app import MisltyBridge
        bridge = MisltyBridge()
    else:
        bridge = MockVisualBridge()

    engine.rootContext().setContextProperty("bridge", bridge)
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    root_objects = engine.rootObjects()
    if not root_objects:
        raise RuntimeError("Failed to load root window from Main.qml")

    window = root_objects[0]
    window.show()

    # Define views to test
    views = [
        (0, "dashboard", "Dashboard Overview"),
        (1, "wifi", "Wi-Fi Hotspot Deck"),
        (2, "sms", "SMS Center Deck"),
        (3, "dialer", "Phone Dialer Deck"),
        (4, "diagnostics", "Diagnostics Console Deck"),
    ]

    resolutions = [
        (980, 650, "default"),
        (1200, 800, "large"),
        (850, 560, "compact"),
    ]

    captured_files = []

    for w, h, res_label in resolutions:
        window.setWidth(w)
        window.setHeight(h)

        for deck_idx, name, title in views:
            bridge.setActiveDeck(deck_idx)

            # Let QML layout and animations settle
            for _ in range(15):
                app.processEvents()
                time.sleep(0.02)

            content = window.contentItem()
            loop = QEventLoop()
            grab = content.grabToImage()
            grab.ready.connect(loop.quit)
            loop.exec()

            out_file = output_dir / f"{name}_{res_label}_{w}x{h}.png"
            grab.saveToFile(str(out_file))
            print(f"Captured: {out_file.name} ({w}x{h})")
            captured_files.append(out_file)

            if deck_idx == 1 and res_label == "default":
                scroll_item = window.findChild(QQuickItem, "wifiScrollView")
                if scroll_item:
                    scroll_item.setProperty("contentY", 450.0)
                    for child in scroll_item.childItems():
                        if child.property("contentY") is not None:
                            child.setProperty("contentY", 450.0)
                for _ in range(25):
                    app.processEvents()
                    time.sleep(0.02)
                loop = QEventLoop()
                grab_scrolled = window.contentItem().grabToImage()
                grab_scrolled.ready.connect(loop.quit)
                loop.exec()
                scrolled_out = output_dir / f"wifi_relay_scrolled_{w}x{h}.png"
                grab_scrolled.saveToFile(str(scrolled_out))
                print(f"Captured: {scrolled_out.name}")
                captured_files.append(scrolled_out)

    # Also capture Tragic Voice Lore modal if on dialer view
    bridge.setActiveDeck(3)
    if hasattr(bridge, "tragicVoiceVisibleChanged"):
        if hasattr(bridge, "tragicVoiceVisible"):
            try:
                bridge.tragicVoiceVisible = True
            except Exception:
                pass
        bridge.tragicVoiceVisibleChanged.emit(True)
    if hasattr(bridge, "tragicVoiceModalVisibleChanged"):
        bridge._tragic_modal = True
        bridge.tragicVoiceModalVisibleChanged.emit(True)
    for _ in range(15):
        app.processEvents()
        time.sleep(0.02)

    loop = QEventLoop()
    grab = window.contentItem().grabToImage()
    grab.ready.connect(loop.quit)
    loop.exec()

    tragic_out = output_dir / f"tragic_voice_modal_980x650.png"
    grab.saveToFile(str(tragic_out))
    print(f"Captured: {tragic_out.name}")
    captured_files.append(tragic_out)

    return captured_files


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MisLTy Visual Inspector")
    parser.add_argument("--out-dir", default="screenshots", help="Directory to save screenshots")
    parser.add_argument("--live", action="store_true", help="Use live backend instead of mock data")
    args = parser.parse_args()

    out_path = Path(args.out_dir).resolve()
    print(f"Running visual inspection, outputting to: {out_path}")
    files = render_inspection(out_path, live=args.live)
    print(f"Successfully generated {len(files)} screenshot captures.")
