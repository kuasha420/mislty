# Technical Design Document (TDD)
## MisLTy Desktop Suite & MicroSD Toolkit
### *Engineering Architecture, IPC Protocols, Component Boundaries & Implementation Contracts*

```
  /\_/\  
 ( o.o )  MisLTy Systems Architecture Blueprint
  > ^ <   "Software out of time, for hardware out of time."
```

---

| Document Metadata | Specification |
| :--- | :--- |
| **Document ID** | `TDD-MISLTY-2026-V1` |
| **Reference PRD** | [docs/PRD.md](file:///home/psl/Projects/ufi-modem/docs/PRD.md) |
| **Target Hardware** | Aleka Incorporated UV310 (Qualcomm MDM9600 / Broadcom BRCM_WL) |
| **System IDs** | USB VID/PID: `05c6:6000` (Post-Modeswitch) |
| **Author** | Purrfect Software Limited (PSL) Systems Architecture Guild |
| **Status** | `APPROVED FOR IMPLEMENTATION` |

---

## 1. System & Process Architecture

### 1.1 Process Topology
The MisLTy suite decouples long-running device state management, high-speed data transmission, desktop user interface, and telephony audio streaming into four distinct processes communicating across IPC and serial planes:

```
+---------------------------------------------------------------------------------------+
|                                    Linux Host System                                  |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   | Desktop User Space                                                            |   |
|   |                                                                               |   |
|   |   +-------------------------+      +------------------+                       |   |
|   |   | MisLTy GUI (PySide6)    |      | MisLTy CLI       |                       |   |
|   |   | - Dashboard & Gauges    |      | (mislty status,  |                       |   |
|   |   | - SMS Split-Pane        |      |  connect, sms)   |                       |   |
|   |   | - Tray Applet           |      +--------+---------+                       |   |
|   |   +------------+------------+               |                                 |   |
|   +----------------|----------------------------|---------------------------------+   |
|                    | IPC (D-Bus / Unix Socket)  |                                     |
|                    v                            v                                     |
|   +-------------------------------------------------------------------------------+   |
|   | MisLTy Core Daemon (`misltyd` - systemd user service)                         |   |
|   |                                                                               |   |
|   |   +------------------------+  +--------------------+  +-------------------+   |   |
|   |   | Control Port Master    |  | Unsolicited Event  |  | IPC Server        |   |   |
|   |   | (Exclusive MI_01 lock) |  | Parser (URC)       |  | (D-Bus & Socket)  |   |   |
|   |   | - 2000ms CSQ Telemetry |  | - +CMTI, +CMGS     |  | - org.mislty.Modem|   |   |
|   |   | - Wi-Fi AP NVRAM Sync  |  | - RING, +CLIP      |  | - /run/user/sock  |   |   |
|   |   | - Command Priority Mtx |  | - +CEREG, +CREG    |  +---------+---------+   |   |
|   |   +-----------+------------+  +---------+----------+            |             |   |
|   |               |                         |                       |             |   |
|   |               +-------------------+-----+                       |             |   |
|   |                                   |                             |             |   |
|   |   +-------------------------------+-------------------------+   |             |   |
|   |   | SQLite Storage Manager                                  |   |             |   |
|   |   | - SMS Threads & Full History (WAL Mode)                 |   |             |   |
|   |   | - Session Bandwidth Accounting                          |   |             |   |
|   |   +---------------------------------------------------------+   |             |   |
|   |                                                                 |             |   |
|   |   +---------------------------------------------------------+   |             |   |
|   |   | Network & Polkit Supervisor                             |   |             |   |
|   |   | - Invokes pppd on MI_00 (/dev/mislty/modem)             |   |             |   |
|   |   | - Manages Routing Table (metric 50) & DNS               |   |             |   |
|   |   +---------------------------------------------------------+   |             |   |
|   +-----------------------------------|-----------------------------|-------------+   |
|                                       |                             |                 |
|   +-----------------------------------|-----------------------------|-------------+   |
|   | Audio & Telephony Process         |                             |                 |
|   |                                   |                             |                 |
|   |   +-------------------------+     |                             |                 |
|   |   | mislty-voice-bridge     |     |                             |                 |
|   |   | - 8000 Hz 16-bit Mono   |     |                             |                 |
|   |   | - PipeWire / ALSA Loop  |     |                             |                 |
|   |   +------------+------------+     |                             |                 |
|   +----------------|------------------|-----------------------------|-------------+   |
+--------------------|------------------|-----------------------------|-----------------+
                     |                  |                             |
                     v                  v                             v
            +-----------------+  +-----------------+           +-----------------+
            | /dev/mislty/    |  | /dev/mislty/    |           | /dev/mislty/    |
            | voice (MI_02)   |  | control (MI_01) |           | modem (MI_00)   |
            +-----------------+  +-----------------+           +-----------------+
                     |                  |                             |
+--------------------+------------------+-----------------------------+-----------------+
|                       Aleka UV310 USB 4G Dongle (05c6:6000)                           |
+---------------------------------------------------------------------------------------+
```

### 1.2 Physical Interface Mapping & Udev Determinism
Linux kernel `option.ko` binds to interfaces 0–3, while `usb-storage` claims interface 4. Standard `/dev/ttyUSB*` numbering fluctuates if auxiliary serial devices exist. MisLTy enforces determinism via persistent `/dev/mislty/*` symlinks:

| Hardware Endpoint | Interface # | Sysfs Path | Canonical Symlink | Exclusive Owner | Protocol / Payload |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MI_00`** | Interface 00 | `...:1.0/ttyUSB*` | `/dev/mislty/modem` | `pppd` daemon | Raw HDLC Point-to-Point Protocol (`ATD*99#`) |
| **`MI_01`** | Interface 01 | `...:1.1/ttyUSB*` | `/dev/mislty/control` | `misltyd` core daemon | Non-blocking Hayes AT, URC alerts, RF telemetry |
| **`MI_02`** | Interface 02 | `...:1.2/ttyUSB*` | `/dev/mislty/voice` | `mislty-voice-bridge` | Raw uncompressed 8000 Hz 16-bit mono PCM |
| **`MI_03`** | Interface 03 | `...:1.3/ttyUSB*` | `/dev/mislty/diag` | Diagnostic / QCDM tool | Qualcomm DM binary frames |
| **`MI_04`** | Interface 04 | `...:1.4/host*/...`| `/dev/disk/by-label/UFI_TOOLKIT` | Kernel `usb-storage` | FAT32 mass storage (MicroSD card) |

### 1.3 Serial Port Locking & Contention Model
1. **Single Master on `MI_01`**:
   - `misltyd` opens `/dev/mislty/control` (`115200 8N1`, `O_RDWR | O_NOCTTY | O_NONBLOCK`) and holds it open for the duration of the systemd user session.
   - An asynchronous `select()` / `poll()` event loop handles incoming traffic.
2. **Command Serialization (The Serial Mutex)**:
   - AT command queries (`AT+CSQ`, `AT+WIFI?`, `AT+CGDCONT?`) run on a priority queue.
   - Periodic telemetry tasks yield instantly if a user-directed command (e.g., `SendSms`, `SetWifiCredentials`, `DialVoice`) enters the queue.
3. **CLI Standalone Fallback**:
   - When the user runs `mislty <command>`, the CLI client first checks if `misltyd` is reachable via IPC (D-Bus or Unix socket).
   - If `misltyd` is running: CLI dispatches an IPC request and prints the response.
   - If `misltyd` is **not** running (e.g., minimal recovery mode, air-gapped terminal): CLI acquires a brief lock on `/dev/mislty/control`, executes the AT sequence directly, and exits.

---

## 2. Codebase Directory Layout & Package Structure

The project transitions from a monolithic script into a modular Python package adhering to PEP 517/621:

```text
ufi-modem/
├── pyproject.toml                      # Build metadata & dependency declarations
├── README.md                           # Public overview & developer setup
├── docs/                               # Specs & architectural documentation
│   ├── PRD.md
│   ├── TECHNICAL_DESIGN.md             # (This document)
│   ├── HARDWARE_SPEC.md
│   ├── SOFTWARE_SPEC.md
│   ├── OPERATIONAL_MODES.md
│   ├── AT_COMMAND_REFERENCE.md
│   ├── VOICE_CALL_ANALYSIS.md
│   ├── SD_CARD_SPEC.md
│   └── LINUX_COMPATIBILITY_GUIDE.md
├── config/                             # Production system configuration files
│   ├── udev/
│   │   └── 99-ufi-permissions.rules    # Hardened udev rules with ID_MM_DEVICE_IGNORE
│   ├── ppp/
│   │   ├── chat-ufi                    # Optimized cellular chatscript
│   │   └── peers-ufi                   # Optimized pppd peer file
│   ├── polkit/
│   │   └── org.freedesktop.mislty.policy # Polkit action definitions
│   └── systemd/
│       └── mislty-daemon.service       # systemd user unit
├── src/
│   └── mislty/
│       ├── __init__.py                 # Version & package exports
│       ├── __main__.py                 # Entrypoint for python -m mislty
│       ├── core/                       # Serial, protocol & hardware abstraction
│       │   ├── __init__.py
│       │   ├── port_resolver.py        # Resolves /dev/mislty/* from sysfs/udev
│       │   ├── serial_transport.py     # Non-blocking async POSIX termios transport
│       │   ├── at_parser.py            # AT tokenizer, response parser & error mapper
│       │   ├── urc_demuxer.py          # Real-time event demuxer (+CMTI, +CMGS, RING)
│       │   ├── modem_state.py          # State engine tracking SIM, RF, Wi-Fi, PPP
│       │   └── exceptions.py           # Typed domain exceptions
│       ├── daemon/                     # Long-running service logic
│       │   ├── __init__.py
│       │   ├── engine.py               # Main asyncio daemon event loop
│       │   ├── telemetry.py            # 2000ms CSQ, COPS, CEREG polling coordinator
│       │   ├── watchdog.py             # PPP link supervisor & auto-reconnect backoff
│       │   └── service.py              # Daemon lifecycle & signal handling
│       ├── ipc/                        # Inter-Process Communication
│       │   ├── __init__.py
│       │   ├── protocol.py             # DTO schemas, data types & constants
│       │   ├── dbus_service.py         # org.mislty.Modem implementation (sdbus-network)
│       │   ├── socket_server.py        # Unix domain socket JSON-RPC 2.0 server
│       │   └── client.py               # Unified client (D-Bus with Socket fallback)
│       ├── net/                        # Linux networking & privileges
│       │   ├── __init__.py
│       │   ├── ppp_controller.py       # pppd process launcher, supervisor & PID tracking
│       │   ├── route_manager.py        # Deterministic routing table (metric 50)
│       │   ├── dns_manager.py          # systemd-resolved & resolv.conf manager
│       │   ├── qcwebs_client.py        # Embedded QC-Webs (192.168.100.1:80) GoForm & JSON telemetry client (see QC_WEBS_API_SPEC.md)
│       │   ├── relay_manager.py        # Linux host reverse-tethering hotspot relay (iptables)
│       │   └── helper_client.py        # Interface to privileged helper
│       ├── storage/                    # Persistence layer
│       │   ├── __init__.py
│       │   ├── database.py             # SQLite WAL connection manager
│       │   ├── sms_store.py            # Two-way conversation threads & contact cache
│       │   └── metrics_store.py        # Session throughput & historical data tracking
│       ├── audio/                      # Voice & Easter Egg subsystem
│       │   ├── __init__.py
│       │   ├── pcm_streamer.py         # 16-bit 8000 Hz mono reader/writer on MI_02
│       │   ├── pipewire_bridge.py      # PipeWire pw-cat subprocess loopback
│       │   └── lore_engine.py          # CSFB rejection detector & easter egg controller
│       ├── cli/                        # Terminal interface (mislty)
│       │   ├── __init__.py
│       │   ├── main.py                 # CLI argument parsing & dispatch
│       │   ├── commands/               # Subcommand implementations
│       │   │   ├── status.py
│       │   │   ├── connect.py
│       │   │   ├── disconnect.py
│       │   │   ├── wifi.py
│       │   │   ├── sms.py
│       │   │   ├── sim.py
│       │   │   └── at.py
│       │   └── formatter.py            # ANSI colors, tabular output & progress bars
│       └── gui/                        # Desktop Interface (PySide6 / Qt6)
│           ├── __init__.py
│           ├── app.py                  # Qt application initialization & lifecycle
│           ├── tray.py                 # Dynamic 5-bar QSystemTrayIcon
│           ├── viewmodels/             # Reactive QObject bridge between IPC & QML
│           │   ├── dashboard_vm.py
│           │   ├── wifi_vm.py
│           │   ├── sms_vm.py
│           │   ├── phone_vm.py
│           │   └── diag_vm.py
│           └── qml/                    # Qt Quick Controls 2 Declarative UI
│               ├── Main.qml
│               ├── Theme.qml           # Feline palette tokens (#1A1823, #E5A93C, etc.)
│               ├── components/         # Reusable cards, buttons, signal meters
│               └── views/              # DashboardView, WifiView, SmsView, PhoneView
├── helper/                             # Privileged execution helper
│   ├── mislty-net-helper               # Audited Python/POSIX script executed via Polkit
│   └── org.freedesktop.mislty.policy
├── packaging/                          # Distribution scripts
│   ├── pyinstaller/
│   │   └── mislty.spec                 # PyInstaller standalone build recipe
│   ├── appimage/
│   │   └── AppRun
│   └── toolkit/                        # MicroSD staging tree (UFI_TOOLKIT)
│       ├── install.sh                  # Zero-internet offline installer
│       └── uninstall.sh
└── tests/                              # Automated test suite
    ├── unit/
    │   ├── test_at_parser.py
    │   ├── test_urc_demuxer.py
    │   ├── test_port_resolver.py
    │   └── test_sms_store.py
    └── integration/
        ├── test_ipc_contracts.py
        └── test_mode_switch.py
```

---

## 3. IPC Specification: D-Bus & Unix Domain Socket

MisLTy exposes its complete state and control plane over standard desktop IPC. **D-Bus Session Bus** is the canonical primary interface, complemented by a local **Unix Domain Socket** (`JSON-RPC 2.0`) for headless or containerized environments.

### 3.1 D-Bus Interface Specification
* **Well-Known Bus Name**: `org.mislty.Modem`
* **Object Path**: `/org/mislty/Modem`
* **Primary Interface**: `org.mislty.Modem1`

#### 3.1.1 Methods
| Method Name | Input Parameters | Return Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GetStatus` | *None* | `a{sv}: status` | Returns full snapshot of hardware, SIM, cellular RF, Wi-Fi AP, and PPP data plane. |
| `Connect` | `s: gateway_mode` | `b: success, s: message` | Initiates USB cellular connection (`"default"` for metric 50 default route; `"secondary"` for split route). |
| `Disconnect` | *None* | `b: success, s: message` | Terminates active `ppp0` data session and restores host routing/DNS. |
| `SetWifiPower` | `b: enable` | `b: success, s: message` | Toggles Broadcom Wi-Fi co-processor (`AT+WIFI=1` or `AT+WIFI=0`). |
| `SetWifiCredentials` | `s: ssid, s: password` | `b: success, s: message` | Configures new SSID and WPA2-PSK key (uses GoForm API for clean un-suffixed SSID; falls back to serial `AT^SSID`). |
| `CommitWifiNvram` | *None* | `b: success, s: message` | Flushes current Wi-Fi configuration to persistent flash memory (`AT+WRWIFI`). |
| `SendSms` | `s: recipient, s: text` | `b: success, s: message, i: ref` | Sends standard 7-bit GSM-03.38 text SMS via `AT+CMGS`. |
| `ListSms` | `s: box, i: limit, i: offset`| `aa{sv}: messages` | Queries stored messages from local SQLite database (`box`: `"inbox"`, `"outbox"`, `"all"`). |
| `DeleteSms` | `i: message_id` | `b: success` | Deletes message from local database and SIM memory. |
| `ExecuteRawAt` | `s: command, d: timeout` | `s: response` | Sends arbitrary Hayes AT command to `MI_01` (Diagnostics/Dev console). |
| `SetWorkMode` | `s: mode` | `b: success, s: message` | Transitions between `"router"` (Pocket Router) and `"usb"` (USB Modem) in ~3.4 seconds. |
| `GetWifiClients` | *None* | `aa{sv}: clients` | Queries local QC-Webs API on `http://192.168.100.1/` returning active Wi-Fi client leases (MAC, IP, hostname). |
| `SetHotspotRelay` | `b: enable` | `b: success, s: message` | Enables Linux kernel masquerade routing between `ppp0` and Wi-Fi interface (Reverse-Tethering Hotspot Relay). |
| `StartAudioTest` | *None* | `b: success` | Bridges `MI_02` 8000 Hz PCM audio to PipeWire system speakers. |
| `StopAudioTest` | *None* | `b: success` | Terminates active PipeWire audio bridge. |
| `DialVoice` | `s: phone_number` | `b: success, s: message` | Dials voice call (`ATD<num>;`) to trigger the CSFB Easter Egg. |

#### 3.1.2 Signals (Real-Time Asynchronous Events)
| Signal Name | Payload Signature | Description |
| :--- | :--- | :--- |
| `SignalQualityChanged` | `i: rssi, i: dbm, y: bars` | Emitted when RF telemetry shifts (0–31 RSSI, -113 to -51 dBm, 0–5 bars). |
| `RegistrationChanged` | `s: operator, y: stat, s: tech` | Emitted when cellular network operator or EPS status changes. |
| `ConnectionStateChanged`| `b: connected, s: iface, s: ip, s: mode`| Emitted upon PPP connect, disconnect, or IP change. |
| `WifiStateChanged` | `b: enabled, b: transmitting, s: ssid` | Emitted when Wi-Fi state shifts (handles mutual exclusion suspended state). |
| `SmsReceived` | `i: id, s: sender, s: timestamp, s: text` | Emitted immediately when `+CMTI` URC is captured and decoded from SIM. |
| `SmsSubmissionChanged` | `i: ref, s: status, s: details` | Emitted when `+CMGS` confirmation arrives or send error occurs. |
| `CallStateChanged` | `s: state, s: number, s: reason` | Emitted during voice dialing, incoming `RING`, or `+CEER` rejection. |

#### 3.1.3 Properties
| Property Name | Type | Access | Description |
| :--- | :--- | :--- | :--- |
| `IsConnected` | `b` | Read | True if `ppp0` is up with an active IP. |
| `AllocatedIp` | `s` | Read | Assigned cellular IP address (`10.x.x.x` or public). |
| `SignalDbm` | `i` | Read | Current signal strength in dBm (-113 to -51). |
| `SignalBars` | `y` | Read | Visual 0–5 bar index. |
| `OperatorName` | `s` | Read | Current registered network (e.g. "Robi", "Teletalk"). |
| `WifiTransmitting` | `b` | Read | Current hardware transmitter status (`AT^WIENABLE?`). |
| `CurrentSsid` | `s` | Read | Configured Wi-Fi SSID. |
| `CurrentApn` | `s` | Read | Active cellular APN profile. |

---

### 3.2 Unix Domain Socket Fallback (JSON-RPC 2.0)
For headless systems without a desktop D-Bus session bus, `misltyd` listens on:
`/run/user/$UID/mislty/mislty.sock` (mode `0600`).

Messages follow standard JSON-RPC 2.0 formatting:
```json
// Request from CLI:
{
  "jsonrpc": "2.0",
  "id": 42,
  "method": "SendSms",
  "params": {
    "recipient": "+88018XXXXXXXX",
    "text": "Hello from MisLTy headless socket!"
  }
}

// Response from Daemon:
{
  "jsonrpc": "2.0",
  "id": 42,
  "result": {
    "success": true,
    "message_reference": 128,
    "status": "SENT"
  }
}

// Asynchronous Notification (URC):
{
  "jsonrpc": "2.0",
  "method": "SmsReceived",
  "params": {
    "id": 14,
    "sender": "+88017XXXXXXXX",
    "timestamp": "2026-09-10 00:15:30",
    "text": "Your OTP code is 987654"
  }
}
```

---

## 4. Data Persistence & SQLite Schema

Because the onboard SIM card can only store ~100 messages (`AT+CPMS`) before rejecting incoming SMS with memory full errors, MisLTy implements a persistent, local SQLite storage engine located at:
`~/.local/share/mislty/mislty.db`

The database runs in **WAL (Write-Ahead Logging)** mode with foreign keys enabled to ensure concurrent read/write access between the daemon and GUI without database locking bottlenecks.

### 4.1 Schema DDL
```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

-- 1. Contacts Directory
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    msisdn TEXT NOT NULL UNIQUE,
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. Two-Way Message Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    peer_msisdn TEXT NOT NULL UNIQUE,
    contact_id INTEGER,
    last_message_at DATETIME NOT NULL,
    unread_count INTEGER DEFAULT 0,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE SET NULL
);

-- 3. Individual SMS Messages
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    direction TEXT CHECK(direction IN ('inbound', 'outbound')) NOT NULL,
    peer_msisdn TEXT NOT NULL,
    body TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    status TEXT CHECK(status IN ('pending', 'sent', 'delivered', 'failed', 'received')) NOT NULL,
    sim_index INTEGER,              -- NULL if purged from SIM or outgoing
    delivery_ref INTEGER,           -- +CMGS reference number for tracking
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);

-- 4. Session Network Accounting & Telemetry
CREATE TABLE IF NOT EXISTS session_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at DATETIME NOT NULL,
    ended_at DATETIME,
    gateway_mode TEXT NOT NULL,      -- 'default' or 'secondary'
    assigned_ip TEXT,
    rx_bytes_start INTEGER NOT NULL,
    tx_bytes_start INTEGER NOT NULL,
    rx_bytes_total INTEGER DEFAULT 0,
    tx_bytes_total INTEGER DEFAULT 0,
    operator TEXT,
    average_dbm REAL
);
```

### 4.2 SIM Memory Reconciliation Algorithm
To prevent SIM storage exhaustion while guaranteeing zero message loss:
1. **Detection**: Daemon traps unsolicited `+CMTI: "SM", <idx>` on `MI_01`.
2. **Fetch**: Daemon issues `AT+CMGR=<idx>`, extracting sender, timestamp, and message body.
3. **Persist**: Message is inserted into SQLite (`messages` and `conversations` tables) within a single transaction.
4. **Purge from Hardware**: Daemon immediately issues `AT+CMGD=<idx>` to free the hardware SIM slot.
5. **Broadcast**: `SmsReceived` signal is dispatched across D-Bus and Unix sockets.
6. **Recovery Sweep**: On cold daemon startup, daemon queries `AT+CMGL="ALL"`. Any unread messages left on the SIM from power-off periods are ingested into SQLite and purged.

---

## 5. Privilege Separation & System Integration

MisLTy enforces the **Principle of Least Privilege**:
* The daemon `misltyd`, CLI `mislty`, and GUI run as unprivileged regular user processes.
* No continuous `sudo` prompts or interactive root requirements during normal operation.

```
+-------------------------------------------------------------------------------+
| Regular User Space (No Root Privileges)                                       |
|                                                                               |
|   mislty-gui / mislty CLI / misltyd (UID: 1000)                               |
|   - Reads/Writes /dev/mislty/* via udev group 'uucp' (0666)                   |
|   - Reads sysfs /sys/class/net/ppp0/statistics/*                              |
|   - Maintains SQLite in ~/.local/share/mislty/mislty.db                       |
+---------------------------------------+---------------------------------------+
                                        |
                                        | Invokes via Polkit:
                                        | /usr/libexec/mislty-net-helper <action>
                                        v
+-------------------------------------------------------------------------------+
| Privileged Helper Execution (Root / Polkit Managed)                           |
|                                                                               |
|   Action: org.freedesktop.mislty.manage-connection                            |
|                                                                               |
|   Operations Authorized:                                                      |
|   1. Launch/Terminate pppd call ufi                                           |
|   2. Insert/Remove default route: ip route replace default dev ppp0 metric 50|
|   3. DNS Configuration: Update resolv.conf or call systemd-resolved           |
+-------------------------------------------------------------------------------+
```

### 5.1 Polkit Policy Definition
Installed at `/usr/share/polkit-1/actions/org.freedesktop.mislty.policy`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE policyconfig PUBLIC
 "-//freedesktop//DTD PolicyKit Policy Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/PolicyKit/1.0/policyconfig.dtd">
<policyconfig>
  <vendor>Purrfect Software Limited</vendor>
  <vendor_url>https://github.com/kuasha420/mislty</vendor_url>

  <action id="org.freedesktop.mislty.manage-connection">
    <description>Manage MisLTy Cellular Network Connections</description>
    <message>Authentication is required to start or stop the MisLTy cellular data link</message>
    <defaults>
      <allow_any>auth_admin</allow_any>
      <allow_inactive>auth_admin</allow_inactive>
      <allow_active>yes</allow_active>
    </defaults>
    <annotate key="org.freedesktop.policykit.exec.path">/usr/libexec/mislty-net-helper</annotate>
  </action>
</policyconfig>
```
*Notice that `<allow_active>yes</allow_active>` allows local, active desktop console users to connect and disconnect without prompting for a sudo password.*

### 5.2 Deterministic Routing & DNS Management
1. **Default Gateway Mode (`--default`)**:
   - `mislty-net-helper start-default` invokes `pppd call ufi` with `nodefaultroute`.
   - As soon as `ppp0` acquires an IP, the helper executes:
     `ip route replace default dev ppp0 metric 50`
   - Metric 50 takes precedence over standard Wi-Fi (metric 600) and Ethernet (metric 100), routing all host internet traffic through LTE without disrupting local LAN subnets.
2. **DNS Resolution**:
   - If `systemd-resolved` is active: Helper communicates over D-Bus with `org.freedesktop.resolve1` to configure carrier DNS on interface `ppp0`.
   - Fallback: Backs up `/etc/resolv.conf` to `/etc/resolv.conf.backup.ppp0` and atomically replaces it with carrier nameservers + `1.1.1.1`.
3. **Restoration**:
   - On disconnect, helper restores `/etc/resolv.conf` and deletes the metric 50 route.

---

## 6. Audio & Telephony Pipeline: The "Tragic Voice" Subsystem

Disassembly of `pcmWave.dll` established that interface `MI_02` (`/dev/mislty/voice` -> `/dev/ttyUSB2`) is a dedicated full-duplex digital audio streaming port operating at 115200 baud.

### 6.1 Audio Stream Specifications
* **Encoding Format**: Raw signed 16-bit little-endian linear PCM (`s16le`).
* **Sampling Rate**: **8000 Hz** (Mono).
* **Frame Size**: 2 bytes per sample.
* **Throughput**: 16,000 bytes/sec (128 kbps).
* **Linux Sound Server Integration**: Direct streaming into **PipeWire** via `pw-cat` (or PulseAudio via `pacat`).

### 6.2 Linux Audio Loopback Pipeline Architecture
```
+-------------------------------------------------------------------------------+
|                      MisLTy PCM Audio Streaming Loop                          |
|                                                                               |
|   /dev/mislty/voice        +------------------------+      +--------------+   |
|   (MI_02 @ 115200) =======>| Non-blocking Serial    |=====>| PipeWire     |   |
|   Raw 8kHz s16le           | Buffer Reader (640 B)  |      | pw-cat sink  |   |
|                            +------------------------+      +-------+------+   |
|                                                                    |          |
|                                                                    v          |
|                                                            Host Speakers /    |
|                                                            Headphones (Static)|
+-------------------------------------------------------------------------------+
```

### 6.3 Voice Signaling & Easter Egg State Machine
1. **User Initiates Call**: User types phone number into GUI dialer and clicks Call.
2. **Signaling Issued**: `misltyd` dispatches `ATD<phone_number>;` over `MI_01` (trailing semicolon mandatory for 3GPP voice).
3. **Carrier Behavior & 2026 CSFB Rejection**:
   - The modem requests Circuit-Switched Fallback (CSFB).
   - In Bangladesh in 2026, 3G is decommissioned.
   - The LTE MME inspects the device IMEI (`86117903...`) and NVRAM profile, recognizes an **EPS Data-Only Device**, and terminates the call setup with `NO CARRIER` or a 30s timeout.
4. **Error Trap**:
   - `misltyd` immediately issues `AT+CEER`.
   - The baseband reports: `+CEER: No service available` or `+CEER: No service`.
5. **Easter Egg Activation**:
   - `misltyd` emits D-Bus signal `CallStateChanged("CSFB_REJECTED", "<number>", "No service available")`.
   - The GUI launches the **"Tragic Voice" modal dialog**, featuring the feline ASCII lore of Misty, explaining the historical context of CSFB and VoLTE in 2026.
   - The dialog provides a **"Listen to 8kHz Carrier Static"** button which launches the `pw-cat` audio loopback on `MI_02` for 10 seconds.

---

## 7. UI/UX Technology Stack & Packaging Architecture

### 7.1 Framework Decision: PySide6 + Qt Quick Controls 2
* **Language & Runtime**: Python 3.10+ with **PySide6 (Qt 6.6+)**.
* **Rationale**:
  - Eliminates native C++ compilation during development and packaging.
  - Using **Qt Quick Controls 2** with custom Purrfect palette tokens gives 100% of the visual elegance of KDE Kirigami while eliminating hard dependencies on system KDE Frameworks 6 (`kirigami2`, `extra-cmake-modules`), enabling flawless execution on GNOME (Ubuntu/Fedora) and minimal window managers.
  - Native adherence to system theme palettes (Breeze Dark / Catppuccin).
* **System Tray**: Implemented via `QSystemTrayIcon` utilizing dynamically generated 5-bar signal strength SVG pixmaps overlaid with connection status indicators.

### 7.2 MicroSD Toolkit Self-Contained Deployment (`UFI_TOOLKIT`)
The onboard 32 GB MicroSDHC card contains two partitions:
1. `UFI_TOOLKIT` (1.0 GB FAT32, Partition 1): The zero-internet offline install directory.
2. `UFI_STORAGE` (31 GB FAT32/ext4, Partition 2): User files and personal media.

#### Staged Filesystem Layout on `UFI_TOOLKIT`:
```text
/media/$USER/UFI_TOOLKIT/
├── install.sh                          # 1-Click zero-internet installer
├── uninstall.sh                        # Clean uninstaller
├── mislty                              # Standalone frozen executable (PyInstaller)
├── mislty-daemon                       # Standalone daemon executable
├── mislty-net-helper                   # Privileged network helper
├── mislty.desktop                      # XDG Application Launcher
├── assets/
│   ├── mislty-cat.png                  # Application icon (Misty the Cat)
│   └── audio/
│       ├── purr.wav                    # Incoming SMS notification chime
│       └── connect.wav                 # Data link established chime
├── config/
│   ├── udev/
│   │   └── 99-ufi-permissions.rules    # Hardened udev rules
│   ├── ppp/
│   │   ├── chat-ufi
│   │   └── peers-ufi
│   ├── polkit/
│   │   └── org.freedesktop.mislty.policy
│   └── systemd/
│       └── mislty-daemon.service
└── docs/                               # Complete offline documentation
    ├── PRD.md
    └── TECHNICAL_DESIGN.md
```

#### Deterministic Execution Flow of `install.sh`:
```bash
#!/usr/bin/env bash
set -euo pipefail

echo "🐱 Installing MisLTy 4G Suite from MicroSD Toolkit..."

# 1. Install udev rules & trigger
sudo cp config/udev/99-ufi-permissions.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger

# 2. Install PPP peer and chat scripts
sudo mkdir -p /etc/ppp/peers
sudo cp config/ppp/chat-ufi /etc/ppp/chat-ufi
sudo cp config/ppp/peers-ufi /etc/ppp/peers/ufi

# 3. Install Polkit security policy
sudo cp config/polkit/org.freedesktop.mislty.policy /usr/share/polkit-1/actions/

# 4. Install executables
sudo cp mislty /usr/local/bin/mislty
sudo cp mislty-daemon /usr/local/bin/misltyd
sudo cp mislty-net-helper /usr/libexec/mislty-net-helper
sudo chmod 755 /usr/libexec/mislty-net-helper

# 5. Install Desktop entry & icons
mkdir -p ~/.local/share/applications ~/.local/share/icons/hicolor/256x256/apps
cp mislty.desktop ~/.local/share/applications/
cp assets/mislty-cat.png ~/.local/share/icons/hicolor/256x256/apps/mislty.png

# 6. Install & enable systemd user service
mkdir -p ~/.config/systemd/user
cp config/systemd/mislty-daemon.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mislty-daemon.service

echo "🎉 MisLTy installed successfully! Run 'mislty' or launch from desktop menu."
```

---

## 8. Work Breakdown Structure & Issue Filing Roadmap

With the architectural contracts established in this document, implementation can be divided into **18 targeted, self-contained, and testable engineering issues**:

```
+-----------------------------------------------------------------------------------+
|                           Issue Dependency Flow Graph                             |
+-----------------------------------------------------------------------------------+

   [Issue 1: Scaffolding & Packaging]
                 |
                 +-----------------------------------+
                 |                                   |
                 v                                   v
   [Issue 2: Port Resolver & Udev]       [Issue 5: SQLite Storage Engine]
                 |                                   |
                 v                                   |
   [Issue 3: Serial Transport & Parser]              |
                 |                                   |
                 v                                   |
   [Issue 4: URC Demuxer Engine]                     |
                 |                                   |
                 +-----------------+                 |
                 |                 |                 |
                 v                 v                 v
   [Issue 7: Polkit & Helper]    [Issue 6: Core Daemon Engine]
                 |                         |
                 v                         v
   [Issue 8: PPP Manager]        [Issue 9: D-Bus & Socket IPC]
                 |                         |
                 +-------------------------+
                             |
                             v
                 [Issue 10: Unified IPC Client]
                             |
                 +-----------+-----------+
                 |                       |
                 v                       v
   [Issue 11: Production CLI]   [Issue 13: Qt6 Shell & Theme]
                 |                       |
                 v                       +-------------------+
   [Issue 12: MicroSD Installer]         |                   |
                                         v                   v
                               [Issue 14: Dashboard]  [Issue 16: SMS Suite]
                                         |                   |
                                         v                   v
                               [Issue 15: Wi-Fi Deck] [Issue 17: Voice Easter Egg]
                                         |                   |
                                         +---------+---------+
                                                   |
                                                   v
                                      [Issue 18: AppImage & Verification]
```

### Issue Catalog (Ready for Issue Tracker Filing)

#### Phase 1: Core Foundation & Daemon Engine
1. **Issue #1: Project Scaffolding & Package Layout**
   - Setup `pyproject.toml`, establish `src/mislty/` package tree, configure pytest framework and linting.
2. **Issue #2: Deterministic Port Resolver & Hardened Udev Rules**
   - Implement `src/mislty/core/port_resolver.py` parsing `/dev/mislty/*` symlinks and sysfs interfaces.
3. **Issue #3: Non-Blocking Serial Transport & Hayes AT Parser**
   - Implement `serial_transport.py` and `at_parser.py` with priority command queue, timeouts, and error mapping.
4. **Issue #4: Asynchronous URC Demuxer Engine**
   - Implement `urc_demuxer.py` trapping `+CMTI`, `+CMGS`, `RING`, `+CLIP`, `+CEREG` asynchronously on `MI_01`.
5. **Issue #5: SQLite Storage Engine & SIM Reconciliation**
   - Implement `src/mislty/storage/` with WAL mode, schema migrations, and SIM-to-disk message purging.
6. **Issue #6: Core Daemon Engine & Connection Watchdog**
   - Build `misltyd` main asyncio loop, 2000ms RF telemetry polling, and exponential backoff auto-reconnect.

#### Phase 2: Networking, Security & IPC
7. **Issue #7: Polkit Security Policy & Privileged Network Helper**
   - Implement `/usr/libexec/mislty-net-helper` and Polkit policy for unprivileged execution of connection tasks.
8. **Issue #8: PPP Manager & Dual Routing Engine**
   - Implement `ppp_controller.py`, `route_manager.py` (metric 50), and `dns_manager.py` (`systemd-resolved` integration).
9. **Issue #9: D-Bus Interface & Unix Domain Socket IPC Server**
   - Implement `org.mislty.Modem` D-Bus service and `/run/user/$UID/mislty.sock` JSON-RPC server in `src/mislty/ipc/`.
10. **Issue #10: Unified IPC Client & Standalone Serial Fallback**
    - Build `src/mislty/ipc/client.py` transparently choosing D-Bus, Unix socket, or direct serial execution.

#### Phase 3: CLI Suite & MicroSD Bootstrap
11. **Issue #11: Production CLI Suite (`mislty`)**
    - Implement CLI commands (`status`, `connect`, `disconnect`, `wifi`, `sms`, `sim`, `at`) with formatted terminal output.
12. **Issue #12: MicroSD Offline Installer & Bootstrap Automation**
    - Write and verify `install.sh` and `uninstall.sh` on `UFI_TOOLKIT` for zero-internet 5-second setup.

#### Phase 4: Modern Desktop GUI & Telephony Easter Egg
13. **Issue #13: PySide6 Application Shell & Feline Theme System**
    - Set up Qt Quick Controls 2 application shell, window framing, and Purrfect feline color tokens in `Theme.qml`.
14. **Issue #14: GUI Dashboard & Live Telemetry Gauges**
    - Build `DashboardView.qml` with animated 5-bar signal meter, dBm readout, and real-time throughput graphs.
15. **Issue #15: GUI Wi-Fi Deck, QC-Webs Client Scraper & Smart Mode Switcher**
    - Build `WifiView.qml` with Dual-Plane state indicators, clean SSID/password editor, and NVRAM commit.
    - Implement `qcwebs_client.py` consuming `QC-Webs` GoForm API and `/json/refresh_data.asp` real-time telemetry stream (see [QC_WEBS_API_SPEC.md](file:///home/psl/Projects/ufi-modem/docs/QC_WEBS_API_SPEC.md)).
    - Implement Smart Mode Switcher (`SetWorkMode`) toggling between 57.9ms USB PPP mode and 4G Pocket Router mode in ~3.4s.
16. **Issue #16: GUI Split-Pane SMS Conversation Suite**
    - Build `SmsView.qml` with thread list, chat bubbles, 160-char GSM counter, and desktop notifications.
17. **Issue #17: Audio Bridge & "Tragic Voice" Telephony Easter Egg**
    - Implement `src/mislty/audio/` (PipeWire `pw-cat` loop on `MI_02`), dialer UI, and the CSFB rejection modal dialog.
18. **Issue #18: System Tray Applet & AppImage Packaging**
    - Implement `tray.py` with dynamic 5-bar icon and context menu; author PyInstaller spec and AppImage recipe.

---

## 9. Verification & Acceptance Criteria Traceability

| PRD Test Case | Component / Issue | Target Specification | Verification Method |
| :--- | :--- | :--- | :--- |
| `TC-DATA-01` | Issue #8 (`route_manager.py`) | Metric 50 default route over `ppp0` | Execute `mislty connect --default`. Verify `ip route show` has `default dev ppp0 metric 50` and internet traffic flows over LTE. |
| `TC-DATA-02` | Issue #8 (`route_manager.py`) | Secondary split route | Execute `mislty connect`. Verify host default route is untouched, `curl --interface ppp0 https://icanhazip.com` yields cellular IP. |
| `TC-WIFI-01` | Issue #6 / Issue #15 | Single-PDN Packet Multiplexing | Connect host via USB PPP with Wi-Fi enabled. Verify Wi-Fi client pings gateway (`192.168.100.1`) in <2ms, but pings to `8.8.8.8` drop. On PPP disconnect, Wi-Fi internet resumes in <2 seconds. |
| `TC-SMS-01` | Issue #4 / Issue #16 | Real-time URC alert | Send SMS to dongle. Verify daemon catches `+CMTI` on `MI_01` within 500ms, saves to SQLite, and displays desktop notification. |
| `TC-VOICE-01`| Issue #17 (`lore_engine.py`)| Tragic Voice easter egg | Dial number in UI. Verify call times out, daemon captures `+CEER: No service`, and Tragic Voice modal renders with carrier static test. |
| `TC-BOOT-01` | Issue #12 (`install.sh`) | Zero-internet bootstrap | Execute `install.sh` from MicroSD on fresh air-gapped machine. Verify full install in under 5 seconds with zero network downloads. |
| `TC-NFR-01`  | Issue #18 (`tray.py`) | Memory and CPU budget | Run GUI minimized to tray for 1 hour. Verify RSS < 45 MB and CPU < 0.2%. |
