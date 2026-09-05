# MicroSD Storage & Self-Contained Bundling Specification

## Qualcomm MDM9600 MMC Subsystem & Packaging Architecture

### 1. Hardware Storage Controller Limits

#### 1.1 Specification & Maximum Capacity
- **Host Controller**: Integrated Qualcomm SDCC (Secure Digital Card Controller) embedded within the MDM9600 SoC.
- **Specification Standard**: SD Memory Card Specification **v2.00 (SDHC)** and MMC Specification **v4.3**.
- **Maximum Supported Size**: **32 GB (Hard SDHC Ceiling)**.
  - While physical dimensions are identical across SD, SDHC, and SDXC cards, the MDM9600 firmware and boot ROM lack support for **SD 3.0 (UHS-I 1.8V bus signaling)** and the **exFAT** filesystem.
  - Cards formatted as SDXC (64 GB, 128 GB, etc.) will fail to initialize or experience address-wrapping corruptions if forced into FAT32 mode.
  - **Conclusion**: The **32 GB MicroSDHC card** currently installed is the maximum possible capacity supported by this hardware.

#### 1.2 Speed Class & Bus Performance
- **Supported Standards**: Standard Class 2, Class 4, Class 6, and **Class 10**.
- **UHS Compatibility**: UHS-I cards (U1/U3/V10/V30) function in backward-compatible High Speed (HS) 3.3V mode at up to a 50 MHz bus clock (theoretical 25 MB/s maximum).
- **USB Throughput**: Over the USB 2.0 Bulk-Only mass storage endpoint (`Interface 4`), realistic transfer speeds are:
  - **Sequential Read**: ~12–18 MB/s
  - **Sequential Write**: ~8–14 MB/s

---

### 2. Self-Contained Upgrade Strategy (The Portable Linux Deliverable)

Because rewriting the internal NAND flash partition (where the 3.1 MiB ZeroCD lives) risks corrupting baseband NVRAM radio calibration data (`qcn`), the **MicroSD slot provides the ideal medium for self-contained software distribution**.

#### 2.1 Proposed Card Layout

```
+-------------------------------------------------------------------------+
|                  32 GB MicroSD Card Partitioning Layout                 |
+------------------------------------+------------------------------------+
|  Partition 1: UFI_TOOLKIT (1 GB)   |  Partition 2: UFI_STORAGE (31 GB)  |
|  - Filesystem: FAT32 (Cross-OS)    |  - Filesystem: FAT32 or exFAT      |
|  - 1-Click install.sh              |  - Personal file storage           |
|  - Standalone ufi-modem CLI        |  - Wi-Fi shared media/NAS folder   |
|  - Modern KDE / Qt6 GUI App        |  - Offline documentation mirror    |
|  - Offline dependencies cache      |                                    |
|  - udev & PPP system configs       |                                    |
+------------------------------------+------------------------------------+
```

#### 2.2 The "Zero-Internet" First-Plug Experience
When you plug this dongle into ANY new or disconnected Linux machine:
1. The mass storage partition (`UFI_TOOLKIT`) automounts immediately.
2. The user executes:
   ```bash
   cd /run/media/$USER/UFI_TOOLKIT && ./install.sh
   ```
3. The installer installs the udev rules, copies the CLI/GUI binaries, sets permissions, and starts the service.
4. Within 5 seconds, the PC is online through the modem with no prior internet connection required.
