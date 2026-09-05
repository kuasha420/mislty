# Complete AT Command Reference

## Qualcomm MDM9600 / Aleka UV310 (05c6:6000)

This reference documents the complete command set supported by the Aleka UV310 firmware (`MDM9K-CIGO-U-7.3.9-4M`), reverse-engineered via `AT+CLAC` inspection and live hardware probing.

---

### 1. Device Identification & Diagnostics

| Command | Type | Description | Example Response |
| :--- | :--- | :--- | :--- |
| `ATI` | Exec | Display manufacturer, model, firmware revision, and IMEI | `Manufacturer: QUALCOMM INCORPORATED`<br>`Model: 0`<br>`Revision: MDM9K-CIGO-U-7.3.9-4M`<br>`IMEI: 86117903XXXXXXX` |
| `AT+CGMI` | Exec | Request manufacturer identification | `QUALCOMM INCORPORATED` |
| `AT+CGMM` | Exec | Request model identification | `0` |
| `AT+CGMR` | Exec | Request firmware revision | `MDM9K-CIGO-U-7.3.9-4M  1  [Jan 19 2012 21:00:00]` |
| `AT+CGSN` | Exec | Request product serial number (IMEI) | `86117903XXXXXXX` |
| `AT+CIMI` | Exec | Request International Mobile Subscriber Identity (IMSI) | `47004XXXXXXXXXX` |
| `AT+CLAC` | Exec | List all supported AT commands | *(Full list of ~150 commands)* |

---

### 2. Hardware Platform & Aleka / CIGO Vendor Commands

| Command | Type | Description | Example Response |
| :--- | :--- | :--- | :--- |
| `AT^CONAME?` | Query | Display manufacturing company name | `^CONAME:ALEKA INCORPORATED` |
| `AT^PROJECTNAME?` | Query | Display internal project code name | `^PROJECTNAME:MDM9600 UV310` |
| `AT^HWVER?` | Query | Display hardware board revision | `^HWVER:UV310-U-5.1 CGWL` |
| `AT^SWVER?` | Query | Display exact software build date & time | `^SWVER: MDM9K-CIGO-U-7.3.9-4M,May  9 2018,18:25:41` |
| `AT^CIGOID?` | Query | Baseband family generation ID | `^CIGOID:MDM9200` |
| `AT^UFIV?` | Query | UFI dongle software version | `^UFIV:2` |
| `AT^APN?` | Query | Default APN stored in flash | `^APN:internet` |
| `AT^APN=<name>` | Set | Set default APN | `OK` |
| `AT^HWCFG?` | Query | Hardware configuration status | `^HWCFG:NOT CONFIG` |
| `AT^CARDLOCK?` | Query | SIM network lock status | `^CARDLOCK:2,0,10,0` (2 = Unlocked) |

---

### 3. SIM & Cellular Network Management

| Command | Type | Description | Example Response / Values |
| :--- | :--- | :--- | :--- |
| `AT+CPIN?` | Query | SIM PIN authentication status | `+CPIN: READY` |
| `AT+CSQ` | Query | Received Signal Strength Indication (RSSI) | `+CSQ: 31,99`<br>RSSI = `0` (-113 dBm) to `31` (-51 dBm). `99` = unknown/undetectable. |
| `AT+COPS?` | Query | Current network operator & access tech | `+COPS: 0,0,"Teletalk",7`<br>Tech: `0`=GSM, `2`=UMTS, `7`=LTE |
| `AT+COPS=?` | Exec | Perform active RF scan for all towers | `+COPS: (1,"BGD AKTEL",...),(3,"GrameenPhone",...),...` |
| `AT+COPS=0` | Set | Set network selection to Automatic | `OK` |
| `AT+CREG?` | Query | Circuit-switched (GSM/2G) registration | `+CREG: 0,1` (`1`=Registered Home, `5`=Roaming) |
| `AT+CGREG?` | Query | Packet-switched (GPRS/3G) registration | `+CGREG: 0,1` |
| `AT+CEREG?` | Query | EPS (4G LTE) registration status | `+CEREG: 0,1` (`1`=Registered LTE Home) |
| `AT+CFUN?` | Query | Phone functionality level | `+CFUN: 1` (`1`=Full, `0`=Minimum, `4`=Airplane mode) |

---

### 4. Data Call & PPP Dial-Up Commands

| Command | Type | Description | Syntax / Behavior |
| :--- | :--- | :--- | :--- |
| `AT+CGDCONT?` | Query | Display defined PDP contexts | `+CGDCONT: 1,"IP","internet","0.0.0.0",0,0` |
| `AT+CGDCONT=1,"IP","<apn>"` | Set | Configure PDP Context 1 with APN | `OK` |
| `ATD*99#` | Exec | Dial primary packet data call | Returns `CONNECT 100000000` and enters raw PPP HDLC packet mode. |
| `ATH` | Exec | Terminate packet call / hang up | `OK` (drops carrier and resets baseband state machine). |

---

### 5. SMS Text Messaging Commands

| Command | Type | Description | Usage / Example |
| :--- | :--- | :--- | :--- |
| `AT+CMGF=1` | Set | Set SMS mode to ASCII Text Mode | `OK` (`1`=Text mode, `0`=PDU mode) |
| `AT+CPMS="SM","SM","SM"` | Set | Select SIM card as SMS storage | `+CPMS: 0,100,0,100,0,100` |
| `AT+CMGL="ALL"` | Exec | List all SMS messages on SIM | `+CMGL: 1,"REC READ","+8801...","","26/09/05,..."` |
| `AT+CMGR=<index>` | Exec | Read a specific SMS by index | Returns SMS header and body text. |
| `AT+CMGS="<number>"` | Exec | Send SMS | 1. Modem responds with `>` prompt.<br>2. Send text body terminated with `0x1A` (Ctrl+Z).<br>3. Returns `+CMGS: <mr> OK`. |
| `AT+CMGD=<index>` | Exec | Delete a specific SMS | `OK` |

| `AT+CGSMS?` | Query | SMS routing domain | `+CGSMS: 2`<br>`0`=Packet Switched (LTE), `1`=Circuit Switched (2G/3G), `2`=PS preferred, `3`=CS preferred. |
| `AT+CGSMS=<val>` | Set | Set SMS routing domain (use `2` for 4G LTE SMS) | `OK` |
| `AT+CSCA?` | Query | SMS Service Center Address (SMSC) | `+CSCA: "+88015015XXXX",145` |
| `AT+CEER` | Exec | Extended Error Report (Diagnose disconnect/reject cause) | `+CEER: No service available` or `+CEER: Client ended call` |

---

### 6. Cellular Voice Call Commands

| Command | Type | Description | Usage / Protocol |
| :--- | :--- | :--- | :--- |
| `ATD<number>;` | Exec | Initiate cellular voice call | **Trailing semicolon is mandatory** for voice call. Audio streams over `/dev/ttyUSB2`. |
| `RING` | Unsolicited | Incoming call alert | Accompanied by `+CLIP: "<number>",...` |
| `ATA` | Exec | Answer incoming voice call | Connects call and opens PCM audio stream on `MI_02`. |
| `AT+CHUP` / `ATH` | Exec | Hang up voice call | Terminates active or alerting voice call. |
| `AT+VTS=<digit>` | Exec | Generate DTMF tone during call | `AT+VTS=1` sends DTMF tone for digit 1. |

---

### 7. Broadcom Wi-Fi Subsystem (`AT+WIFI` & `AT^WI...`)

The onboard Broadcom Wi-Fi chip exposes a complete dedicated command group:

| Command | Type | Description | Example / Notes |
| :--- | :--- | :--- | :--- |
| `AT+WIFI?` | Query | Current Wi-Fi radio power state | `+WIFI:1` (`1`=ON, `0`=OFF) |
| `AT+WIFI=1` | Set | Turn ON Wi-Fi radio & broadcast AP | `OK` |
| `AT+WIFI=0` | Set | Turn OFF Wi-Fi radio (Pure USB mode) | `OK` |
| `AT^SSID?` | Query | Current Wi-Fi SSID | `^SSID: wl_ssid="TypeScript 420"62C` |
| `AT^SSID="<name>"` | Set | Configure Wi-Fi SSID | `OK` |
| `AT^WRSSID?` | Query | Read NVRAM-stored SSID | `^WRSSID: wl_ssid=...` |
| `AT^WFPWD?` | Query | Current WPA2 Pre-Shared Key (Password) | `^WFPWD: wl_wpa_psk_key=1234567890` |
| `AT^WFPWD="<key>"` | Set | Set WPA2 Pre-Shared Key | `OK` |
| `AT^WIMODE?` | Query | Wi-Fi operational mode | `^WIMODE:4` (`4`=AP mode, `0`=Client) |
| `AT^WIBAND?` | Query | Wi-Fi frequency band | `^WIBAND:0` (`0`=2.4 GHz) |
| `AT^WIFREQ?` | Query | Wi-Fi center frequency | `^WIFREQ:2412` (2412 MHz = Channel 1) |
| `AT^WIHELP` | Exec | Display all supported Broadcom commands | Returns list of all `BRCM_WL_AT_Func_*` handlers. |

---

### 8. Qualcomm Gobi Proprietary Commands (`$QC...`)

| Command | Type | Description | Example / Notes |
| :--- | :--- | :--- | :--- |
| `AT$QCSYSMODE` | Query | Returns current active system mode (GSM, WCDMA, LTE). | `OK` / Unsolicited status |
| `AT$QCBANDPREF?` | Query | List current enabled frequency bands | Returns band list (e.g. `BC0`, `GSM_DCS_1800`, `GSM_EGSM_900`, `WCDMA_I`, `46.Any`). |
| `AT$QCBANDPREF=<p>,<bands>` | Set | Set band preference (`<p>=0` volatile, `1` NVRAM). E.g. `AT$QCBANDPREF=1,"46"` enables all bands. | `OK` |
| `AT+NETMODE?` | Query | Query RAT configuration vector | `+NETMODE: 0,3,0,0,0,1,4,0,0,0,17` (11 integers parsed by `ATManager.dll`). |
| `AT+PHPREF?` | Query | Physical RAT mode preference | `+PHPREF: 4` |
| `AT^CIGOM?` | Query | CIGO baseband operating mode | `^ALKM:5` (`5` = Multi-mode) |
| `AT$QCSIMSTAT` | Query | SIM interface electrical and hardware status | Returns SIM presence. |
| `AT$QCPINSTAT` | Query | Extended PIN/PUK verification state | PIN readiness status. |
| `AT$QCPWRDN` | Exec | Graceful baseband power-down sequence | `OK` |
| `AT$QCDMR` | Exec | Qualcomm Diagnostic Monitor interface control | Diagnostic serial port routing. |
| `AT$QCPDPP` | Set | Qualcomm PDP profile authentication | Configure PAP/CHAP credentials. |
| `AT+CEMODE` | Query/Set | EPS (LTE) Circuit/Packet Switched Mode of Operation | `+CEMODE: 0` |
| `AT+CFUN=1,1` | Exec | Soft reboot baseband processor & reload NVRAM | Restarts RF & baseband RTOS without USB power cycle. |


