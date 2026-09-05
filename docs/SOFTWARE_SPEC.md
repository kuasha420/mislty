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

### 4. Wi-Fi Router Co-Processor Protocol

The Broadcom Wi-Fi radio is managed entirely through Qualcomm baseband AT commands prefixed with `AT^WI...` or `AT+WIFI`:

#### 4.1 Radio Power States
- **`AT+WIFI=1`**: Boots the Broadcom co-processor, enables the 2.4 GHz radio, launches the internal DHCP server (`192.168.100.1` subnet), and begins broadcasting the configured SSID.
- **`AT+WIFI=0`**: Powers down the Broadcom Wi-Fi radio and stops all Wi-Fi RF emissions. Saves approximately 200–300 mA of USB power draw.

#### 4.2 Wi-Fi Credential Management
- **Query SSID**: `AT^SSID?` -> returns `^SSID: wl_ssid=<SSID>`
- **Set SSID**: `AT^SSID="<SSID>"`
- **Query WPA2 Key**: `AT^WFPWD?` -> returns `^WFPWD: wl_wpa_psk_key=<PASSWORD>`
- **Set WPA2 Key**: `AT^WFPWD="<PASSWORD>"`
- **Save to NVRAM**: `AT+WRWIFI`
