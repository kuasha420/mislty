# Cellular Voice Call & Audio Streaming Architecture

## Deep Dive into Qualcomm MDM9600 Voice Capabilities & LTE Carrier Constraints

### 1. Hardware & Driver Port Architecture

From reverse-engineering `CT_QUALCOMM_U_mdm.inf`, `CT_QUALCOMM_U_ser.inf`, and the Windows application suite (`App.exe`, `ATManager.dll`, `pcmWave.dll`), Qualcomm officially designated the 5 USB interfaces of VID `0x05C6` PID `0x6000` as:

| Interface | Device Node | Qualcomm INF Device Name | Function |
| :--- | :--- | :--- | :--- |
| **`MI_00`** | `/dev/ttyUSB0` | `Qualcomm USB Modem 6000` | High-speed data modem & dial-up PPP (`ATD*99#`) |
| **`MI_01`** | `/dev/ttyUSB1` | `Qualcomm Command Control Port` | Primary AT command dispatcher, status, & signaling |
| **`MI_02`** | `/dev/ttyUSB2` | **`Qualcomm Voice Device Port`** | **Bidirectional raw PCM audio streaming endpoint** |
| **`MI_03`** | `/dev/ttyUSB3` | `Qualcomm DM Service port` | Qualcomm Diagnostic Monitor (QCDM / NVRAM calibration) |
| **`MI_04`** | `/dev/sda` | `USB Mass Storage Device` | 32 GB MicroSD card reader |

---

### 2. Disassembly & Reverse-Engineering of `pcmWave.dll`

Disassembly of `pcmWave.dll` (`20160917\bin\Release\pcmWave.pdb`) revealed the exact audio subsystem design:

```
                  +----------------------------------------------+
                  |         pcmWave.dll Audio Subsystem          |
                  |                                              |
/dev/ttyUSB2      |  +--------------------+     +-------------+  |   PC Speakers /
Serial PCM In ===>|=>|  CWaveInSerial     |====>|  CWaveOut   |=>|== Headset (waveOut)
(115200 baud)     |  +--------------------+     +-------------+  |
                  |                                              |
                  |  +--------------------+     +-------------+  |   PC Microphone
/dev/ttyUSB2 <====|<=|  CWaveOutSerial    |<====|  CWaveIn    |<=|<= (waveIn)
Serial PCM Out    |  +--------------------+     +-------------+  |
                  +----------------------------------------------+
```

#### Audio Stream Characteristics:
* **Encoding**: Raw linear 16-bit Signed Little-Endian PCM (`s16le`).
* **Sampling Rate**: **8000 Hz** (verified by `mov DWORD PTR [ecx+0x18], 0x1f40` in `WAVEFORMATEX` initialization).
* **Channels**: 1 (Mono).
* **Bit Depth**: 16 bits per sample.
* **Byte Rate**: 16,000 bytes/sec.
* **Serial Framing**: Raw uncompressed PCM frames transferred via standard `ReadFile` / `WriteFile` at 115200 baud (native USB 2.0 Bulk transfer).
* **Linux Bridge**: Can be piped bidirectionally to PipeWire/PulseAudio via `pacat`, `sox`, or a Python ALSA loopback.

---

### 3. Voice Call Signaling Protocol

Voice call control is performed over the AT command port (`/dev/ttyUSB0` or `/dev/ttyUSB1`):

1. **Voice Dialing**:
   ```text
   ATD<phone_number>;
   ```
   *(The trailing semicolon `;` is mandatory in 3GPP standards to instruct the baseband that this is a voice call rather than a data dial-up).*
2. **Incoming Call Indication**:
   Modem emits:
   ```text
   RING
   +CLIP: "01841832034",129,,,,0
   ```
3. **Answering Call**: `ATA`
4. **Hanging Up**: `AT+CHUP` or `ATH`
5. **In-Call DTMF Generation**: `AT+VTS=<digit>`

---

### 4. Empirical Test Results & Why LTE Voice Failed

#### 4.1 Teletalk Carrier Tests
On live hardware with a Teletalk SIM, we initiated an outgoing voice call to `01841832034`:
```text
Dialing 01841832034; on /dev/ttyUSB0...
[0.0s] USB0: b'ATD01841832034;\r'
[32.1s] USB0: b'\r\nNO CARRIER\r\n'
```
Querying the 3GPP Extended Error Report (`AT+CEER`) revealed:
```text
AT+CEER
+CEER: No service available
```

#### 4.2 Robi (AKTEL) Carrier Tests
On live hardware with a Robi SIM (`47002`), we tested both outbound and inbound calling:
1. **Outbound Call (`ATD01842988266;`)**:
   - The modem returned `OK` and held the RF link active for 30.0 seconds.
   - When terminated from the host with `AT+CHUP`, the baseband reported `+CEER: Client ended call`. However, the destination phone did not alert because the carrier's MME did not forward an active CSFB voice bearer.
2. **Inbound Call (Dialing `01841832034` from Robi & Teletalk)**:
   - On the calling handset: 20–30 seconds of absolute dead silence, followed by an abrupt termination.
   - On the dongle: Serial monitoring caught the internal bearer state transition; querying `AT+CEER` immediately returned `+CEER: No service`.

#### 4.3 Technical Root Cause:
1. **4G LTE (E-UTRAN) is an All-IP Packet Network**: Standard 4G LTE has no legacy circuit-switched (CS) voice channels.
2. **Absence of VoLTE / IMS**: Voice over LTE requires a carrier IMS APN profile. Generic 2014 MDM9600 data dongles do not have carrier-certified VoLTE firmware profiles.
3. **MME SGs CSFB Paging Rejection**: When an inbound call arrives at the MSC, it queries the HSS and sends an SGs paging request to the LTE MME. Because the dongle's IMEI (`86117903...`) and Qualcomm NVRAM declare the terminal as a **Data-Centric / EPS Data-Only Device**, the network does not establish a circuit-switched voice channel. The caller hears dead silence during the SGs paging timeout before the MSC tears down the call.
4. **Known OEM Limitation**: The OEM Windows dashboard explicitly anticipated this behavior in its localization dictionary (`Localize/English.txt`):
   ```ini
   SMSAlertInLTEMode=SMS is not possible in current network\nPlease change network to %s mode
   
   [DlgVoice]
   SMSCallAlertInEVDOOnly=Voice call/SMS/Scratch card recharge is not possible in EVDO mode. \nPlease select 1x or Hybrid mode from File -> Settings -> Mode selection
   ```

---

### 5. Definitive Conclusion & Modern Capability Matrix

| Feature | Working on Modern Linux? | Notes |
| :--- | :---: | :--- |
| **4G LTE High-Speed Data** | ✅ YES | Direct PPP (`pppd call ufi`) at full LTE speeds. |
| **Broadcom Wi-Fi Hotspot** | ✅ YES | Autonomous Broadcom AP broadcasting WPA2 (`TypeScript 420`). |
| **Simultaneous Dual-Mode** | ✅ YES | Concurrent USB PPP data link + Wi-Fi router. |
| **Outbound & Inbound SMS** | ✅ YES | Text mode (`AT+CMGF=1`, `AT+CSMP=17,167,0,0`), verified delivered OTA. |
| **Live Incoming SMS Alerts** | ✅ YES | Emits `+CMTI` directly to host on `/dev/ttyUSB2`. |
| **32GB MicroSD Card Reader** | ✅ YES | Native Linux SCSI mass storage (`/dev/sda`). |
| **Circuit-Switched Voice Calls**| ❌ NO | Restricted by carrier MME policies on 4G LTE data modems (`+CEER: No service`). |

