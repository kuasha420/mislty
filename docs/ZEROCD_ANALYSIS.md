# ZeroCD Analysis & Extracted Artifacts

## Reverse-Engineering the OEM Windows Installer (05c6:f000)

### 1. Extraction Methodology

The device was switched back to its initial power-on state (`05c6:f000`) by setting `DisableSwitching=1` in `/etc/usb_modeswitch.conf` and issuing `AT+CFUN=1,1`. It enumerated as an emulated SCSI CD-ROM (`/dev/sr0`, 3.1 MiB).

The raw image was dumped via `dd` to `research/zerocd.iso` and mounted via loopback. The setup payload (`Setup.exe`) was identified as an Inno Setup 5.5.0 unicode bundle and unpacked using `innoextract`.

---

### 2. Extracted Artifacts Overview

```
zerocd_extracted/
├── autorun.inf                         # Windows shell execute entry
├── autorun.ini                         # Version: Setup_01.02.1
├── autorun.ico                         # OEM Application icon
└── installer_unpacked/
    └── app/
        ├── App.exe                     # Main Win32 MFC Dashboard
        ├── 4G_Server.exe               # Background device detection daemon
        ├── ATManager.dll               # Core AT command routing engine
        ├── InitHW.dll                  # Hardware initialization & mode verification
        ├── RasDial.dll                 # Windows Remote Access Service dialer wrapper
        ├── DrvScript/general.ini       # OEM configuration: VID_05C6&PID_6000
        ├── Localize/English.txt        # Full English localization strings
        ├── Skin/                       # Original bitmap skin assets (buttons, signal bars)
        ├── Music/                      # Audio alerts (ring.wav, call-connect.wav)
        └── driver/                     # Windows XP/Vista/7/8 x86 and x64 kernel drivers
```

---

### 3. Key Reverse-Engineering Findings

#### 3.1 The Missing Web UI Mystery Solved
The Windows software contains **no references to a local Web UI or browser dashboard**. All device control—including network profile creation, USSD requests, SMS handling, and work mode switching—was executed natively inside `App.exe` through direct AT commands over the virtual serial ports.

#### 3.2 Official Qualcomm Port Mapping
Inspection of `CT_QUALCOMM_U_ser.inf` and `CT_QUALCOMM_U_mdm.inf` revealed Qualcomm's official internal designations for each USB interface:

- **Interface 0 (`MI_00`)**: `"Qualcomm USB Modem 6000"` (Primary Dial-Up / PPP data interface)
- **Interface 1 (`MI_01`)**: `"Qualcomm Command Control Port"` (Secondary AT control interface)
- **Interface 2 (`MI_02`)**: `"Qualcomm Voice Device Port"` (Voice call signaling & audio interface)
- **Interface 3 (`MI_03`)**: `"Qualcomm DM Service port"` (Qualcomm Diagnostic Monitor interface)

#### 3.3 The "WiFi Mode" vs "Dongle Mode" Switch
`English.txt` confirmed the user's recollection:
```ini
[DlgSetMode]
WiFi_Mode = WiFi Mode
Dongle_Mode = Dongle Mode

ModeSwitchTip = Current mode is WiFi, please switch to Dongle mode.
```
Binary inspection of `ATManager.dll` verified that clicking these buttons executed:
- `AT+WIFI=1` (WiFi Mode)
- `AT+WIFI=0` (Dongle Mode)
