"""
mislty.net.wifi_relay
~~~~~~~~~~~~~~~~~~~~~

Simultaneous 4G Modem + Wi-Fi Hotspot Relay supervisor.
Orchestrates secondary/assist WLAN hardware (e.g. TP-Link USB dongles, auxiliary Wi-Fi chips),
provisions Linux softAPs via NetworkManager in AP shared mode, and configures kernel NAT
masquerading and policy routing (table 420) over ppp0 without disrupting the host's
primary Wi-Fi connection.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple, Union

from mislty.net.helper_client import NetworkHelperClient

logger = logging.getLogger("mislty.net.relay")


@dataclass
class WlanDevice:
    """Represents a discovered wireless network adapter on the host."""
    iface: str
    phy: str = ""
    driver: str = ""
    vendor: str = ""
    model: str = ""
    mac: str = ""
    state: str = "disconnected"
    is_primary: bool = False
    is_in_use: bool = False
    active_connection: Optional[str] = None
    supports_ap: bool = False
    is_candidate: bool = False

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelayClient:
    """Represents a connected wireless station on the assist hotspot."""
    mac: str
    ip: Optional[str] = None
    hostname: Optional[str] = None
    signal_dbm: Optional[int] = None
    rx_bytes: int = 0
    tx_bytes: int = 0
    inactive_ms: int = 0

    def as_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RelayStatus:
    """Current telemetry state of the assist Wi-Fi hotspot relay."""
    active: bool = False
    interface: Optional[str] = None
    ssid: Optional[str] = None
    password: Optional[str] = None
    channel: int = 11
    band: str = "bg"
    ip_address: Optional[str] = None
    wan_iface: str = "ppp0"
    start_time: float = 0.0
    client_count: int = 0
    uptime_seconds: int = 0

    def as_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.active and self.start_time > 0:
            data["uptime_seconds"] = int(time.time() - self.start_time)
        return data


class WifiRelayManager:
    """
    Supervisor for assist Wi-Fi Hotspot Relay provisioning and packet forwarding.
    """

    CON_NAME = "mislty-relay"

    def __init__(
        self,
        helper: Optional[NetworkHelperClient] = None,
        sys_net_path: Optional[Union[str, Path]] = None,
    ) -> None:
        self.helper = helper or NetworkHelperClient()
        self.sys_net_path = Path(sys_net_path) if sys_net_path else Path("/sys/class/net")
        self._status = RelayStatus()

    def get_active_wifi_devices(self) -> Dict[str, str]:
        """
        Identify all Wi-Fi network interfaces that are actively connected to an
        external network (e.g. host Wi-Fi uplink). Excludes mislty-relay softAP.
        Returns a mapping of {interface_name: connection_name}.
        """
        active: Dict[str, str] = {}

        # 1. Query NetworkManager device status
        try:
            res = subprocess.run(
                ["nmcli", "-t", "-f", "DEVICE,TYPE,STATE,CONNECTION", "d"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.strip().split(":")
                    if len(parts) >= 4:
                        dev = parts[0].strip()
                        dev_type = parts[1].strip()
                        state = parts[2].strip()
                        con = ":".join(parts[3:]).strip()
                        if dev_type == "wifi" and state.startswith("connected"):
                            # Exclude our own relay softAP connection
                            if con != self.CON_NAME:
                                active[dev] = con or "connected"
        except Exception as exc:
            logger.debug("Failed to query nmcli for active devices: %s", exc)

        # 2. Check kernel default route as fallback
        try:
            res = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.strip().split()
                    if "dev" in parts:
                        dev = parts[parts.index("dev") + 1]
                        if not dev.startswith("ppp") and not dev.startswith("mislty") and dev not in active:
                            dev_dir = self.sys_net_path / dev
                            if (dev_dir / "wireless").exists() or (dev_dir / "phy80211").exists():
                                active[dev] = "default-route"
        except Exception as exc:
            logger.debug("Failed to query ip route for primary dev: %s", exc)

        return active

    def get_primary_interface(self) -> Optional[str]:
        """
        Identify the host's primary active Wi-Fi interface, if any.
        Returns None when the host has no active Wi-Fi connection (e.g. PPP-only mode).
        """
        active = self.get_active_wifi_devices()
        return next(iter(active.keys()), None)

    def list_devices(self) -> List[WlanDevice]:
        """
        Enumerate all host wireless network interfaces, discovering hardware drivers,
        vendor/model info, AP mode capability, and determining relay candidates.
        Host Link Protection is dynamic state-based: only devices currently connected
        to an external network are protected. Any idle/disconnected device supporting
        AP mode is marked as an available candidate.
        """
        devices: List[WlanDevice] = []
        active_wifi = self.get_active_wifi_devices()

        net_path = self.sys_net_path
        if not net_path.exists():
            return devices

        for iface_dir in sorted(net_path.iterdir()):
            iface = iface_dir.name
            # Check if wireless interface (has wireless/ or phy80211 link)
            is_wireless = (iface_dir / "wireless").exists() or (iface_dir / "phy80211").exists()
            if not is_wireless:
                continue

            # Read MAC address
            mac = ""
            mac_file = iface_dir / "address"
            if mac_file.is_file():
                try:
                    mac = mac_file.read_text(encoding="utf-8").strip()
                except OSError:
                    pass

            # Resolve phy
            phy = ""
            phy_link = iface_dir / "phy80211"
            if phy_link.exists():
                try:
                    phy = os.path.basename(os.readlink(str(phy_link)))
                except OSError:
                    pass

            # Check operstate
            state = "disconnected"
            oper_file = iface_dir / "operstate"
            if oper_file.is_file():
                try:
                    state = oper_file.read_text(encoding="utf-8").strip()
                except OSError:
                    pass

            # Gather vendor, model, and driver via udevadm
            driver, vendor, model = self._query_udev_info(iface)

            # Check AP capability via iw phy
            supports_ap = self._check_ap_support(phy, iface)

            # Dynamic state-based host link protection:
            # Protected only if actively connected to an external Wi-Fi network.
            is_in_use = (iface in active_wifi)
            active_con = active_wifi.get(iface)
            is_primary = is_in_use  # Kept for backward compatibility
            is_candidate = supports_ap and not is_in_use

            devices.append(WlanDevice(
                iface=iface,
                phy=phy,
                driver=driver,
                vendor=vendor,
                model=model,
                mac=mac,
                state=state,
                is_primary=is_primary,
                is_in_use=is_in_use,
                active_connection=active_con,
                supports_ap=supports_ap,
                is_candidate=is_candidate,
            ))

        return devices

    def _query_udev_info(self, iface: str) -> Tuple[str, str, str]:
        """Query driver, vendor, and model strings for interface via udevadm."""
        driver, vendor, model = "", "", ""
        try:
            res = subprocess.run(
                ["udevadm", "info", "-p", f"/sys/class/net/{iface}"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode == 0:
                props: Dict[str, str] = {}
                for line in res.stdout.splitlines():
                    if line.startswith("E: "):
                        k, _, v = line[3:].partition("=")
                        props[k.strip()] = v.strip()

                driver = props.get("ID_NET_DRIVER", "")
                vendor = props.get("ID_VENDOR_FROM_DATABASE") or props.get("ID_VENDOR", "")
                model = props.get("ID_MODEL_FROM_DATABASE") or props.get("ID_MODEL", "")

                # Clean up vendor/model if empty
                if not vendor and "rtw" in driver.lower():
                    vendor = "Realtek"
                elif not vendor and "iwl" in driver.lower():
                    vendor = "Intel"

                if not model and driver:
                    model = f"{driver} Wireless Adapter"
        except Exception as exc:
            logger.debug("udevadm query failed for %s: %s", iface, exc)

        return driver, vendor, model

    def _check_ap_support(self, phy: str, iface: str) -> bool:
        """Check if interface/phy supports Access Point (AP) operation."""
        # 1. Check via iw phy
        if phy:
            try:
                res = subprocess.run(
                    ["iw", "phy", phy, "info"],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                if res.returncode == 0:
                    in_modes = False
                    for line in res.stdout.splitlines():
                        stripped = line.strip()
                        if "Supported interface modes:" in stripped:
                            in_modes = True
                            continue
                        if in_modes:
                            if stripped.startswith("*"):
                                mode = stripped.lstrip("* ").strip()
                                if mode == "AP":
                                    return True
                            elif not line.startswith("\t") and stripped:
                                in_modes = False
            except Exception as exc:
                logger.debug("iw phy query failed for %s: %s", phy, exc)

        # 2. Check via iw list fallback
        try:
            res = subprocess.run(
                ["iw", "dev", iface, "info"],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode == 0 and "type AP" in res.stdout:
                return True
        except Exception:
            pass

        return False

    def start_relay(
        self,
        interface: str = "wlan1",
        ssid: str = "MisLTy 4G Share",
        password: Optional[str] = "mislty420",
        band: str = "bg",
        channel: int = 11,
        wan_iface: str = "ppp0",
    ) -> Dict[str, Any]:
        """
        Provision assist Wi-Fi softAP on specified interface, activate NAT packet
        forwarding, and attach table 420 policy routing to steer client packets out WAN.
        Refuses to touch primary host interface.
        """
        # Guard against touching actively connected host Wi-Fi connections
        active_wifi = self.get_active_wifi_devices()
        if interface in active_wifi:
            conn = active_wifi[interface]
            raise ValueError(
                f"Interface '{interface}' is actively connected to '{conn}'. "
                "Cannot use an active host Wi-Fi connection as hotspot relay to protect network integrity."
            )

        # Check if already running on same interface and parameters
        if self._status.active and self._status.interface == interface:
            if self._status.ssid == ssid and self._status.wan_iface == wan_iface:
                logger.info("Hotspot relay already active on %s with SSID '%s'", interface, ssid)
                return self.get_status().as_dict()

        # If already running on another interface or config, stop first
        if self._status.active:
            self.stop_relay()

        logger.info(
            "Starting Hotspot Relay: iface=%s, ssid='%s', band=%s, ch=%d, wan=%s",
            interface, ssid, band, channel, wan_iface,
        )

        # 1. Clean up any existing mislty-relay connection in NetworkManager
        self._cleanup_nm_connection()

        # 2. Build and add NetworkManager AP hotspot connection
        cmd_add = [
            "nmcli", "connection", "add",
            "type", "wifi",
            "ifname", interface,
            "con-name", self.CON_NAME,
            "autoconnect", "no",
            "ssid", ssid,
            "mode", "ap",
            "802-11-wireless.band", band,
            "802-11-wireless.channel", str(channel),
            "ipv4.method", "shared",
        ]

        if password and len(password) >= 8:
            cmd_add.extend([
                "wifi-sec.key-mgmt", "wpa-psk",
                "wifi-sec.psk", password,
            ])

        res_add = subprocess.run(cmd_add, capture_output=True, text=True, timeout=10.0)
        if res_add.returncode != 0:
            err = res_add.stderr.strip() or res_add.stdout.strip()
            raise RuntimeError(f"Failed to create NetworkManager hotspot connection: {err}")

        # 3. Bring up the hotspot connection
        try:
            res_up = subprocess.run(
                ["nmcli", "connection", "up", self.CON_NAME],
                capture_output=True,
                text=True,
                timeout=12.0,
            )
            if res_up.returncode != 0:
                err = res_up.stderr.strip() or res_up.stdout.strip()
                self._cleanup_nm_connection()
                raise RuntimeError(f"Failed to activate hotspot on {interface}: {err}")
        except subprocess.TimeoutExpired:
            self._cleanup_nm_connection()
            hint = " (Note: 5 GHz softAP often fails due to regulatory 'no-IR' rules; try 2.4 GHz Ch 11 or 6)" if band == "a" else ""
            raise RuntimeError(f"Hotspot activation timed out on {interface}{hint}.")
        except Exception:
            self._cleanup_nm_connection()
            raise

        # 4. Wait briefly and resolve assigned local IP
        ip_addr = self._resolve_interface_ip(interface)

        # 5. Enable IP forwarding, iptables MASQUERADE, and table 420 policy routing
        nat_ok = False
        try:
            nat_ok = self.helper.enable_nat(wan_iface, interface)
        except Exception as exc:
            logger.warning("Helper enable_nat call encountered: %s", exc)

        # 6. Update internal status
        self._status = RelayStatus(
            active=True,
            interface=interface,
            ssid=ssid,
            password=password,
            channel=channel,
            band=band,
            ip_address=ip_addr,
            wan_iface=wan_iface,
            start_time=time.time(),
            client_count=0,
            uptime_seconds=0,
        )

        logger.info(
            "Hotspot relay successfully activated on %s (IP: %s) -> WAN: %s",
            interface, ip_addr, wan_iface,
        )
        return self.get_status().as_dict()

    def stop_relay(self) -> Dict[str, Any]:
        """
        Deactivate assist hotspot softAP, remove table 420 policy routing,
        and teardown NAT forwarding rules cleanly.
        """
        if not self._status.active:
            # Still perform connection cleanup just in case
            self._cleanup_nm_connection()
            return self._status.as_dict()

        iface = self._status.interface or "wlan1"
        wan = self._status.wan_iface or "ppp0"

        logger.info("Stopping Hotspot Relay on %s (WAN: %s)", iface, wan)

        # 1. Bring down NetworkManager connection
        try:
            subprocess.run(
                ["nmcli", "connection", "down", self.CON_NAME],
                capture_output=True,
                text=True,
                timeout=8.0,
            )
        except Exception as exc:
            logger.debug("nmcli con down failed: %s", exc)

        # 2. Delete the connection profile
        self._cleanup_nm_connection()

        # 3. Disable NAT and policy routing via privileged helper
        try:
            self.helper.disable_nat(wan, iface)
        except Exception as exc:
            logger.debug("Helper disable_nat failed: %s", exc)

        # 4. Reset status
        self._status = RelayStatus(active=False)
        logger.info("Hotspot relay stopped successfully.")
        return self._status.as_dict()

    def get_status(self) -> RelayStatus:
        """Query live telemetry status of the assist hotspot relay."""
        if self._status.active:
            # Refresh client count
            clients = self.get_connected_clients()
            self._status.client_count = len(clients)
            if self._status.start_time > 0:
                self._status.uptime_seconds = int(time.time() - self._status.start_time)

        return self._status

    def get_connected_clients(self) -> List[RelayClient]:
        """
        Discover client devices connected to the assist softAP.
        Extracts MAC address, signal strength, and transfer metrics from iw station dump,
        and correlates with ARP table to resolve assigned client IP addresses.
        """
        if not self._status.active or not self._status.interface:
            return []

        iface = self._status.interface
        clients: List[RelayClient] = []
        arp_map = self._get_arp_table(iface)

        # 1. Query stations via iw dev <iface> station dump (if driver supports it)
        try:
            res = subprocess.run(
                ["iw", "dev", iface, "station", "dump"],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if res.returncode == 0 and res.stdout.strip():
                current_mac: Optional[str] = None
                current_signal: Optional[int] = None
                rx_b = 0
                tx_b = 0
                inact = 0

                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("Station "):
                        if current_mac:
                            clients.append(RelayClient(
                                mac=current_mac,
                                ip=arp_map.get(current_mac.lower()),
                                signal_dbm=current_signal,
                                rx_bytes=rx_b,
                                tx_bytes=tx_b,
                                inactive_ms=inact,
                            ))
                        parts = line.split()
                        current_mac = parts[1] if len(parts) >= 2 else None
                        current_signal = None
                        rx_b, tx_b, inact = 0, 0, 0
                    elif line.startswith("signal:"):
                        # Format: signal: -42 dBm
                        sig_parts = line.split(":")[-1].replace("dBm", "").strip().split()
                        if sig_parts and sig_parts[0].lstrip("-").isdigit():
                            current_signal = int(sig_parts[0])
                    elif line.startswith("rx bytes:"):
                        val = line.split(":")[-1].strip()
                        if val.isdigit():
                            rx_b = int(val)
                    elif line.startswith("tx bytes:"):
                        val = line.split(":")[-1].strip()
                        if val.isdigit():
                            tx_b = int(val)
                    elif line.startswith("inactive time:"):
                        val = line.split(":")[-1].replace("ms", "").strip()
                        if val.isdigit():
                            inact = int(val)

                if current_mac:
                    clients.append(RelayClient(
                        mac=current_mac,
                        ip=arp_map.get(current_mac.lower()),
                        signal_dbm=current_signal,
                        rx_bytes=rx_b,
                        tx_bytes=tx_b,
                        inactive_ms=inact,
                    ))

        except Exception as exc:
            logger.debug("Failed to query stations on %s: %s", iface, exc)

        # 2. Correlate with ARP / Neighbor table for any active clients not returned by iw
        seen_macs = {c.mac.lower() for c in clients}
        for mac, ip in arp_map.items():
            if mac.lower() not in seen_macs:
                clients.append(RelayClient(
                    mac=mac,
                    ip=ip,
                    signal_dbm=None,
                    rx_bytes=0,
                    tx_bytes=0,
                    inactive_ms=0,
                ))

        return clients

    def _get_arp_table(self, iface: str) -> Dict[str, str]:
        """Parse /proc/net/arp and ip neigh to map MAC addresses to IP addresses for given interface."""
        arp_map: Dict[str, str] = {}
        # 1. Parse /proc/net/arp
        try:
            arp_path = Path("/proc/net/arp")
            if arp_path.is_file():
                lines = arp_path.read_text(encoding="utf-8").splitlines()
                for line in lines[1:]:  # skip header
                    parts = line.split()
                    if len(parts) >= 6 and parts[5] == iface:
                        ip = parts[0]
                        mac = parts[3].lower()
                        if mac != "00:00:00:00:00:00":
                            arp_map[mac] = ip
        except Exception as exc:
            logger.debug("Failed to read /proc/net/arp: %s", exc)

        # 2. Augment with ip neigh show dev <iface>
        try:
            res = subprocess.run(
                ["ip", "neigh", "show", "dev", iface],
                capture_output=True,
                text=True,
                timeout=2.0,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 4 and "lladdr" in parts:
                        idx = parts.index("lladdr")
                        if idx + 1 < len(parts):
                            ip = parts[0]
                            mac = parts[idx + 1].lower()
                            if mac != "00:00:00:00:00:00":
                                arp_map[mac] = ip
        except Exception as exc:
            logger.debug("Failed to query ip neigh: %s", exc)

        return arp_map

    def _resolve_interface_ip(self, iface: str) -> Optional[str]:
        """Query assigned IPv4 address for interface."""
        try:
            res = subprocess.run(
                ["ip", "-4", "addr", "show", "dev", iface],
                capture_output=True,
                text=True,
                timeout=3.0,
            )
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    line = line.strip()
                    if line.startswith("inet "):
                        # Format: inet 10.42.0.1/24 scope global ...
                        return line.split()[1].split("/")[0]
        except Exception as exc:
            logger.debug("Failed to query IP on %s: %s", iface, exc)

        return "10.42.0.1"

    def _is_interface_active(self, iface: str) -> bool:
        """Check if interface is currently reported active/connected by nmcli or sysfs."""
        try:
            oper_path = Path(f"/sys/class/net/{iface}/operstate")
            if oper_path.is_file():
                state = oper_path.read_text(encoding="utf-8").strip()
                return state in ("up", "dormant", "unknown")
        except Exception:
            pass
        return True

    def _cleanup_nm_connection(self) -> None:
        """Remove any pre-existing mislty-relay connection from NetworkManager."""
        try:
            subprocess.run(
                ["nmcli", "connection", "delete", self.CON_NAME],
                capture_output=True,
                text=True,
                timeout=5.0,
            )
        except Exception:
            pass
