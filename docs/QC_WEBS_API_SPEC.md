# QC-Webs Embedded Web API & Server Specification

## Overview

The Aleka UV310 / Qualcomm MDM9600 4G LTE device embeds **QC-Webs**, a specialized embedded GoForm HTTP server (derived from GoAhead WebServer 2.5) running on `http://192.168.100.1:80`.

This document specifies the complete reverse-engineered API, data formats, endpoints, and hidden telemetry interfaces extracted directly from the device firmware.

---

## 1. Authentication & Session Management

All management actions (except initial status polling) require an authenticated session.

### 1.1 Login (`LOGIN_NEW`)
* **Endpoint**: `POST /goform/goform_process`
* **Form Parameters**:
  * `goformId`: `LOGIN_NEW`
  * `user`: Username (default: `admin`)
  * `psw`: Password (default: `admin`)
  * `lucknum`: Client-generated random session token (timestamp + random integer)
  * `systemDate`: Client timestamp in milliseconds
  * `save_login`: Optional (`1` or empty)
* **Headers/Cookies**: Sets `Cookie: lucknum=<token>`
* **Success Response**: `<html>...timer = setTimeout('location.replace("/index.asp")', 100)...</html>`
* **Failure Response**: Redirects back to `login.asp`

### 1.2 Logout (`LOGOUT`)
* **Endpoint**: `GET /goform/goform_process?goformId=LOGOUT`
* **Result**: Invalidates session cookie and redirects to `login.asp`.

### 1.3 Language Selection (`SET_LANGUAGE`)
* **Endpoint**: `GET /goform/goform_process?goformId=SET_LANGUAGE&language=<lang>`
* **Supported Languages**: `en` (English), `cn` (Simplified Chinese), `tw` (Traditional Chinese).

---

## 2. High-Value Telemetry & Monitoring APIs

### 2.1 Real-Time JSON Telemetry (`json/refresh_data.asp`)
Provides live cellular, throughput, and connection telemetry in clean JSON format without screen scraping:
* **Endpoint**: `GET http://192.168.100.1/json/refresh_data.asp`
* **Sample Payload**:
  ```json
  {
    "network_type": "LTE",
    "realtime_statistics": "0,0,196,168,476,61732223,898445230,57521",
    "ppp_status": "ppp_connected",
    "cardstate": "modem_init_complete",
    "roam": "roam_off"
  }
  ```
* **`realtime_statistics` Array Unpacking**:
  | Index | Field Name | Unit | Description |
  | :--- | :--- | :--- | :--- |
  | `0` | `speed_up` | Bytes/s | Real-time upstream throughput rate |
  | `1` | `speed_down` | Bytes/s | Real-time downstream throughput rate |
  | `2` | `current_tx_bytes` | Bytes | Bytes transmitted during active session |
  | `3` | `current_rx_bytes` | Bytes | Bytes received during active session |
  | `4` | `session_duration` | Seconds | Elapsed duration of current data session |
  | `5` | `total_tx_bytes` | Bytes | Cumulative lifetime bytes transmitted |
  | `6` | `total_rx_bytes` | Bytes | Cumulative lifetime bytes received |
  | `7` | `total_uptime` | Seconds | Cumulative lifetime connected time |

### 2.2 Active Wi-Fi Station Discovery (`station_list.asp`)
* **Endpoint**: `GET http://192.168.100.1/station_list.asp`
* **Data Format**: HTML table containing currently associated client devices:
  ```html
  <tr><td class="head">1</td><td class="tail">D2:6F:5B:13:A8:B5</td></tr>
  ```
* **Integration**: MisLTy scrapes this endpoint to populate the real-time client station table on the desktop dashboard.

---

## 3. Configuration & Control APIs (`goform/goform_process`)

All configuration commands are dispatched via HTTP POST to `/goform/goform_process`.

### 3.1 Wi-Fi Basic Settings (`WIFI_BASIC`)
Allows configuring the Wi-Fi AP **without appending the 3-character BSSID suffix**:
* **Parameters**:
  * `goformId`: `WIFI_BASIC`
  * `lucknum_WIFI_BASIC`: Session token
  * `ssid`: Clean SSID name (up to 32 characters, supports spaces)
  * `broadcastssid`: `1` (Broadcast SSID) or `0` (Hidden SSID)
  * `wirelessmode`: `0` (`802.11 b/g/n` mixed) or `1` (`802.11n` only)
  * `channel`: `0` (Auto) or `1` through `11` (Fixed channel)
  * `Allow_MAX_STAs`: `1` through `8` (Maximum allowed connected clients)

### 3.2 Wi-Fi Security (`WIFI_SECURITY`)
* **Parameters**:
  * `goformId`: `WIFI_SECURITY`
  * `lucknum_WIFI_SECURITY`: Session token
  * `security_shared_mode`: `NONE` (WPA/WPA2) or `WEP`
  * `cipher`: `2` (AES / CCMP)
  * `passphrase`: WPA2 pre-shared key (8 to 63 ASCII characters)

### 3.3 Wi-Fi Sleep / Standby Timer (`WIFI_SLEEP`)
* **Parameters**:
  * `goformId`: `WIFI_SLEEP`
  * `lucknum_WIFI_SLEEP`: Session token
  * `sleep_mode`: `0` (Disabled) or `1` (Enabled)
  * `sleep_time`: Inactivity timeout before radio sleeps:
    * `5`, `10`, `20`, `30`, `60`, `120` (minutes)
    * `-1` (**Always On / Never Sleep**, default)

### 3.4 Cellular RAT Mode Selection (`NET_SELECT_NEW`)
Locks the cellular modem into specific radio access technology modes:
* **Parameters**:
  * `goformId`: `NET_SELECT_NEW`
  * `lucknum_NET_SELECT_NEW`: Session token
  * `net_select`: Target mode:
    * `Automatic` (Auto 2G/3G/4G)
    * `Only_4G` (LTE Band lock)
    * `Only_UMTS` (3G WCDMA)
    * `Only_GSM_EDGE` (2G GSM)
    * `Only_EVDO` (CDMA/EVDO)

### 3.5 Cellular WAN Connection Control (`NET_CONNECT`)
Enables connecting or disconnecting cellular data routing in Pocket Router mode:
* **Parameters**:
  * `goformId`: `NET_CONNECT`
  * `dial_mode`: `auto_dial` or `manual_dial`
  * `action`: `connect` or `disconnect`
  * `wan_conn_which_page`: `wan_operation`

### 3.6 Hardware Reboot (`device_reboot`)
Triggers an immediate software restart of the baseband processor:
* **Endpoint**: `GET /goform/goform_process?goformId=device_reboot`

### 3.7 Factory Reset (`RESTORE`)
Restores all settings and NVRAM vectors to factory defaults:
* **Parameters**:
  * `goformId`: `RESTORE`
  * `action_flag`: `restore`

### 3.8 DHCP Server Settings (`DHCP_SET`)
* **Parameters**:
  * `goformId`: `DHCP_SET`
  * `lanIp`: Gateway IP address (default: `192.168.100.1`)
  * `lanNetmask`: Subnet mask (default: `255.255.255.0`)
  * `dhcpStart`: Allocation start IP (default: `192.168.100.100`)
  * `dhcpEnd`: Allocation end IP (default: `192.168.100.200`)
  * `dhcpLease`: Lease time in hours (default: `24`)
  * `lanDhcpType`: `SERVER`

### 3.9 Data Counter Reset (`DATA_STATISTICS_CLEAR`)
Resets session and total cellular byte counters:
* **Parameters**:
  * `goformId`: `DATA_STATISTICS_CLEAR`
  * `action_flag`: `ALL`

---

## 4. Architectural Summary: Serial AT vs. Web GoForm

| Capability | Serial AT (`MI_01` / `/dev/ttyUSB1`) | Web GoForm (`192.168.100.1:80`) |
| :--- | :--- | :--- |
| **Availability** | Available via USB anytime | Available over local WLAN or reverse tether |
| **SSID Setting** | Appends factory 3-char BSSID suffix (`62C`) | Writes 100% clean, un-suffixed SSID |
| **Station List** | Unsupported (`AT^WIWL?` returns `ERROR`) | Supported (`station_list.asp`) |
| **Live Throughput** | Must compute from periodic `AT+FLOWQ?` | Real-time JSON stream (`refresh_data.asp`) |
| **Hardware Reboot** | `AT+CFUN=1,1` | `goformId=device_reboot` |
| **NVRAM Persistence**| `AT+WRWIFI` | Handled automatically or committed via `AT+WRWIFI` |
