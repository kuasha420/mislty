# Linux Compatibility Guide & Historical Failure Analysis

## Why the Aleka UV310 Failed on Linux in 2015–2016, and How It Was Solved

### 1. The Historical Mystery

In 2015–2016, plugging this modem into a Linux PC resulted in a baffling user experience:
1. The USB drive powered on.
2. The onboard Wi-Fi router started broadcasting its network (`TypeScript 420`).
3. But the Linux host PC showed **no internet connection, no network device (`usb0` / `wwan0`), and no Mobile Broadband option in NetworkManager**.
4. The user was forced to purchase a separate USB Wi-Fi adapter just to connect to the dongle's own Wi-Fi network from the same PC.

---

### 2. Root Cause Analysis

By analyzing kernel traces, driver module tables, and system core dumps, three distinct failures were identified:

```
[Hardware Insertion]
        |
        v
[Initial USB ID: 05c6:f000]
        |
        v usb_modeswitch (SCSI Eject)
[Re-enumerates as 05c6:6000]
        |
        +---> [Kernel Driver Trap]
        |     option.ko claims ALL 4 interfaces as serial ports (/dev/ttyUSB0..3)
        |     No Ethernet/RNDIS netdev (ethX / usb0) is created by the kernel.
        |
        +---> [The ModemManager Crash]
        |     ModemManager probes ports concurrently.
        |     Duplicate Qualcomm response strings cause SIGSEGV in g_hash_table_lookup.
        |     NetworkManager never receives a valid modem device.
        |
        +---> [Baseband Default Fallback]
              With no USB data session initiated by the host,
              the dongle remains in standalone Wi-Fi AP router mode.
```

#### Failure 1: The Linux Kernel `option` Driver Trap
In the Linux kernel's `drivers/usb/serial/option.c`, the following device table entry exists:
```c
{ USB_DEVICE(0x05c6, 0x6000) }
```
Because `USB_DEVICE` matches Vendor and Product ID without specifying an interface subclass or protocol, the `option` driver binds greedily to **all four vendor-specific interfaces** (0, 1, 2, and 3), generating `/dev/ttyUSB0` through `/dev/ttyUSB3`.

Unlike modern Android or LTE sticks that present a virtual RNDIS/CDC-ECM Ethernet adapter, this device operates as a serial AT/PPP composite modem. The Linux kernel does not automatically configure an IP address on a serial device.

#### Failure 2: The ModemManager SIGSEGV Core Dump (The Smoking Gun)
When desktop environments (GNOME, KDE Plasma) run, `ModemManager` automatically scans all `/dev/ttyUSB*` ports. When probing `05c6:6000`, ModemManager sends AT inquiries to determine device capability:
- `/dev/ttyUSB0` responds: `Manufacturer: QUALCOMM INCORPORATED, Model: 0, Revision: MDM9K...`
- `/dev/ttyUSB1` responds with the **exact same strings**.
- `/dev/ttyUSB2` is the raw PCM audio device port (`pcmWave.dll`) which handles 16-bit 8000 Hz audio streams rather than Hayes AT commands.
- `/dev/ttyUSB3` is a binary QCDM diagnostic port.

During port grouping and plugin dispatch (specifically in the `generic` and `icera` probing plugins), ModemManager encounters an unhandled pointer exception when organizing ports reporting duplicate identifiers, resulting in an immediate segmentation fault:

```text
systemd-coredump: Process 341782 (ModemManager) dumped core.
Stack trace of thread 341782:
#0  0x0000564f5f047a2b n/a (ModemManager + 0x14ca2b)
#1  0x00007fbbff96f9cc g_hash_table_lookup (libglib-2.0.so.0 + 0x4a9cc)
#2  0x0000564f5f04f250 n/a (ModemManager + 0x154250)
...
ModemManager.service: Main process exited, code=dumped, status=11/SEGV
```
Because ModemManager continuously crashed and restarted in a failure loop, NetworkManager was never notified of a working mobile broadband device.

#### Failure 3: Baseband Default Fallback
With no host initiating an AT dialup connection (`ATD*99#`), the onboard firmware defaulted to its standalone battery/car-charger mode: powering up the Broadcom Wi-Fi radio, starting its internal DHCP server, and broadcasting Wi-Fi.

---

### 3. The 2026 Modern Linux Solution

The solution bypasses the crashing generic probes and establishes a direct, optimized PPP link over the primary serial port.

#### Step 1: Fix Serial Device Permissions (udev)
Create `/etc/udev/rules.d/99-ufi-permissions.rules`:
```udev
KERNEL=="ttyUSB*", SUBSYSTEMS=="usb", ATTRS{idVendor}=="05c6", ATTRS{idProduct}=="6000", MODE="0666", GROUP="uucp"
```
This grants normal users and background services read/write access to the modem ports without requiring root for simple AT queries.

#### Step 2: Cellular-Optimized PPP Options
In `/etc/ppp/peers/ufi`:
```text
/dev/ttyUSB0
115200
connect "/usr/bin/chat -v -f /etc/ppp/chat-ufi"
noauth
nodefaultroute       # Prevents disconnecting primary Wi-Fi
usepeerdns
persist
maxfail 5
holdoff 3
debug
crtscts
lock
local
hide-password
default-asyncmap
novj                 # Disable VJ header compression (rejected by 3GPP LTE)
novjccomp
noccp                # Disable CCP compression (rejected by 3GPP LTE)
ipcp-accept-local
ipcp-accept-remote
```

#### Step 3: Cellular Chat Script
In `/etc/ppp/chat-ufi`:
```chat
ABORT 'BUSY'
ABORT 'NO CARRIER'
ABORT 'NO DIALTONE'
ABORT 'ERROR'
TIMEOUT 15
'' AT
OK 'AT+CGDCONT=1,"IP","internet"'
OK 'ATD*99#'
CONNECT \c
```
*Note: The `\c` escape is critical. Without `\c`, chat sends a trailing carriage return after `CONNECT`, which interrupts the Qualcomm baseband's HDLC frame parser.*
