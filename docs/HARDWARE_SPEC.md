# Reverse-Engineered Hardware Specification

## Qualcomm MDM9600 / Aleka UV310 4G LTE UFI Dongle

### 1. Executive Summary

This device is a multi-mode 4G LTE/3G cellular USB modem and portable Wi-Fi router (Pocket Wi-Fi / UFI dongle) manufactured by **Aleka Incorporated** under project code **UV310**. Originally sold around 2014–2016, it was commonly marketed under various white-label names (such as *EWangshikong 4G*, *Siptune LM-75*, or generic *4G LTE UFI*).

```
                      +------------------------------------------------+
                      |         Aleka UV310 USB 4G UFI Dongle          |
                      |                                                |
                      |   +--------------------+   SDIO   +----------+  |
+------------+  USB   |   |  Qualcomm MDM9600  |<-------->| Broadcom |  |=== 2.4 GHz
| Linux Host |<======>|   |  Baseband SoC      |          | Wi-Fi SoC|  |    Wi-Fi AP
+------------+        |   +---------+----------+          +----------+  |
                      |             |                                  |
                      |     SPI/I2C | MMC                              |
                      |   +---------+----------+                       |
                      |   | 32GB MicroSD Slot  |                       |
                      |   | Standard SIM Slot  |                       |
                      |   +--------------------+                       |
                      +------------------------------------------------+
```

---

### 2. Physical & Board Identifiers

| Parameter | Value | Source / AT Command |
| :--- | :--- | :--- |
| **Manufacturer** | ALEKA INCORPORATED | `AT^CONAME?` |
| **Project Code** | MDM9600 UV310 | `AT^PROJECTNAME?` |
| **Hardware Revision**| UV310-U-5.1 CGWL | `AT^HWVER?` |
| **CIGO Baseband ID** | MDM9200 / MDM9600 | `AT^CIGOID?` |
| **Firmware Revision**| `MDM9K-CIGO-U-7.3.9-4M, May 9 2018, 18:25:41` | `AT^SWVER?` / `ATI` |
| **Form Factor** | USB 2.0 Type-A Dongle with sliding SIM/MicroSD cover | Physical Inspection |
| **Power Input** | 5.0V DC ± 5%, Max 500mA (USB Bus Powered) | USB Device Descriptor |

---

### 3. Core Chipset Architecture

#### 3.1 Primary Cellular SoC: Qualcomm MDM9600
- **Silicon Family**: Qualcomm Gobi LTE / MDM9k generation.
- **Architecture**: Dual-core baseband processor running Qualcomm REX / AMSS RTOS.
- **Cellular Standards**:
  - **4G LTE FDD/TDD**: 3GPP Rel 9, Category 3 (up to 100 Mbps DL, 50 Mbps UL).
  - **3G UMTS/HSPA+**: Rel 7/8 HSPA+ (up to 42 Mbps DL).
  - **2G GSM/GPRS/EDGE**: Quad-band.
- **Baseband Interface**: Direct USB 2.0 High-Speed (480 Mbps) endpoint controller.

#### 3.2 Wireless LAN Co-Processor: Broadcom BRCM_WL
- **Standard**: IEEE 802.11b/g/n (Single stream, up to 65–72.2 Mbps PHY rate).
- **Frequency**: 2.412 GHz – 2.472 GHz (2.4 GHz ISM Band, Channels 1–13).
- **Antenna**: Internal omnidirectional PCB trace antenna.
- **Interconnect**: Interfaced to the Qualcomm MDM9600 via internal SDIO/UART bus.
- **Control**: Controlled from the host via vendor-specific Broadcom AT commands (`AT^WI...` and `AT+WIFI`).
- **Default SSID Format**: User-defined or `"TypeScript 420"62C` (with last 3 hex digits of BSSID).

#### 3.3 Storage Subsystem
- **Mass Storage Controller**: Qualcomm integrated MMC host controller.
- **Card Reader**: Push-pull slot for MicroSD / MicroSDHC (tested functional with 32 GB FAT32 media).
- **SCSI Emulation**: Bulk-Only Transport (BBB) SCSI device class `0x08`, Subclass `0x06`.

---

### 4. RF & Band Capabilities

Querying the band preference register (`AT$QCBANDPREF=?`) reveals firmware support for:

#### Supported Cellular Bands
- **CDMA / 1xRTT / EV-DO**:
  - BC0 (800 MHz)
  - BC1 (1900 MHz PCS)
  - BC3, BC4, BC6, BC7, BC8, BC9, BC10, BC11, BC12, BC14, BC15, BC16
- **GSM / GPRS / EDGE**:
  - GSM 850 / EGSM 900 / DCS 1800 / PCS 1900
- **UMTS / WCDMA**:
  - Band I (IMT 2100 MHz)
  - Band II (PCS 1900 MHz)
  - Band IV (AWS 1700/2100 MHz)
  - Band V (850 MHz)
  - Band VIII (900 MHz)
- **LTE (E-UTRAN)**:
  - Band 1 (2100 MHz), Band 3 (1800 MHz DCS), Band 7 (2600 MHz), Band 8 (900 MHz).
  - In Bangladesh, tested operating on **Robi 4G LTE (Band 3 / 1800 MHz, 31/31 -51 dBm full signal)** and **Teletalk 4G LTE**.


---

### 5. USB Descriptors & Pinout

#### 5.1 Physical Connector
- Standard USB Type-A Male (USB 2.0 High-Speed, 480 Mbps).
- Pin 1: VBUS (+5V)
- Pin 2: Data- (D-)
- Pin 3: Data+ (D+)
- Pin 4: GND (Ground)

#### 5.2 USB Endpoint Map (Post-Switch `05c6:6000`)
```
Endpoint Address  | Direction | Type      | Max Packet | Function
------------------+-----------+-----------+------------+---------------------------
0x81 (EP 1 IN)    | IN        | Interrupt | 64 bytes   | Interface 0 Status/Notify
0x82 (EP 2 IN)    | IN        | Bulk      | 512 bytes  | Interface 0 Data Rx (PPP/AT)
0x01 (EP 1 OUT)   | OUT       | Bulk      | 512 bytes  | Interface 0 Data Tx (PPP/AT)
0x83 (EP 3 IN)    | IN        | Bulk      | 512 bytes  | Interface 1 Data Rx (Control)
0x02 (EP 2 OUT)   | OUT       | Bulk      | 512 bytes  | Interface 1 Data Tx (Control)
0x84 (EP 4 IN)    | IN        | Bulk      | 512 bytes  | Interface 2 Voice PCM Audio Rx (MI_02)
0x03 (EP 3 OUT)   | OUT       | Bulk      | 512 bytes  | Interface 2 Voice PCM Audio Tx (MI_02)
0x85 (EP 5 IN)    | IN        | Bulk      | 512 bytes  | Interface 3 Data Rx (QCDM Diag)
0x04 (EP 4 OUT)   | OUT       | Bulk      | 512 bytes  | Interface 3 Data Tx (QCDM Diag)
0x05 (EP 5 OUT)   | OUT       | Bulk      | 512 bytes  | Interface 4 Mass Storage Tx
0x86 (EP 6 IN)    | IN        | Bulk      | 512 bytes  | Interface 4 Mass Storage Rx
```
