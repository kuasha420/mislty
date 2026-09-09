# MisLTy (Qualcomm MDM9600 / Aleka UV310)

> *"The almost perfect software for hardware that outlasted its time. And the only thing keeping it from 100% is that nobody started the research five years ago. Software out of time, for hardware out of time — both legendary, yet forever one PR away from completion."*

---

## 📖 The Lore of MisLTy

Around 2014–2016, millions of generic 4G LTE USB dongles flooded the global market. When plugged into Windows, they presented an emulated CD-ROM with drivers, re-enumerated with the classic Windows USB chime, and provided internet via a proprietary dashboard toggling between "Wireless Modem" and "USB Modem".

On Linux, however, they failed completely: no network interface appeared, desktop connection managers crashed on probe, and the device defaulted to broadcasting an isolated Wi-Fi access point. For years, owners were forced to purchase separate Wi-Fi adapters just to connect to the dongle's own Wi-Fi from the host PC.

In 2026, one such forgotten device was pulled from storage for a weekend deep-dive rabbit hole. Through full reverse-engineering, its true identity and capabilities were laid bare:
- **Baseband SoC**: Genuine Qualcomm MDM9600 (`MDM9K-CIGO-U-7.3.9-4M`).
- **Wi-Fi Co-Processor**: Broadcom `BRCM_WL` 802.11b/g/n radio.
- **Board Code**: Aleka Incorporated, Project `MDM9600 UV310` (HW Rev `UV310-U-5.1 CGWL`).
- **The "Siemens SG75" Mystery**: A historical entry in `/usr/share/hwdata/usb.ids` for PID `05c6:6000` which Qualcomm reused as a reference modem ID.
- **Recovered Wi-Fi Credentials & The Feline Origin**: The forgotten WPA2 password (`misty-6969`) was recovered directly from baseband NVRAM via `AT^WFPWD?`. In 2018, the founder adopted their first cat, **Misty**—sparking a feline fascination that eventually gave birth to **Purrfect Software Limited (PSL)**, where Misty now reigns as the *Keeper of Wisdom* across the Purrfect Universe. That password was the very last credential configured on this dongle before it was consigned to a drawer of obsolete tech when its owner made the leap to Linux.
- **The Operational Reality & Single-PDN Multiplexing**: Extensive live silicon testing disproved the historical 500mA electrical power-down myth—both radios remain fully powered and transmit RF frames simultaneously. The true hardware ceiling is **Qualcomm AMSS Single-PDN packet multiplexing**: during active USB PPP sessions, AMSS dedicates cellular data routing exclusively to the USB host. Meanwhile, the Broadcom Wi-Fi radio stays alive indefinitely, hosting a local WLAN (`192.168.100.0/24`) and embedded web server (`QC-Webs`). This enables 4 major unlocked features: out-of-band "Shadow Telemetry", local client discovery, host reverse-tethering relay, and sub-4-second smart mode switching.
- **The Name `MisLTy`**: 
  - `Misty`: The beloved feline Keeper of Wisdom whose name cracked open the radio NVRAM.
  - `LTE`: The high-speed 4G data backbone running at full signal (-51 dBm).
  - `Missed`: The missed call, the missed fallback, the missed connection (`+CEER: No service`). The tragic voice subsystem reverse-engineered down to its 8000 Hz 16-bit PCM audio pipelines and telephony AT state machines, only to be rejected in 2026 by modern carrier MMEs because 3G was switched off and 4G data sticks lack VoLTE provisioning. So close, yet so far `</3`.

---

## 📂 Repository Structure

```
ufi-modem/
├── README.md                           # Project overview, lore, and quickstart
├── docs/
│   ├── PRD.md                          # Product Requirement Document (v1.0 Desktop & Toolkit)
│   ├── TECHNICAL_DESIGN.md             # System architecture, D-Bus RPC, process topology & roadmap
│   ├── OPERATIONAL_MODES.md            # Empirical benchmarks & Single-PDN dual-plane networking
│   ├── QC_WEBS_API_SPEC.md             # Reverse-engineered GoForm & JSON telemetry API specs
│   ├── HARDWARE_SPEC.md                # Complete board architecture, pinout & RF specs
│   ├── SOFTWARE_SPEC.md                # USB enumeration, PPP data plane & Wi-Fi control
│   ├── AT_COMMAND_REFERENCE.md         # Comprehensive dictionary of ~150 AT commands
│   ├── LINUX_COMPATIBILITY_GUIDE.md    # Analysis of the 2015 failure & ModemManager crash
│   ├── VOICE_CALL_ANALYSIS.md          # Audio PCM architecture & LTE carrier CSFB analysis
│   ├── SD_CARD_SPEC.md                 # 32GB SDHC storage & offline self-install deployment
│   └── ZEROCD_ANALYSIS.md              # Reverse-engineered Windows ISO & installer assets
├── config/
│   ├── udev/
│   │   └── 99-ufi-permissions.rules    # User-space permission rules for /dev/ttyUSB*
│   └── ppp/
│       ├── chat-ufi                    # Cellular chatscript for ATD*99#
│       └── peers-ufi                   # Cellular-optimized pppd configuration
├── bin/
│   └── ufi-modem                       # Standalone Python CLI management utility
└── research/
    ├── raw_descriptors.txt             # Complete lsusb -v dump
    ├── at_clac_dump.txt                # Raw AT+CLAC command output
    ├── dmesg_switch_trace.txt          # Kernel boot & ZeroCD mode switch trace
    └── usb_modeswitch_05c6_f000.txt    # Upstream usb_modeswitch database entry
```

---

## 🚀 Quickstart & Usage

### 1. Requirements
- Linux Kernel 4.x / 5.x / 6.x / 7.x with `option.ko` module.
- `ppp` package (`pppd` and `chat`).
- Python 3.8+.

### 2. Device Permissions
Install the udev rule to allow non-root access to the modem ports:
```bash
sudo cp config/udev/99-ufi-permissions.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### 3. CLI Commands

The `ufi-modem` CLI provides full control over the modem without requiring heavy desktop daemons:

```bash
# Display live status (Hardware, SIM, Operator, CSQ dBm, Wi-Fi, PPP)
ufi-modem status

# Inspect SIM card identity (IMSI, PIN, Operator)
ufi-modem sim

# List SMS messages stored on the SIM card
ufi-modem sms list

# Send an SMS directly from the terminal
ufi-modem sms send +8801XXXXXXXXX "Hello from Linux!"

# Toggle Wi-Fi Router Mode on/off
ufi-modem wifi off    # Powers down Wi-Fi radio (Pure USB Mode)
ufi-modem wifi on     # Powers up Wi-Fi AP ("TypeScript 420")

# Update cellular APN
ufi-modem apn internet

# Connect via USB (establishes ppp0)
sudo ufi-modem connect          # Secondary interface (preserves local Wi-Fi)
sudo ufi-modem connect --default # Primary default gateway

# Disconnect USB session
sudo ufi-modem disconnect

# Send raw AT commands directly
ufi-modem at "AT+CSQ"
ufi-modem at "AT^SSID?"
```

---

## 🗺️ Project Roadmap

- [x] **Phase 1: Reverse-Engineering & Architecture Specifications**
  - Trace USB descriptors and ZeroCD switching.
  - Map serial ports, PCM audio endpoints, and QCDM diagnostics.
  - Document complete AT command set (~150 commands).
  - Empirically benchmark USB PPP vs. Pocket Router Wi-Fi performance.
  - Reverse-engineer `QC-Webs` embedded GoForm web server & real-time JSON telemetry stream.
  - Author comprehensive PRD (`PRD.md`) and Technical Design Document (`TECHNICAL_DESIGN.md`).
- [x] **Phase 2: Core Tooling & Permissions**
  - Standalone `ufi-modem` Python CLI with clean Web API integration.
  - Hardened udev rules (`99-ufi-permissions.rules`) with `ID_MM_DEVICE_IGNORE` and symlinks.
  - Cellular-optimized PPP dialer with non-destructive split routing.
  - SMS listing, reading, and sending OTA.
- [ ] **Phase 3: Modern Desktop GUI (KDE Plasma / Kirigami / Qt6)**
  - Native KDE Plasma / Qt6 application.
  - Real-time animated signal bars and carrier display.
  - One-click Connect/Disconnect and Wi-Fi toggles.
  - Integrated SMS conversation manager.
  - Bandwidth consumption and session analytics.
- [ ] **Phase 4: Advanced Linux Automation**
  - Automated Multi-WAN failover daemon.
  - Telegram / Discord 2FA SMS forwarder.
  - Automount MicroSD card as local Wi-Fi NAS.
