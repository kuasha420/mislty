# Product Requirement Document (PRD)
## MisLTy Desktop Suite & MicroSD Toolkit
### *The Definitive Linux Management Suite & Offline Ecosystem for the Qualcomm MDM9600 / Aleka UV310 4G LTE Dongle*

```
  /\_/\  
 ( o.o )  MisLTy: "Software out of time, for hardware out of time."
  > ^ <   Keeper of Wisdom: Misty (PSL / Purrfect Software Limited)
```

---

| Metadata | Specification |
| :--- | :--- |
| **Document ID** | `PRD-MISLTY-2026-V1` |
| **Target Product** | MisLTy Desktop Suite & MicroSD Toolkit |
| **Target Hardware** | Aleka Incorporated UV310 (Qualcomm MDM9600 / Broadcom BRCM_WL) |
| **USB Identifiers** | Boot/ZeroCD: `05c6:f000` ➔ Switched Modem: `05c6:6000` |
| **Target Release** | v1.0.0 *"Keeper of Wisdom"* |
| **Target Platforms** | Linux Kernel 4.x – 7.x (KDE Plasma 6 / Kirigami / Qt6, GNOME, Headless) |
| **Author / Guild** | Purrfect Software Limited (PSL) Systems Architecture Guild |
| **Canonical Repo** | [https://github.com/kuasha420/mislty](https://github.com/kuasha420/mislty) |
| **Document Status** | `APPROVED FOR IMPLEMENTATION` |

---

## 1. Executive Summary & Philosophical Vision

### 1.1 The Lore of MisLTy
> *"The almost perfect software for hardware that outlasted its time. And the only thing keeping it from 100% is that nobody started the research five years ago. Software out of time, for hardware out of time — both legendary, yet forever one PR away from completion."*

Around 2014–2016, millions of generic 4G LTE USB dongles flooded the global electronics market. When plugged into Windows machines of that era, they presented an emulated SCSI CD-ROM containing proprietary drivers, triggered an automatic modeswitch with the familiar Windows USB chime, and exposed a proprietary Win32 MFC dashboard (`App.exe`) toggling between "Wireless Modem" and "USB Modem".

On Linux, however, they were an unmitigated catastrophe. No network interface (`ethX`, `usb0`, or `wwan0`) ever appeared. Desktop connection daemons (`ModemManager`) crashed in segmentation fault loops when querying the multi-port serial interfaces. The dongle would silently drop into an isolated Wi-Fi access point mode, forcing Linux users to buy separate USB Wi-Fi adapters just to connect to the dongle sitting directly in their computer's USB port. Millions of these devices were subsequently abandoned in drawers as "Linux-incompatible e-waste."

In 2026, one such forgotten device was pulled from storage for a weekend deep-dive reverse-engineering marathon. Through USB descriptor tracing, disassembly of OEM Windows binaries (`ATManager.dll`, `InitHW.dll`, `pcmWave.dll`), AT command probing (`AT+CLAC`), and RF telemetry logging, the complete ground truth was uncovered.

The hardware was neither cheap nor broken. It was an engineering marvel trapped by abandoned software:
- **`Misty` & The Feline Origin**: In 2018, the founder adopted their first cat—**Misty**—sparking a deep feline fascination that laid the philosophical foundations of **Purrfect Software Limited (PSL)**. Misty now reigns as the *Keeper of Wisdom* across the Purrfect Universe. The WPA2 passphrase (`misty-6969`) recovered directly from the baseband's NVRAM (`AT^WFPWD?`) was the very last credential configured on this dongle in 2018 before its owner switched permanently to Linux and relegated the hardware to darkness.
- **`LTE`**: A genuine Qualcomm Gobi MDM9600 Category 3 cellular data engine, capable of 100 Mbps downlink, humming along at maximum signal (31/31, -51 dBm on Robi 4G Band 3).
- **`Missed`**: The missed call, the missed fallback, the missed connection (`+CEER: No service`). A full cellular voice subsystem reverse-engineered down to its 8000 Hz 16-bit mono linear PCM audio streaming pipeline (`pcmWave.dll`) and telephony state machines, only to be rejected at the network edge in 2026 because 3G was decommissioned in Bangladesh and 4G data dongles lack carrier VoLTE/IMS provisioning (`</3`).

### 1.2 Mission Statement
The **MisLTy Desktop Suite & MicroSD Toolkit** exists to redeem this hardware. We provide a modern, ultra-reliable, zero-bloat Linux environment that unlocks the dongle's full concurrent dual-mode potential (simultaneous USB PPP + Broadcom Wi-Fi), provides rich two-way SMS messaging, exposes deep RF telemetry, pays tribute to the tragic voice architecture through a lore-accurate Easter egg, and enables a 100% offline, zero-internet first-plug experience delivered directly from the onboard 32 GB MicroSD card.

### 1.3 Target Personas
1. **The Linux Sysadmin & DevOps Engineer**: Needs an indestructible, scriptable, out-of-band cellular backup link for servers or field laptops. Demands raw terminal visibility, deterministic routing, systemd service management, and zero desktop daemon dependencies.
2. **The Retro-Hardware & Cellular Hacker**: Driven by curiosity. Appreciates baseband architecture, QCDM diagnostic registers, Hayes AT command sets, and the poetic archaeology of resurrecting abandoned silicon.
3. **The Digital Nomad & Off-Grid Explorer**: Travels to remote areas with fluctuating cellular coverage. Needs an autonomous portable Wi-Fi hub that simultaneously feeds a wired Linux workstation with low latency while distributing connectivity to mobile devices, completely self-bootstrapping from the dongle itself.

### 1.4 Guiding Design Principles
- **Zero-Internet Self-Sufficiency**: The suite must be entirely installable and operational without an active internet connection. Everything required lives on the dongle's MicroSD card.
- **Direct Serial Sovereignty**: Bypass generic desktop abstractions that crash on composite modems. Communicate directly with `/dev/ttyUSB*` ports using non-blocking asynchronous Python/Qt architectures.
- **Concurrent Dual-Mode by Default**: Treat simultaneous USB PPP host data and Broadcom Wi-Fi AP broadcasting as standard operating procedure, never an either/or compromise.
- **Radical Telemetry Transparency**: Expose raw signal strength (RSSI and dBm), frequency bands, cell registration vectors, and extended error diagnostics (`AT+CEER`) directly to the user.
- **Reverence for the Lore**: Infuse the software with the warmth, wit, and feline elegance of the Purrfect Universe and Misty the cat.

---

## 2. Technical Ground Truth & Hardware Architecture

### 2.1 Hardware Specification
The target device is an **Aleka Incorporated UV310** (board revision `UV310-U-5.1 CGWL`) incorporating a multi-processor cellular architecture:

```
+-------------------------------------------------------------------------------+
|                       Aleka UV310 USB 4G UFI Dongle                           |
|                                                                               |
|   +--------------------------+          SDIO Bus         +----------------+   |
|   |  Qualcomm MDM9600 SoC    |<------------------------->| Broadcom       |   |=== 2.4 GHz
|   |  - Dual-Core AMSS/REX    |                           | BRCM_WL Radio  |   |    Wi-Fi AP
|   |  - Cat 3 LTE (100M/50M)  |                           | - 802.11b/g/n  |   |    (b/g/n)
|   |  - Native USB 2.0 PHY    |                           | - Internal DHCP|   |
|   +-------------+------------+                           +----------------+   |
|                 |                                                             |
|                 +-------------------+ Qualcomm Integrated SDCC MMC            |
|                 |                   |                                         |
|         +-------+-------+   +-------+-------+                                 |
|         | Standard SIM  |   | 32GB MicroSDHC|                                 |
|         | Slot (2FF)    |   | Slot (FAT32)  |                                 |
|         +---------------+   +---------------+                                 |
+-----------------+-------------------------------------------------------------+
                  | USB 2.0 High-Speed (480 Mbps)
                  v
       +--------------------+
       |  Linux Host PC     |
       +--------------------+
```

### 2.2 USB Enumeration & Two-Phase State Machine
The dongle utilizes Qualcomm's ZeroCD architecture to deliver drivers on legacy operating systems:

```
+-----------------------------------------------------------------------+
| Phase 1: ZeroCD State (Cold Boot / Power Insertion)                   |
| USB ID: 05c6:f000 | Class: Mass Storage (SCSI CD-ROM /dev/sr0, 3.1MB) |
+-----------------------------------+-----------------------------------+
                                    |
                                    | Host issues SCSI Eject / Switch Packet:
                                    | "5553424308306384c00000008000067103000000..."
                                    v
+-----------------------------------------------------------------------+
| Hardware USB PHY Reset & Re-Enumeration (1.2s bus debounce)           |
+-----------------------------------+-----------------------------------+
                                    |
                                    v
+-----------------------------------------------------------------------+
| Phase 2: Operational Modem Composite State                            |
| USB ID: 05c6:6000 | Class: Vendor-Specific Composite (5 Interfaces)   |
+-----------------------------------------------------------------------+
```

### 2.3 5-Interface Multi-Port Map (Post-Modeswitch `05c6:6000`)
The Linux kernel `option.ko` driver binds to interfaces 0–3, while `usb-storage` binds to interface 4:

| Interface | USB Endpoints | Linux Node | Driver | Official Qualcomm INF Name | Architectural Function in MisLTy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`MI_00`** | `EP1 IN (0x81 Interrupt)`<br>`EP2 IN (0x82 Bulk)`<br>`EP1 OUT (0x01 Bulk)` | `/dev/ttyUSB0` | `option` | `Qualcomm USB Modem 6000` | **Primary Data Plane**: Dedicated to `pppd` dialup (`ATD*99#`). Enters raw HDLC PPP packet mode at 100 Mbps PHY rate. |
| **`MI_01`** | `EP3 IN (0x83 Bulk)`<br>`EP2 OUT (0x02 Bulk)` | `/dev/ttyUSB1` | `option` | `Qualcomm Command Control Port` | **Asynchronous Control & Signaling**: Dedicated daemon channel for AT queries, RSSI telemetry, Wi-Fi control, and inbound URCs (`+CMTI`, `+CMGS`, `RING`). |
| **`MI_02`** | `EP4 IN (0x84 Bulk)`<br>`EP3 OUT (0x03 Bulk)` | `/dev/ttyUSB2` | `option` | `Qualcomm Voice Device Port` | **Voice Audio PCM Pipeline**: Bidirectional raw 16-bit 8000 Hz linear PCM audio stream (`pcmWave.dll` audio bridge). |
| **`MI_03`** | `EP5 IN (0x85 Bulk)`<br>`EP4 OUT (0x04 Bulk)` | `/dev/ttyUSB3` | `option` | `Qualcomm DM Service Port` | **Qualcomm Diagnostic Monitor (QCDM)**: Low-level binary protocol for baseband NVRAM diagnostics and RF calibration. |
| **`MI_04`** | `EP6 IN (0x86 Bulk)`<br>`EP5 OUT (0x05 Bulk)` | `/dev/sda` | `usb-storage` | `USB Mass Storage Device` | **Storage Subsystem**: 32 GB MicroSDHC card controller hosting the offline toolkit and user files. |

> [!IMPORTANT]
> Port indices (`/dev/ttyUSB0..3`) can shift if other serial adapters are present. MisLTy must resolve interfaces deterministically using `udev` sysfs symlinks (`/dev/mislty/modem`, `/dev/mislty/control`, `/dev/mislty/voice`, `/dev/mislty/diag`) mapped via `KERNELS=="...:1.0"` through `...:1.3`.

---

## 3. System Architecture & Daemon Design

### 3.1 Multi-Process Daemon Architecture
To guarantee that high-speed data transmission over PPP never interferes with real-time SMS delivery or telemetry polling, MisLTy implements a multi-threaded, asynchronous daemon architecture:

```
+---------------------------------------------------------------------------------------+
|                                    MisLTy Suite                                        |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   |                       MisLTy Core Daemon (`misltyd`)                          |   |
|   |                                                                               |   |
|   |   +------------------------+  +--------------------+  +-------------------+   |   |
|   |   | Port Coordinator &     |  | Unsolicited Event  |  | IPC Server        |   |   |
|   |   | Command Queue (MI_01)  |  | Listener (MI_01)   |  | (Unix Socket /    |   |   |
|   |   | - 2000ms CSQ Telemetry |  | - +CMTI (New SMS)  |  |  D-Bus Interface) |   |   |
|   |   | - Wi-Fi AP Toggle      |  | - +CMGS (Receipts) |  +---------+---------+   |   |
|   |   | - SMS Dispatcher       |  | - RING / +CLIP     |            |             |   |
|   |   +-----------+------------+  +---------+----------+            |             |   |
|   +---------------|-------------------------|-----------------------|-------------+   |
|                   |                         |                       |                 |
|                   v                         v                       v                 |
|          +-----------------+       +-----------------+     +-----------------+        |
|          | /dev/ttyUSB1    |       | Kernel Event    |     | Desktop UI      |        |
|          | (Control Port)  |       | Dispatch Bus    |     | (KDE Kirigami)  |        |
|          +-----------------+       +--------+--------+     | or CLI Client   |        |
|                                             |              +-----------------+        |
|   +---------------------------------+       |                                         |
|   | Network Subsystem               |       |                                         |
|   |                                 |       |                                         |
|   |   +-------------------------+   |       |                                         |
|   |   | PPP Process Manager     |   |       |                                         |
|   |   | - Spawns pppd on MI_00  |   |       |                                         |
|   |   | - /dev/ttyUSB0          |<--+       |                                         |
|   |   | - Monitors ppp0 status  |           |                                         |
|   |   +------------+------------+           |                                         |
|   |                |                        |                                         |
|   |                v                        |                                         |
|   |          +------------+                 |                                         |
|   |          |    ppp0    |                 |                                         |
|   |          +------------+                 |                                         |
|   +-----------------------------------------+                                         |
|                                                                                       |
|   +-------------------------------------------------------------------------------+   |
|   | Audio & Easter Egg Subsystem                                                  |   |
|   |                                                                               |   |
|   |   +-------------------------+            +--------------------------------+   |   |
|   |   | PCM Audio Bridge        |<---------->| /dev/ttyUSB2 (MI_02 Voice Port)|   |   |
|   |   | - 8000 Hz 16-bit Mono   |            +--------------------------------+   |   |
|   |   | - PipeWire / ALSA Loop  |                                                 |   |
|   |   +-------------------------+                                                 |   |
|   +-------------------------------------------------------------------------------+   |
+---------------------------------------------------------------------------------------+
```

### 3.2 Threading & Non-Blocking Serial Isolation
1. **Primary Control Channel (`MI_01` Worker)**:
   - Maintains an open file descriptor on `/dev/ttyUSB1` (`115200 8N1`, raw termios mode).
   - Utilizes `select()` / `poll()` with non-blocking I/O.
   - Enforces a serial command mutex so user-initiated actions (e.g., sending an SMS, changing Wi-Fi password) wait cleanly for any pending telemetry poll cycle (`AT+CSQ`) to finish.
2. **Unsolicited Response Code (URC) Demuxer**:
   - `MI_01` concurrently emits asynchronous network alerts.
   - The stream parser detects `+CMTI: "SM",<idx>`, `+CMGS: <seq>`, and `RING` even while idle.
   - Immediately dispatches internal signals across the IPC bus without interrupting other processes.
3. **Data Channel (`MI_00` Worker)**:
   - Completely decoupled from the control thread.
   - Operated exclusively by the kernel `pppd` daemon during active data calls.

### 3.3 Linux Networking & Subsystem Integration
- **Direct PPP Dialup**: Avoids high-overhead virtual Ethernet encapsulation. Executes `pppd` with custom, hardware-tuned configuration:
  - Disables LCP/IPCP compression incompatible with Qualcomm 3GPP baseband (`noccp`, `novj`, `novjccomp`).
  - Utilizes hardware flow control (`crtscts`).
  - Strict chat termination (`CONNECT \c`) to prevent CR/LF injection into the HDLC frame stream.
- **Dual Routing Modes**:
  1. *Primary Gateway Mode*: Injects `defaultroute replacedefaultroute`, setting `ppp0` as the system's primary internet gateway (metric 50).
  2. *Secondary Split Mode*: Uses `nodefaultroute`. Local Ethernet and Wi-Fi remain active; `ppp0` is exposed as an auxiliary interface accessible via `curl --interface ppp0` or policy-based routing (`ip rule`).
- **DNS Handling**: Parses assigned carrier DNS servers from `ipcp-accept-remote` and updates `/etc/resolv.conf`, `resolvconf`, or `systemd-resolved` via D-Bus.
- **ModemManager Coexistence & Immunity**:
  - Implements udev rules tagging the hardware with:
    ```udev
    ENV{ID_MM_DEVICE_IGNORE}="1"
    ENV{NM_UNMANAGED}="1"
    ```
  - Permanently prevents ModemManager from probing `05c6:6000`, eliminating the historical `SIGSEGV` in `g_hash_table_lookup`.

---

## 4. Detailed Functional Requirements

```
+---------------------------------------------------------------------------------------+
|                               MisLTy Functional Modules                                |
|                                                                                       |
|   +---------------------+   +---------------------+   +---------------------------+   |
|   | FR-1: Cellular Data |   | FR-2: Wi-Fi Deck    |   | FR-3: SMS Suite           |   |
|   | - 1-Click Connect   |   | - Radio Power Toggle|   | - Split-Pane Threading    |   |
|   | - Auto-Reconnect    |   | - SSID & Passphrase |   | - Real-Time +CMTI Push    |   |
|   | - RF Telemetry/dBm  |   | - NVRAM Sync        |   | - 160-Char Limit / GSM7   |   |
|   +---------------------+   +---------------------+   +---------------------------+   |
|                                                                                       |
|   +---------------------+   +---------------------+   +---------------------------+   |
|   | FR-4: Tragic Voice  |   | FR-5: MicroSD Bundle|   | FR-6: AT Diagnostics      |   |
|   | - PCM Audio Pipe    |   | - Zero-Internet Boot|   | - Raw Serial Terminal     |   |
|   | - CSFB Lore Modal   |   | - 1-Click install.sh|   | - Command Auto-Complete   |   |
|   | - 8000Hz Static Test|   | - Partition Layout  |   | - NVRAM & Band Registers  |   |
|   +---------------------+   +---------------------+   +---------------------------+   |
+---------------------------------------------------------------------------------------+
```

### FR-1: Cellular Data Manager
- **FR-1.1: One-Click Connection Lifecycle**:
  - Provide instantaneous Connect and Disconnect triggers from both UI and CLI (`mislty connect`, `mislty disconnect`).
  - Transition modem state cleanly: `ATH` ➔ configure PDP context `AT+CGDCONT=1,"IP","<APN>"` ➔ launch `pppd call ufi` ➔ poll sysfs for `ppp0` `UP` state.
  - On disconnection, issue `SIGTERM` to `pppd`, assert DTR drop, and verify baseband returns to command mode with `ATH`.
- **FR-1.2: Dual-Routing Gateway Selector**:
  - Provide a toggle in UI/CLI between **Default Gateway** (`defaultroute`) and **Secondary Link** (`nodefaultroute`).
  - In Secondary Link mode, keep host Wi-Fi/Ethernet intact while displaying the allocated cellular IP (`10.x.x.x`) for multi-homed routing.
- **FR-1.3: Resilient Auto-Reconnect Engine**:
  - Background watchdog monitoring PPP link state and LCP echo responses (`lcp-echo-interval 5`, `lcp-echo-failure 3`).
  - If carrier drops link, trigger exponential backoff reconnection (1s, 2s, 4s, 8s, up to max 30s) with user-configurable retry limits.
- **FR-1.4: APN Profile Management**:
  - Built-in APN library with automated auto-detection from SIM IMSI (`AT+CIMI`):
    - *Robi / Airtel (Bangladesh)*: `internet`
    - *Teletalk (Bangladesh)*: `teletalk`
    - *Grameenphone (Bangladesh)*: `gpinternet`
    - *Banglalink (Bangladesh)*: `blweb`
    - Custom APN entry with optional PAP/CHAP username and password support (`AT$QCPDPP`).
  - Synchronizes APN to baseband volatile PDP context (`AT+CGDCONT`) and NVRAM default (`AT^APN=<name>`).
- **FR-1.5: Real-Time RF Telemetry & Signal Engine**:
  - Query `AT+CSQ` every 2000ms over `MI_01`.
  - Calculate true RF power in dBm using the 3GPP formula:
    $$\text{dBm} = -113 + (2 \times \text{RSSI})$$
    *(Range: $0 = -113\text{ dBm}$ to $31 = -51\text{ dBm}$, with $99 = \text{Unknown/No Signal}$)*.
  - Map RSSI to a 5-bar visual indicator:
    - 5 Bars: RSSI 25–31 (-63 to -51 dBm) [Excellent / Full Signal]
    - 4 Bars: RSSI 19–24 (-75 to -65 dBm) [Good]
    - 3 Bars: RSSI 13–18 (-87 to -77 dBm) [Fair]
    - 2 Bars: RSSI 7–12 (-99 to -89 dBm) [Poor]
    - 1 Bar: RSSI 1–6 (-111 to -101 dBm) [Marginal]
    - 0 Bars: RSSI 0 or 99 [No Service]
  - Query active network operator via `AT+COPS?` and EPS registration status via `AT+CEREG?` (`1 = Registered Home`, `5 = Registered Roaming`).
- **FR-1.6: Traffic & Bandwidth Accounting**:
  - Direct real-time polling of Linux kernel sysfs counters:
    `/sys/class/net/ppp0/statistics/rx_bytes` and `/sys/class/net/ppp0/statistics/tx_bytes`.
  - Display live RX/TX throughput graphs (KB/s, MB/s) and session cumulative data usage.

---

### FR-2: Broadcom Wi-Fi Deck
- **FR-2.1: Hotspot Power Toggle ("Dual Mode" vs "Pure USB")**:
  - Control the Broadcom `BRCM_WL` co-processor directly via AT commands:
    - Enable Hotspot (`AT+WIFI=1`): Powers up 2.4 GHz radio, launches internal DHCP server (`192.168.100.1` pool), and broadcasts SSID.
    - Disable Hotspot (`AT+WIFI=0`): Shuts down Broadcom radio entirely.
  - Power-saving benefit: Saves 200–300 mA of USB bus power when running mobile on a laptop battery. Zero RF emissions when purely tethered.
- **FR-2.2: SSID & WPA2 Passphrase Management**:
  - Query current SSID with `AT^SSID?` and WPA2 Pre-Shared Key with `AT^WFPWD?`.
  - Configure new SSID (`AT^SSID="<NewSSID>"`) and passphrase (`AT^WFPWD="<NewPassword>"`).
  - Enforce WPA2 standard password rules (minimum 8 characters, maximum 63 characters).
  - Provide a "Show/Hide Password" eye-toggle in the UI.
- **FR-2.3: Baseband NVRAM Permanent Commit**:
  - Issue `AT+WRWIFI` to flush modified Wi-Fi configuration directly to persistent flash NVRAM, surviving physical power cycles.
- **FR-2.4: Wi-Fi RF Diagnostics**:
  - Read operational mode (`AT^WIMODE?` ➔ `4 = AP Mode`).
  - Read frequency band (`AT^WIBAND?` ➔ `0 = 2.4 GHz`).
  - Read active channel and frequency (`AT^WIFREQ?` ➔ `2412 MHz = Channel 1`, `2462 MHz = Channel 11`).

---

### FR-3: SMS Communication Suite
- **FR-3.1: Two-Way Messaging Protocol Stack**:
  - Force ASCII Text Mode on initialization: `AT+CMGF=1`.
  - Set SMS text parameters to 3GPP standard: `AT+CSMP=17,167,0,0`.
  - Configure LTE packet-switched SMS preference: `AT+CGSMS=2`.
  - Select SIM card storage: `AT+CPMS="SM","SM","SM"`.
- **FR-3.2: Real-Time Inbound SMS Interception (`+CMTI`)**:
  - The background listener on `MI_01` traps unsolicited notifications:
    ```text
    +CMTI: "SM", <index>
    ```
  - Daemon immediately issues `AT+CMGR=<index>`, decodes the sender number, timestamp, and message body.
  - Plays optional feline alert chime ("purr" or "meow" notification sound) and dispatches a desktop notification via `org.freedesktop.Notifications`.
  - Appends message to the active conversation thread in real time without requiring a manual inbox refresh.
- **FR-3.3: Split-Pane Modern Conversation UI**:
  - Left pane: Chronological list of message threads grouped by sender/recipient MSISDN, displaying contact name/number, last message snippet, timestamp, and unread badge count.
  - Right pane: Active chat conversation with alternating message bubbles (incoming on left, outgoing on right), timestamps, delivery status ticks, and context menu (Copy Text, Delete Message, Forward).
- **FR-3.4: Message Composer & 160-Character Limit Engine**:
  - Real-time character counter showing remaining characters in standard 7-bit GSM-03.38 alphabet (160 characters).
  - Multi-part SMS warning indicator: When text exceeds 160 characters, indicates segment breakdown (e.g., `161/306 (2 Parts, 153 chars/segment)`).
  - Keyboard shortcut: `Ctrl+Enter` or `Enter` (configurable) to transmit.
- **FR-3.5: Transmission Dispatcher & Delivery Confirmation**:
  - Transmits message via `AT+CMGS="<Recipient>"`, monitors for modem `>` prompt, streams payload followed by `0x1A` (Ctrl+Z).
  - Traps `+CMGS: <mr> OK` response to record successful OTA submission.
  - Deletes messages from SIM memory (`AT+CMGD=<index>`) when deleted by user, preventing SIM memory exhaustion (100 message limit).
- **FR-3.6: Conversation Backup & Export**:
  - Export entire inbox/outbox history to structured JSON or CSV format.

---

### FR-4: The "Tragic Voice" Easter Egg / Telephony Interface

#### 4.1 Technical Reverse-Engineering Summary (`pcmWave.dll`)
Disassembly of `pcmWave.dll` established that Qualcomm interface `MI_02` (`/dev/ttyUSB2`) is a dedicated full-duplex digital audio streaming port operating at 115200 baud.

```
+-------------------------------------------------------------------------------+
|                    pcmWave.dll Reverse-Engineered Pipeline                    |
|                                                                               |
|   /dev/ttyUSB2          +--------------------+         +------------------+   |
|   Raw Serial In  =====> |  CWaveInSerial     | ======> |  Linux Speakers  |   |
|   (115200 baud)         |  (Buffer Rx)       |         |  (PipeWire/ALSA) |   |
|                         +--------------------+         +------------------+   |
|                                                                               |
|   /dev/ttyUSB2          +--------------------+         +------------------+   |
|   Raw Serial Out <===== |  CWaveOutSerial    | <====== |  Linux Mic       |   |
|   (115200 baud)         |  (Buffer Tx)       |         |  (PipeWire/ALSA) |   |
|                         +--------------------+         +------------------+   |
+-------------------------------------------------------------------------------+
```

- **Audio Characteristics**:
  - Audio Encoding: Raw linear 16-bit Signed Little-Endian PCM (`s16le`).
  - Sampling Rate: **8000 Hz** (`0x1F40` in `WAVEFORMATEX`).
  - Channels: 1 (Mono).
  - Byte Rate: 16,000 bytes/sec.
  - Protocol: Unframed binary PCM streaming directly over USB Bulk endpoints.

#### 4.2 Telephony Signaling Protocol
- Outbound Call: `ATD<phone_number>;` on `MI_01` (trailing semicolon mandatory for voice).
- Inbound Call Alert: `RING` and `+CLIP: "<number>",129,,,,0` emitted on `MI_01`.
- Answer: `ATA`.
- Hangup: `ATH` or `AT+CHUP`.
- In-Call DTMF: `AT+VTS=<digit>`.

#### 4.3 Modern Carrier Reality & The 2026 CSFB Rejection
In 2026, 3G UMTS networks have been decommissioned across Bangladesh (Robi, Teletalk, Grameenphone), and 4G LTE is an all-IP packet architecture lacking legacy circuit-switched voice channels.

Because generic MDM9600 data dongles lack carrier-certified VoLTE/IMS firmware profiles, any voice call attempt on LTE triggers Circuit-Switched Fallback (CSFB). When the LTE MME receives the request, it checks the device's IMEI (`86117903...`) and NVRAM profile, discovers an **EPS Data-Only Device**, and abruptly rejects the voice bearer with:
```text
AT+CEER
+CEER: No service available
```

#### 4.4 The Lore-Accurate Easter Egg UI Specification
MisLTy must not treat this failure as an ugly crash or an unexplained network error. Instead, it transforms this technical truth into a poignant narrative experience:

1. **The Telephony Interface**:
   - Features a clean, retro-futuristic phone dialer with a standard 12-key numeric keypad (`0-9`, `*`, `#`), number entry field, and Call/Hangup buttons.
   - Includes a live volume VU-meter displaying audio activity on `/dev/ttyUSB2`.
   - Includes a **"Static & Loopback Test"** button that bridges `MI_02` directly to the system default audio sink via PipeWire (`pw-cat --playback --rate 8000 --channels 1 --format s16`) to let the user listen to the raw 8000 Hz Qualcomm audio carrier static.
2. **The "Tragic Voice" Dialog (`</3`)**:
   - When a call attempt inevitably terminates in `NO CARRIER` or a 30-second timeout, the daemon queries `AT+CEER`.
   - Upon detecting `+CEER: No service available` or `+CEER: No service`, the dialer transitions into an elegant, melancholic dialog box:

```
+-----------------------------------------------------------------------+
|  💔 The Tragic Voice of MisLTy                                    [X] |
+-----------------------------------------------------------------------+
|                                                                       |
|      |\_/\_.-""'''-.                                                  |
|     ( o.o )         \    "A missed call, a missed connection..."      |
|      =(_)=  \       |                                                 |
|             / /---/ /    Cause: +CEER: No service available           |
|                                                                       |
|  You have touched the ghost in the machine.                           |
|                                                                       |
|  In 2014, this Qualcomm MDM9600 was engineered to stream 8000 Hz      |
|  16-bit linear PCM voice calls directly over /dev/ttyUSB2.            |
|                                                                       |
|  In 2026, modern 4G LTE MME networks have silenced 3G fallback,      |
|  demanding carrier-provisioned VoLTE profiles this abandoned data     |
|  stick will never possess.                                            |
|                                                                       |
|  Software out of time, for hardware out of time.                      |
|  Forever one PR away from completion.                                 |
|                                                                       |
|  [ 🎧 Listen to 8kHz Carrier Static ]         [ Close with Reverence ]|
+-----------------------------------------------------------------------+
```

---

### FR-5: MicroSD Self-Contained Deployment ("Zero-Internet" First-Plug)

#### 5.1 Storage Controller Ground Truth
- Host Controller: Qualcomm integrated SDCC MMC host controller.
- Specification Standard: **SDHC v2.00 (Maximum 32 GB)**.
- Bus Mode: High Speed (HS) 3.3V, 50 MHz bus clock.
- Real-world Throughput: Read ~14–18 MB/s, Write ~8–12 MB/s over USB 2.0 Bulk-Only mass storage.
- Unsupported: SDXC cards (64GB+) and exFAT will fail due to boot ROM addressing limits.

#### 5.2 MicroSD Partition Architecture
The 32 GB MicroSD card is formatted into two distinct partitions:

```
+-------------------------------------------------------------------------------+
|                       32 GB MicroSDHC Card Partition Layout                   |
|                                                                               |
|   +------------------------------------+----------------------------------+   |
|   | Partition 1: UFI_TOOLKIT (1.0 GB)  | Partition 2: UFI_STORAGE (31 GB) |   |
|   | Filesystem: FAT32 (Cross-Platform) | Filesystem: FAT32 or ext4        |   |
|   | Label: "UFI_TOOLKIT"               | Label: "UFI_STORAGE"             |   |
|   | Read-Only Recommended / System     | Read-Write / User Files          |   |
|   +------------------------------------+----------------------------------+   |
+-------------------------------------------------------------------------------+
```

#### 5.3 `UFI_TOOLKIT` File Structure
```
/media/$USER/UFI_TOOLKIT/
├── install.sh                          # Universal 1-Click zero-internet setup script
├── uninstall.sh                        # Clean uninstaller script
├── mislty                              # Standalone compiled binary (PyInstaller/Nuitka)
├── mislty.desktop                      # XDG Desktop Menu entry
├── assets/
│   ├── mislty-cat.png                  # Application icon (Misty the Cat)
│   └── audio/                          # Purr and notification sound assets
├── config/
│   ├── udev/
│   │   └── 99-ufi-permissions.rules    # udev permission and MM-ignore rules
│   └── ppp/
│       ├── chat-ufi                    # Optimized cellular chatscript
│       └── peers-ufi                   # Optimized cellular pppd options
├── systemd/
│   └── mislty-daemon.service           # systemd user service unit
└── docs/                               # Complete offline markdown & HTML documentation
    ├── PRD.md
    ├── HARDWARE_SPEC.md
    └── AT_COMMAND_REFERENCE.md
```

#### 5.4 The "Zero-Internet" Automated Setup Flow (`install.sh`)
When plugged into any fresh or disconnected Linux PC:
1. Card automounts under `/media/` or `/run/media/$USER/UFI_TOOLKIT`.
2. User opens terminal and runs:
   ```bash
   bash /run/media/$USER/UFI_TOOLKIT/install.sh
   ```
3. The script executes the following deterministic steps in under 3 seconds:
   - Copies `config/udev/99-ufi-permissions.rules` to `/etc/udev/rules.d/`.
   - Reloads and triggers udev rules (`udevadm control --reload-rules && udevadm trigger`).
   - Copies `config/ppp/chat-ufi` to `/etc/ppp/chat-ufi` and `config/ppp/peers-ufi` to `/etc/ppp/peers/ufi`.
   - Copies `mislty` executable to `/usr/local/bin/mislty`.
   - Installs `mislty.desktop` and `mislty-cat.png` into standard XDG directories (`~/.local/share/applications/` and `~/.local/share/icons/`).
   - Enables the optional background daemon service: `systemctl --user enable --now mislty-daemon`.
4. The system is immediately ready to connect with `mislty connect` or by clicking the desktop icon. No package manager, compile step, or internet access required.

---

### FR-6: Embedded Diagnostics & AT Console
- **FR-6.1: Interactive Raw Serial Terminal**:
  - Embedded serial console bound to `MI_01` (or user-selectable port).
  - Handles line buffering, CR/LF conversions, and displays raw TX/RX with millisecond timestamps.
- **FR-6.2: Intelligent Auto-Complete & Syntax Help**:
  - Command palette containing all ~150 reverse-engineered commands from `AT_COMMAND_REFERENCE.md`.
  - Typing `AT^` displays suggestions: `AT^SSID?`, `AT^WFPWD?`, `AT^PROJECTNAME?`, `AT^HWVER?`, `AT^SWVER?`, `AT^CARDLOCK?`.
  - Inline tooltip showing command description, expected arguments, and response format.
- **FR-6.3: Baseband & Hardware Telemetry Inspector**:
  - Dedicated GUI panel presenting full hardware inquiry at a glance:
    - Manufacturing Company: `AT^CONAME?` (`ALEKA INCORPORATED`)
    - Project Code: `AT^PROJECTNAME?` (`MDM9600 UV310`)
    - Hardware Revision: `AT^HWVER?` (`UV310-U-5.1 CGWL`)
    - Baseband Chipset: `AT^CIGOID?` (`MDM9200/MDM9600`)
    - Firmware Revision: `AT^SWVER?` / `ATI` (`MDM9K-CIGO-U-7.3.9-4M`)
    - IMEI & IMSI: `AT+CGSN`, `AT+CIMI`
    - SIM Lock Register: `AT^CARDLOCK?` (`2,0,10,0` ➔ Factory Unlocked)
- **FR-6.4: Band Register Inspector**:
  - Live query and decoding of `AT$QCBANDPREF?` showing active LTE, UMTS, and GSM carrier frequencies.

---

## 5. UI/UX & Design Guidelines

### 5.1 Technology Stack & Desktop Integration
- **Framework**: Modern KDE Kirigami / Qt6 (PySide6 or native C++/QML).
- **HIG Compliance**: Strictly adheres to the **KDE Human Interface Guidelines**:
  - Predictable margins (Kirigami grid units).
  - Responsive layout dynamically adapting from compact sidebar mode to expanded desktop view.
  - Native adherence to system theme colors (Breeze Dark / Breeze Light / Catppuccin).
  - Full keyboard accessibility and navigation shortcuts.

### 5.2 Application Layout Architecture

```
+---------------------------------------------------------------------------------------+
|  [🐱] MisLTy 4G Suite         Robi 4G LTE | 📶 31/31 (-51 dBm) | 🟢 Connected     [-] [X] |
+------------------+--------------------------------------------------------------------+
| [📊] Dashboard   |  CELLULAR DATA ENGINE                                              |
|                  |  +--------------------------------------------------------------+  |
| [📻] Wi-Fi Deck  |  | Status: CONNECTED (ppp0)       Session Time: 02h 45m 12s    |  |
|                  |  | IP Address: 10.136.38.7        Default Gateway: Enabled      |  |
| [💬] SMS (2)     |  | Downlink: 14.2 MB/s            Uplink: 2.1 MB/s              |  |
|                  |  +--------------------------------------------------------------+  |
| [📞] Telephony   |  [  DISCONNECT (1-Click)  ]   [ Switch to Secondary Route ]        |
|                  |                                                                    |
| [🔧] Diagnostics |  BROADCOM WI-FI HOTSPOT                                            |
|                  |  +--------------------------------------------------------------+  |
| [📖] Lore & Info |  | Wi-Fi Radio: 🟢 BROADCASTING (Dual-Mode Active)             |  |
|                  |  | SSID: TypeScript 420           Security: WPA2-PSK            |  |
|                  |  | Passphrase: [ ********** ] (👁) Channel: 11 (2.462 GHz)      |  |
|                  |  +--------------------------------------------------------------+  |
|                  |  [ Turn Wi-Fi Off (Save 300mA) ]   [ Edit Wi-Fi Settings ]         |
+------------------+--------------------------------------------------------------------+
```

### 5.3 Color Palette & Visual Token Hierarchy
The UI adopts a warm, refined dark-mode aesthetic honoring the feline palette of Misty:

| Token | Hex Value | Semantic Usage |
| :--- | :--- | :--- |
| `BgPrimary` | `#1A1823` | Main window background (Deep Charcoal Slate) |
| `BgSurface` | `#242232` | Cards, panels, input fields (Rich Plum Grey) |
| `AccentGold` | `#E5A93C` | Misty Feline Gold (Primary buttons, active indicators, high-signal bars) |
| `AccentRose` | `#E06C75` | The Tragic Voice / Disconnect / Error alert |
| `SignalGreen`| `#98C379` | Link connected, Wi-Fi radio broadcasting, SIM ready |
| `TextPrimary`| `#E6E5EA` | Primary headlines and high-contrast telemetry text |
| `TextMuted`  | `#9D9AA8` | Secondary labels, timestamps, AT comments |

### 5.4 System Tray Integration
- Resides persistently in the system notification tray (`StatusNotifierItem` / AppIndicator).
- Dynamic tray icon displaying active 5-bar signal strength overlaid with link state badge:
  - 🟢 Connected
  - 🟡 Connecting / Searching
  - ⚪ Standby / Disconnected
  - 🔴 Error / No SIM
- Tray Context Menu:
  - 1-Click Connect / Disconnect
  - Wi-Fi Hotspot Quick Toggle (On/Off)
  - New SMS quick notification indicator
  - Open Full Window
  - Quit

---

## 6. Non-Functional Requirements (NFRs)

### 6.1 Performance & Resource Footprint
- **Memory Footprint**:
  - Resident Set Size (RSS) must not exceed **45 MB RAM** in idle system tray mode.
  - Peak memory usage during active GUI interaction must remain under **65 MB RAM**.
- **CPU Utilization**:
  - Idle CPU usage when minimized in tray must be **< 0.2%** on a standard modern x86_64 / ARM64 processor.
  - Background telemetry polling on `MI_01` (2000ms interval) must complete within **< 15ms** per cycle.
- **Application Startup Time**:
  - Cold startup to interactive window: **< 400ms**.
  - CLI execution (`mislty status`): **< 180ms**.

### 6.2 Permission Architecture & Security
- **Least-Privilege Operation**:
  - The MisLTy daemon and GUI application must run strictly under standard user privileges.
  - No continuous root or sudo prompts during normal usage.
- **Serial Port Access**:
  - Managed via udev group assignment (`uucp` or `dialout`) with `MODE="0666"`.
- **Privileged Network Operations**:
  - `pppd` invocation managed through standard setuid bit (`/usr/bin/pppd`) or a dedicated, audited Polkit action:
    `org.freedesktop.mislty.manage-connection`.
  - Routing table modifications executed via unprivileged Netlink sockets where permitted, or via Polkit-scoped helper scripts.

### 6.3 Packaging & Distribution Targets
MisLTy must be distributed in four complementary formats:
1. **Standalone MicroSD Bundle (`UFI_TOOLKIT`)**: Fully self-contained folder on the MicroSD card containing pre-compiled binaries, config files, and `install.sh`.
2. **Universal Linux AppImage**: Single-file executable bundling Python 3, Qt6/Kirigami runtimes, and dependencies for instant execution across any distribution.
3. **Python Wheel / PyPI Package**: `pip install mislty` providing the `mislty` CLI and core daemon.
4. **Arch Linux AUR / Debian `.deb` Packages**: Native distro packages integrating systemd unit files and desktop launchers.

---

## 7. Release Milestones & Acceptance Criteria

```
+---------------------------------------------------------------------------------------+
|                                  Roadmap to v1.0                                      |
|                                                                                       |
|   +-------------------+       +-------------------+       +-----------------------+   |
|   | Milestone 1 (M1)  | ----> | Milestone 2 (M2)  | ----> | Milestone 3 (M3)      |   |
|   | MicroSD Engine &  |       | Background Daemon |       | Kirigami / Qt6 GUI    |   |
|   | Core CLI Tooling  |       | & IPC Event Bus   |       | & System Tray Applet  |   |
|   +-------------------+       +-------------------+       +-----------------------+   |
|                                                                   |                   |
|                                                                   v                   |
|   +-------------------+                                   +-----------------------+   |
|   | Milestone 5 (M5)  | <-------------------------------- | Milestone 4 (M4)      |   |
|   | v1.0.0 Release    |                                   | "Tragic Voice" Audio  |   |
|   | "Keeper of Wisdom"|                                   | Pipe & Easter Egg     |   |
|   +-------------------+                                   +-----------------------+   |
+---------------------------------------------------------------------------------------+
```

### Milestone 1: MicroSD Engine & Core CLI (Week 1–2)
- [ ] Format and partition 32 GB MicroSD card into `UFI_TOOLKIT` (1GB FAT32) and `UFI_STORAGE` (31GB).
- [ ] Implement production `install.sh` and `uninstall.sh` on `UFI_TOOLKIT`.
- [ ] Harden `config/udev/99-ufi-permissions.rules` with `ID_MM_DEVICE_IGNORE` flags.
- [ ] Package standalone CLI executable `mislty` supporting `status`, `connect`, `disconnect`, `wifi`, `sms`, and `at`.

### Milestone 2: Background Daemon & IPC Bus (Week 3–4)
- [ ] Implement `misltyd` with non-blocking serial dispatch on `MI_01`.
- [ ] Build async URC parser capturing `+CMTI` and `+CMGS` notifications in real time.
- [ ] Establish Unix domain socket and D-Bus IPC service for client communication.
- [ ] Implement auto-reconnect engine with configurable backoff.

### Milestone 3: Modern Desktop GUI & Tray (Week 5–6)
- [ ] Build KDE Kirigami / Qt6 application shell with custom Purrfect palette.
- [ ] Implement Dashboard with real-time 5-bar animated signal, dBm readout, and throughput graphs.
- [ ] Implement Wi-Fi Deck with instant hotspot toggle, password editor, and NVRAM commit.
- [ ] Implement Split-Pane SMS suite with thread grouping, character counter, and desktop notifications.
- [ ] Implement embedded AT Diagnostics console with command completion.
- [ ] Implement System Tray applet with live status icon and quick-actions menu.

### Milestone 4: The Tragic Voice Pipeline & Easter Egg (Week 7)
- [ ] Implement bidirectional PCM audio streaming bridge on `MI_02` (`/dev/ttyUSB2`) connecting to PipeWire / ALSA at 8000 Hz 16-bit mono.
- [ ] Implement voice dialing signaling (`ATD<num>;`, `ATA`, `ATH`, `AT+VTS`).
- [ ] Implement `AT+CEER` analysis trap detecting CSFB rejection.
- [ ] Build the "Tragic Voice" modal dialog with Misty feline art and carrier static test button.

### Milestone 5: v1.0.0 "Keeper of Wisdom" Release (Week 8)
- [ ] Produce production AppImage bundle.
- [ ] Complete end-to-end testing across major distributions (Ubuntu 24.04, Fedora 40, Arch Linux).
- [ ] Verify zero-internet offline installation on a freshly installed air-gapped machine.
- [ ] Tag git release `v1.0.0` and update public documentation.

---

## 8. Acceptance Test Matrix (Definition of Done)

| Test ID | Category | Description | Verification Procedure | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| `TC-DATA-01` | Cellular Data | 1-Click Default Gateway | Run `mislty connect --default` or click Connect in UI. | `ppp0` interface is created, IP assigned (`10.x.x.x`), `ip route show` displays `default via ppp0`. Internet reachable. |
| `TC-DATA-02` | Cellular Data | Secondary Split Route | Run `mislty connect` without default route flag. | `ppp0` created, host Wi-Fi route remains default gateway. `curl --interface ppp0 https://icanhazip.com` returns cellular IP. |
| `TC-WIFI-01` | Wi-Fi Deck | Concurrent Dual-Mode | Connect host via USB PPP while Wi-Fi clients stream video. | Both interfaces operate simultaneously without packet loss or interface drops. |
| `TC-WIFI-02` | Wi-Fi Deck | Hotspot Power Down | Click "Turn Wi-Fi Off" or run `mislty wifi off`. | Dongle issues `AT+WIFI=0`. Wi-Fi beacon vanishes OTA, USB power draw drops by ~250mA. |
| `TC-WIFI-03` | Wi-Fi Deck | NVRAM Persist | Change SSID/Password and click Save. Power cycle dongle. | On cold reboot, `AT^SSID?` and `AT^WFPWD?` return the newly configured credentials. |
| `TC-SMS-01` | SMS Suite | Real-Time Inbound Alert | Send SMS from external mobile phone to dongle SIM. | Daemon detects `+CMTI` on `MI_01` within 500ms, raises desktop notification, and appends message to chat bubble. |
| `TC-SMS-02` | SMS Suite | 160-Char Limit & Send | Compose 150-character SMS and press Send. | Message delivered to recipient phone, UI shows delivery confirmation tick and `+CMGS` ref. |
| `TC-VOICE-01`| Telephony / Lore| Tragic Voice Easter Egg | Dial arbitrary number in phone dialer UI. | Call fails after CSFB timeout, daemon catches `+CEER: No service`, UI displays Tragic Voice modal with static test. |
| `TC-BOOT-01` | MicroSD Deploy | Zero-Internet Bootstrap | Plug dongle into air-gapped Linux PC, run `UFI_TOOLKIT/install.sh`. | Setup completes in < 5 seconds. Application launches, connects to cellular data with 0 packages downloaded. |
| `TC-NFR-01`  | Performance | Resource Budget | Run `mislty` in system tray for 1 hour. Measure RSS and CPU. | RSS < 45 MB, CPU < 0.2% average. |
