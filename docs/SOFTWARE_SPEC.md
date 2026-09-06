# Reverse-Engineered Software & Protocol Specification

## Qualcomm MDM9600 / Aleka UV310 (05c6:6000)

### 1. USB Enumeration & ZeroCD State Machine

When plugged into a USB host, the dongle traverses a two-phase enumeration sequence:

```
                      +-----------------------------+
                      |         Power On            |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      | Initial State: 05c6:f000    |
                      | - Emulated SCSI CD-ROM      |
                      | - Windows Installer LUN     |
                      +--------------+--------------+
                                     |
                                     | Host sends SCSI Switch command:
                                     | 5553424308306384c00000008000067103000000...
                                     | (or Linux usb_modeswitch)
                                     v
                      +-----------------------------+
                      | USB Disconnect / Reconnect  |
                      | (Hardware reset of USB PHY) |
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      | Modem State: 05c6:6000      |
                      | - If 0: Primary AT / PPP    |
                      | - If 1: Secondary AT Control|
                      | - If 2: Aux / NMEA stream   |
                      | - If 3: Qualcomm QCDM Diag  |
                      | - If 4: MicroSD Mass Storage|
                      +-----------------------------+
```

#### 1.1 The SCSI Switching Packet
The standard `usb_modeswitch` configuration (`/usr/share/usb_modeswitch/05c6:f000`) sends:
```text
TargetVendor=0x05c6
TargetProductList="0016,6000,9000"
StandardEject=1
MessageContent="5553424308306384c000000080000671030000000000000000000000000000"
```

---

### 2. Interface Functional Breakdown

Upon re-enumeration as `05c6:6000`:

| Interface # | Linux Driver | Typical Linux Node | Subsystem & Protocol Role |
| :--- | :--- | :--- | :--- |
| **Interface 0 (`MI_00`)** | `option` | `/dev/ttyUSB0` (or `1`) | **Primary Modem Port**: High-speed AT commands, PPP dial-up data plane (`ATD*99#`), network registration commands. |
| **Interface 1 (`MI_01`)** | `option` | `/dev/ttyUSB1` (or `2`) | **Secondary Control & Unsolicited Event Port**: Independent AT interface and asynchronous carrier notification channel. The baseband delivers `+CMTI` (new SMS arrival), `+CMGS` (OTA SMS delivery receipts), `RING`, and `+CLIP` here. |
| **Interface 2 (`MI_02`)** | `option` | `/dev/ttyUSB2` (or `3`) | **Qualcomm Voice Device Port**: Bidirectional raw linear 16-bit mono 8000 Hz PCM audio streaming endpoint (`pcmWave.dll` audio pipeline at 115200 baud). |
| **Interface 3 (`MI_03`)** | `option` | `/dev/ttyUSB3` (or `4`) | **Qualcomm QCDM Diagnostic Port**: Binary diagnostic monitor interface (115200 baud). Supports Qualcomm DM protocol packets for NVRAM reads/writes, radio calibration, and low-level RF debugging. |
| **Interface 4 (`MI_04`)** | `usb-storage` | `/dev/sda` | **SCSI Mass Storage**: Direct access to the onboard 32 GB MicroSD card slot. Mountable as standard FAT32/ext4 block storage. |


---

### 3. Cellular Data Connection Protocol (PPP over USB)

Unlike newer RNDIS/CDC-ECM LTE dongles that implement virtual Ethernet MAC encapsulation inside the firmware, this Qualcomm MDM9600 firmware operates in **Point-to-Point Protocol (PPP) Mode** over serial:

#### 3.1 Establishing a Connection
1. **Define PDP Context**:
   ```text
   AT+CGDCONT=1,"IP","<APN>"
   ```
2. **Initiate Call**:
   ```text
   ATD*99#
   ```
3. **Connect Handshake**:
   ```text
   CONNECT 100000000
   ```
   The modem switches the serial port from Hayes command mode to raw HDLC/PPP frame mode at 100 Mbps PHY link rate.

4. **LCP Negotiation**:
   - Host sends `LCP ConfReq` (magic number, ACFC, PFC).
   - Baseband responds with `LCP ConfAck`.
   - Compression Control Protocol (CCP) and Van Jacobson (VJ) compression are rejected by the 3GPP baseband (`noccp`, `novj` recommended).

5. **IPCP Phase**:
   - Host requests `0.0.0.0` IP and `0.0.0.0` DNS.
   - Baseband sends `IPCP ConfNak` with assigned cellular IP and upstream carrier DNS (e.g. `10.136.38.7`, DNS `8.8.8.8`, `202.4.173.202`).
   - Host sends `IPCP ConfAck`, bringing `ppp0` into the `UP` operational state.

#### 3.2 Terminating a Connection
1. Host drops PPP daemon (`killall pppd` or LCP TermReq).
2. Host asserts DTR low or sends `ATH` over the AT channel to reset baseband packet state.

---

### 4. Wi-Fi Router Co-Processor Protocol & Operational Modes

The Broadcom Wi-Fi radio is managed entirely through Qualcomm baseband AT commands prefixed with `AT^WI...` or `AT+WIFI`:

#### 4.1 Radio Power States & Hardware Status Registers
- **`AT+WIFI=1`**: Configures the Wi-Fi subsystem to enabled in baseband NVRAM. Launches the internal DHCP server (`192.168.100.1` subnet) and enables the Broadcom co-processor.
- **`AT+WIFI=0`**: Powers down the Broadcom Wi-Fi radio and stops all Wi-Fi RF emissions. Saves approximately 200–300 mA of USB power draw.
- **`AT^WIENABLE?`**: Queries the physical Broadcom RF transmitter hardware status:
  - `^WIENABLE: 1`: Wi-Fi transmitter is actively broadcasting beacon frames and handling client associations (Pocket Router Mode).
  - `^WIENABLE: 0`: Wi-Fi transmitter is muted / suspended (USB Tethered Modem Mode).

#### 4.2 Hardware Mutual Exclusion (Pocket Router vs. USB Tethered Modem)
As verified empirically on live hardware and confirmed by OEM Windows binaries (`[DlgSetMode]`), the device enforces strict mutual exclusion between Wi-Fi AP transmission and USB PPP data:
1. When `ATD*99#` connects on `/dev/ttyUSB0` and IPCP establishes `ppp0`, the Qualcomm baseband immediately clamps `AT^WIENABLE?` to `0`. The Wi-Fi SSID disappears over the air.
2. Even if `AT+WIFI?` reports `+WIFI:1`, the radio is in hardware suspension to honor the USB 2.0 500mA power ceiling and single-PDN routing architecture.
3. When `ppp0` is torn down, the baseband automatically restores `AT^WIENABLE=1`, and the Wi-Fi AP resumes broadcasting within 3–5 seconds without a reboot.
4. Full architectural details and state machines are documented in [OPERATIONAL_MODES.md](file:///home/psl/Projects/ufi-modem/docs/OPERATIONAL_MODES.md).

#### 4.3 Wi-Fi Credential Management
- **Query SSID**: `AT^SSID?` -> returns `^SSID: wl_ssid=<SSID>`
- **Set SSID**: `AT^SSID="<SSID>"` (Note: Broadcom firmware automatically appends the last 3 hex characters of the MAC address, e.g. `62C`).
- **Query WPA2 Key**: `AT^WFPWD?` -> returns `^WFPWD: wl_wpa_psk_key=<PASSWORD>`
- **Set WPA2 Key**: `AT^WFPWD="<PASSWORD>"`
- **Save to NVRAM**: `AT+WRWIFI`

#### 4.4 Broadcom Diagnostic Registers
- **Operational Mode**: `AT^WIMODE?` -> returns `^WIMODE: 4` (Access Point Mode)
- **Band**: `AT^WIBAND?` -> returns `^WIBAND: 0` (2.4 GHz)
- **Frequency**: `AT^WIFREQ?` -> returns `^WIFREQ: 2462` (Channel 11 / 2462 MHz)
- **Command Help**: `AT^WIHELP` -> lists all Broadcom handler functions.
