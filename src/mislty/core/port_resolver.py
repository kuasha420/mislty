"""
mislty.core.port_resolver
~~~~~~~~~~~~~~~~~~~~~~~~~

Deterministic hardware interface resolution for Qualcomm MDM9600 (Aleka UV310) modems.
Resolves the 4 physical USB serial endpoints (MI_00 to MI_03) via udev symlinks or
direct sysfs tree crawling, detects ZeroCD mass-storage state, and discovers
auxiliary Wi-Fi interfaces for Dual-Plane testing.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ModemPorts:
    """
    Data container representing the resolved endpoints of the modem.
    """
    data: Optional[Path] = None          # MI_00: Data Plane / PPP (/dev/mislty/modem)
    control: Optional[Path] = None       # MI_01: Control Plane / AT (/dev/mislty/control)
    voice: Optional[Path] = None         # MI_02: Voice PCM Audio (/dev/mislty/voice)
    diag: Optional[Path] = None          # MI_03: QCDM / Diagnostics (/dev/mislty/diag)
    aux_wifi: Optional[str] = None       # Auxiliary Wi-Fi interface (e.g. "wlan1")
    aux_wifi_netns: Optional[str] = None # Netns containing aux Wi-Fi (e.g. "wifi-client")
    sysfs_path: Optional[Path] = None    # Path to USB device in sysfs
    vid: Optional[str] = None            # USB Vendor ID (e.g. "05c6")
    pid: Optional[str] = None            # USB Product ID (e.g. "6000" or "f000")
    is_present: bool = False             # Device detected on bus in any state
    is_zerocd: bool = False              # Device in ZeroCD mass storage mode

    @property
    def is_ready(self) -> bool:
        """
        Returns True if the essential ports (control and data) are resolved.
        """
        return bool(self.control and self.data and self.is_present)

    @property
    def is_complete(self) -> bool:
        """
        Returns True if all 4 serial endpoints are resolved.
        """
        return bool(
            self.data and self.control and self.voice and self.diag and self.is_present
        )

    def as_dict(self) -> Dict[str, Any]:
        """
        Serialize ports mapping to a dictionary.
        """
        return {
            "data": str(self.data) if self.data else None,
            "control": str(self.control) if self.control else None,
            "voice": str(self.voice) if self.voice else None,
            "diag": str(self.diag) if self.diag else None,
            "aux_wifi": self.aux_wifi,
            "aux_wifi_netns": self.aux_wifi_netns,
            "sysfs_path": str(self.sysfs_path) if self.sysfs_path else None,
            "vid": self.vid,
            "pid": self.pid,
            "is_present": self.is_present,
            "is_zerocd": self.is_zerocd,
            "is_ready": self.is_ready,
            "is_complete": self.is_complete,
        }

    def __str__(self) -> str:
        status = "Present (Ready)" if self.is_ready else ("ZeroCD Mode" if self.is_zerocd else "Not Found")
        lines = [
            f"Modem Status: {status} [VID={self.vid or 'N/A'}:PID={self.pid or 'N/A'}]",
            f"  • Data Plane   (MI_00): {self.data or 'None'}",
            f"  • Control / AT (MI_01): {self.control or 'None'}",
            f"  • Voice / PCM  (MI_02): {self.voice or 'None'}",
            f"  • Diagnostic   (MI_03): {self.diag or 'None'}",
        ]
        if self.aux_wifi:
            ns_info = f" (netns: {self.aux_wifi_netns})" if self.aux_wifi_netns else ""
            lines.append(f"  • Aux Wi-Fi           : {self.aux_wifi}{ns_info}")
        if self.sysfs_path:
            lines.append(f"  • Sysfs Path          : {self.sysfs_path}")
        return "\n".join(lines)


class PortResolver:
    """
    Deterministic hardware endpoint resolver.
    """

    DEFAULT_VID = "05c6"
    DEFAULT_PID = "6000"
    ZEROCD_PID = "f000"

    # USB interface number (bInterfaceNumber) mapping to endpoint roles
    INTERFACE_MAP = {
        "00": "data",
        "01": "control",
        "02": "voice",
        "03": "diag",
    }

    DEFAULT_UDEV_DIR = Path("/dev/mislty")
    DEFAULT_SYSFS_USB_ROOT = Path("/sys/bus/usb/devices")
    DEFAULT_SYSFS_NET_ROOT = Path("/sys/class/net")

    def __init__(
        self,
        target_vid: str = DEFAULT_VID,
        target_pid: str = DEFAULT_PID,
        zerocd_pid: str = ZEROCD_PID,
        udev_dir: Path = DEFAULT_UDEV_DIR,
        sysfs_usb_root: Path = DEFAULT_SYSFS_USB_ROOT,
        sysfs_net_root: Path = DEFAULT_SYSFS_NET_ROOT,
    ) -> None:
        self.target_vid = target_vid.lower()
        self.target_pid = target_pid.lower()
        self.zerocd_pid = zerocd_pid.lower()
        self.udev_dir = Path(udev_dir)
        self.sysfs_usb_root = Path(sysfs_usb_root)
        self.sysfs_net_root = Path(sysfs_net_root)

    def resolve(self, prefer_udev: bool = True) -> ModemPorts:
        """
        Resolve modem endpoints.

        1. Checks for ZeroCD mass-storage state.
        2. If prefer_udev is True and canonical /dev/mislty symlinks exist,
           resolves via udev symlinks.
        3. Falls back to scanning sysfs topology directly by querying
           bInterfaceNumber on matching USB devices.
        4. Detects auxiliary Wi-Fi interfaces if present.
        """
        # 1. Check for ZeroCD state
        zerocd_ports = self._detect_zerocd()
        if zerocd_ports:
            aux_iface, aux_ns = self.detect_aux_wifi()
            zerocd_ports.aux_wifi = aux_iface
            zerocd_ports.aux_wifi_netns = aux_ns
            return zerocd_ports

        # 2. Try udev symlinks if requested
        if prefer_udev and self.udev_dir.exists():
            udev_ports = self._resolve_from_udev()
            if udev_ports and udev_ports.is_ready:
                aux_iface, aux_ns = self.detect_aux_wifi()
                udev_ports.aux_wifi = aux_iface
                udev_ports.aux_wifi_netns = aux_ns
                return udev_ports

        # 3. Fallback to direct sysfs crawl
        sysfs_ports = self._resolve_from_sysfs()
        if sysfs_ports:
            aux_iface, aux_ns = self.detect_aux_wifi()
            sysfs_ports.aux_wifi = aux_iface
            sysfs_ports.aux_wifi_netns = aux_ns
            return sysfs_ports

        # Not found
        aux_iface, aux_ns = self.detect_aux_wifi()
        return ModemPorts(
            is_present=False,
            is_zerocd=False,
            aux_wifi=aux_iface,
            aux_wifi_netns=aux_ns,
        )

    def _detect_zerocd(self) -> Optional[ModemPorts]:
        """
        Check if the modem is stuck in ZeroCD mass storage mode (VID:f000).
        """
        if not self.sysfs_usb_root.exists():
            return None

        for dev_path in self.sysfs_usb_root.iterdir():
            vid_file = dev_path / "idVendor"
            pid_file = dev_path / "idProduct"

            if vid_file.is_file() and pid_file.is_file():
                try:
                    vid = vid_file.read_text(encoding="utf-8").strip().lower()
                    pid = pid_file.read_text(encoding="utf-8").strip().lower()
                    if vid == self.target_vid and pid == self.zerocd_pid:
                        return ModemPorts(
                            sysfs_path=dev_path.resolve(),
                            vid=vid,
                            pid=pid,
                            is_present=True,
                            is_zerocd=True,
                        )
                except (OSError, UnicodeDecodeError):
                    continue

        return None

    def _resolve_from_udev(self) -> Optional[ModemPorts]:
        """
        Resolve endpoints from canonical /dev/mislty/ directory symlinks.
        """
        if not self.udev_dir.is_dir():
            return None

        def _find_dev(candidates: List[str]) -> Optional[Path]:
            for name in candidates:
                candidate = self.udev_dir / name
                if candidate.exists():
                    return candidate
            return None

        data_dev = _find_dev(["data", "modem"])
        ctrl_dev = _find_dev(["control", "at"])
        voice_dev = _find_dev(["voice", "pcm"])
        diag_dev = _find_dev(["diag", "qcdm"])

        if not (data_dev and ctrl_dev):
            return None

        # Trace sysfs parent and VID/PID from control device
        sysfs_path = None
        vid = None
        pid = None

        try:
            real_ctrl = ctrl_dev.resolve()
            tty_name = real_ctrl.name
            tty_sysfs = Path("/sys/class/tty") / tty_name / "device"
            if tty_sysfs.exists():
                # Walk up to the USB device parent
                curr = tty_sysfs.resolve()
                while curr != curr.parent:
                    v_file = curr / "idVendor"
                    p_file = curr / "idProduct"
                    if v_file.is_file() and p_file.is_file():
                        vid = v_file.read_text(encoding="utf-8").strip().lower()
                        pid = p_file.read_text(encoding="utf-8").strip().lower()
                        sysfs_path = curr
                        break
                    curr = curr.parent
        except OSError:
            pass

        return ModemPorts(
            data=data_dev,
            control=ctrl_dev,
            voice=voice_dev,
            diag=diag_dev,
            sysfs_path=sysfs_path,
            vid=vid or self.target_vid,
            pid=pid or self.target_pid,
            is_present=True,
            is_zerocd=False,
        )

    def _resolve_from_sysfs(self) -> Optional[ModemPorts]:
        """
        Walk sysfs to locate the USB device and map interfaces by bInterfaceNumber.
        """
        if not self.sysfs_usb_root.exists():
            return None

        for dev_path in self.sysfs_usb_root.iterdir():
            vid_file = dev_path / "idVendor"
            pid_file = dev_path / "idProduct"

            if not (vid_file.is_file() and pid_file.is_file()):
                continue

            try:
                vid = vid_file.read_text(encoding="utf-8").strip().lower()
                pid = pid_file.read_text(encoding="utf-8").strip().lower()
            except (OSError, UnicodeDecodeError):
                continue

            if vid == self.target_vid and pid == self.target_pid:
                # Found matching modem USB device!
                ports = self._map_interfaces_from_sysfs_device(dev_path)
                ports.vid = vid
                ports.pid = pid
                ports.sysfs_path = dev_path.resolve()
                ports.is_present = True
                ports.is_zerocd = False
                return ports

        return None

    def _map_interfaces_from_sysfs_device(self, dev_path: Path) -> ModemPorts:
        """
        Given a sysfs USB device path, scan interface children and extract TTY device paths.
        """
        resolved_endpoints: Dict[str, Path] = {}

        # Look for interface subdirectories (e.g. 1-3:1.0, 1-3:1.1, etc.)
        for iface_path in dev_path.iterdir():
            b_iface_file = iface_path / "bInterfaceNumber"
            if not b_iface_file.is_file():
                continue

            try:
                iface_num = b_iface_file.read_text(encoding="utf-8").strip().zfill(2)
            except (OSError, UnicodeDecodeError):
                continue

            role = self.INTERFACE_MAP.get(iface_num)
            if not role:
                continue

            # Locate child tty node
            tty_dev = self._find_tty_under_interface(iface_path)
            if tty_dev:
                resolved_endpoints[role] = tty_dev

        return ModemPorts(
            data=resolved_endpoints.get("data"),
            control=resolved_endpoints.get("control"),
            voice=resolved_endpoints.get("voice"),
            diag=resolved_endpoints.get("diag"),
        )

    def _find_tty_under_interface(self, iface_path: Path) -> Optional[Path]:
        """
        Locate the /dev/ttyUSB* node associated with an interface.
        """
        # Pattern 1: Direct child ttyUSB* directory (common in Linux sysfs)
        for child in iface_path.iterdir():
            if child.name.startswith("ttyUSB") and child.is_dir():
                dev_node = Path("/dev") / child.name
                if dev_node.exists():
                    return dev_node

        # Pattern 2: Nested under tty/ subdirectory
        tty_sub = iface_path / "tty"
        if tty_sub.is_dir():
            for child in tty_sub.iterdir():
                if child.name.startswith("ttyUSB") or child.name.startswith("tty"):
                    dev_node = Path("/dev") / child.name
                    if dev_node.exists():
                        return dev_node

        return None

    def detect_aux_wifi(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Detect auxiliary Wi-Fi interfaces used for dual-plane testing.
        Returns a tuple of (interface_name, netns_name).
        """
        # 1. Identify primary interface (e.g. default route interface or wlan0)
        primary_iface = self._get_primary_net_interface()

        # 2. Check host namespace
        if self.sysfs_net_root.exists():
            for iface in self.sysfs_net_root.iterdir():
                name = iface.name
                if name in ("lo", primary_iface, "wlan0"):
                    continue
                # Check for wireless attributes
                if (iface / "wireless").exists() or (iface / "phy80211").exists():
                    return (name, None)

        # 3. Check network namespaces (e.g. wifi-client)
        netns_candidates = ["wifi-client"]
        run_netns = Path("/run/netns")
        if run_netns.exists():
            for ns_file in run_netns.iterdir():
                if ns_file.name not in netns_candidates:
                    netns_candidates.append(ns_file.name)

        for ns in netns_candidates:
            found_iface = self._inspect_netns_for_wifi(ns)
            if found_iface:
                return (found_iface, ns)

        return (None, None)

    def _get_primary_net_interface(self) -> Optional[str]:
        """
        Identify the default route interface on the host.
        """
        # Try reading /proc/net/route
        route_file = Path("/proc/net/route")
        if route_file.is_file():
            try:
                for line in route_file.read_text(encoding="utf-8").splitlines()[1:]:
                    fields = line.split()
                    if len(fields) >= 2 and fields[1] == "00000000":
                        return fields[0]
            except OSError:
                pass

        # Fallback to ip route show default
        try:
            res = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0:
                parts = res.stdout.strip().split()
                if "dev" in parts:
                    return parts[parts.index("dev") + 1]
        except (OSError, subprocess.SubprocessError):
            pass

        return None

    def _inspect_netns_for_wifi(self, netns: str) -> Optional[str]:
        """
        Check if a given network namespace contains a Wi-Fi interface.
        """
        # Try unprivileged ip -n first, then sudo -n
        commands = [
            ["ip", "-n", netns, "-o", "link", "show"],
            ["sudo", "-n", "ip", "-n", netns, "-o", "link", "show"],
        ]

        for cmd in commands:
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=1.5,
                )
                if res.returncode == 0:
                    for line in res.stdout.splitlines():
                        # Format: index: <name>: <flags> ...
                        fields = line.split(": ")
                        if len(fields) >= 2:
                            iface_name = fields[1].split("@")[0].strip()
                            if iface_name.startswith(("wlan", "wlp", "wlx")):
                                return iface_name
                    # Even if no wlan-prefixed name, check if any non-loopback link exists
                    for line in res.stdout.splitlines():
                        fields = line.split(": ")
                        if len(fields) >= 2:
                            iface_name = fields[1].split("@")[0].strip()
                            if iface_name != "lo":
                                return iface_name
            except (OSError, subprocess.SubprocessError):
                continue

        return None

    def switch_zerocd(self) -> bool:
        """
        Attempt to switch the modem out of ZeroCD mass storage mode (05c6:f000)
        into composite communication mode (05c6:6000) using usb_modeswitch.
        """
        cmd = [
            "usb_modeswitch",
            "-v", self.target_vid,
            "-p", self.zerocd_pid,
            "-J",
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5.0)
            return res.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
