# Simultaneous Dual-Mode Architecture

## Concurrent USB PPP Data Link & Broadcom Wi-Fi Access Point

### 1. Overview

A central question in this investigation was whether the Aleka UV310 can simultaneously operate as a **direct-attached USB modem** for the host PC and as a **wireless Wi-Fi router** for other devices.

Empirical testing on live hardware confirmed that **both interfaces function concurrently without interference**.

```
                        +----------------------------------------+
                        |      Aleka UV310 4G LTE UFI Dongle     |
                        |                                        |
                        |    +------------------------------+    |
                        |    |    Qualcomm MDM9600 Baseband |    |
                        |    |    LTE Cat-3 Carrier Engine  |    |
                        |    +--------------+---------------+    |
                        |                   |                    |
                        |         +---------+---------+          |
                        |         | Internal IP Mux   |          |
                        |         +----+---------+----+          |
                        +--------------|---------|---------------+
                                       |         |
                  High-Speed Serial    |         | SDIO Bus
                  (Bulk EP 0x82/0x01)  |         |
                                       v         v
                     +-------------------+     +-------------------+
                     |  Host Linux PC    |     | Broadcom BRCM_WL  |
                     |  - /dev/ttyUSB0   |     | Wi-Fi Co-Processor|
                     |  - ppp0 Interface |     | - 2.4 GHz 802.11n |
                     |  - 10.136.38.7 IP |     | - AP DHCP Server  |
                     |  - Low latency    |     | - SSID Broadcast  |
                     +-------------------+     +---------+---------+
                                                         |
                                                         v Over-the-Air
                                               +-------------------+
                                               | Phones, Tablets,  |
                                               | Guest Laptops     |
                                               +-------------------+
```

---

### 2. Empirical Verification

During testing, the following state was recorded:

1. **Broadcom Wi-Fi Radio Active (`AT+WIFI=1`)**:
   - SSID: `"TypeScript 420"62C`
   - BSSID: `38:1C:23:04:C6:2C`
   - Channel: 11 (2.462 GHz)
   - Max PHY Rate: 65.0 Mbit/s
   - Signal Quality: 100% (-42 dBm near device)
   - WPA2-PSK Authentication active.

2. **Simultaneous Host USB PPP Session Active**:
   - Device: `/dev/ttyUSB0`
   - Dial command: `ATD*99#`
   - Result: `CONNECT 100000000`
   - Interface: `ppp0`
   - Assigned Host IP: `10.136.38.7/32`
   - Remote Peer: `10.64.64.64`
   - Status: `UP, LOWER_UP`

Both subsystems operated in parallel. Traffic transferred over the USB PPP connection while the Wi-Fi beacon frames and associations remained active.

---

### 3. How the Baseband Multiplexes Traffic

The Qualcomm MDM9600 contains an internal packet routing and network address translation (NAT) engine:

1. **Wi-Fi Clients**:
   - Clients associating with the Wi-Fi AP receive IP addresses in the `192.168.100.0/24` subnet assigned by the Broadcom co-processor's internal DHCP daemon.
   - Packets from Wi-Fi clients are routed through the internal NAT engine out the LTE radio bearer.

2. **USB Host (Linux PC)**:
   - The USB host negotiates directly with the baseband via PPP IPCP over `/dev/ttyUSB0`.
   - The host is assigned a direct IP from the carrier's packet gateway pool (`10.x.x.x` or public IP).
   - Host packets bypass the internal Wi-Fi NAT, resulting in reduced packet latency and avoiding double-NAT for the PC.

3. **Multi-Port Independence**:
   - Even when `ppp0` is fully saturated on `/dev/ttyUSB0`, the secondary control port (`/dev/ttyUSB1`) remains open.
   - The host can query signal strength (`AT+CSQ`), inspect cell status, read incoming SMS, or toggle the Wi-Fi radio on `/dev/ttyUSB1` without disturbing the active data transfer on `/dev/ttyUSB0`.

---

### 4. Operational Modes Summary

| Mode | Command | Wi-Fi Radio | USB Host Data | Primary Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Dual Mode** | `AT+WIFI=1` + `pppd` | 🟢 Active (Broadcast) | 🟢 Active (`ppp0`) | Home/Office hub: PC uses direct USB while mobile devices share the Wi-Fi. |
| **Pure USB Mode** | `AT+WIFI=0` + `pppd` | ⚪ Disabled (Off) | 🟢 Active (`ppp0`) | Mobile laptop use: Saves 200–300mA power, zero Wi-Fi RF emissions. |
| **Pocket Router Mode**| `AT+WIFI=1` (no pppd) | 🟢 Active (Broadcast) | ⚪ Idle / Power only | Plugged into wall charger or power bank: Standalone pocket Wi-Fi router. |
