"""
mislty.net.ppp_controller
~~~~~~~~~~~~~~~~~~~~~~~~~

Cellular data plane supervisor managing pppd over MI_00 (/dev/mislty/data),
IP allocation monitoring, route metric coordination, and clean teardown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Dict, List, Optional

from mislty.core.port_resolver import PortResolver
from mislty.net.dns_manager import DnsManager
from mislty.net.helper_client import NetworkHelperClient
from mislty.net.route_manager import RouteManager

logger = logging.getLogger("mislty.net.ppp")


@dataclass
class PppStatus:
    """Status snapshot of cellular PPP connection."""
    connected: bool = False
    interface: str = "ppp0"
    ip_address: Optional[str] = None
    peer_ip: Optional[str] = None
    dns_servers: List[str] = field(default_factory=list)
    rx_bytes: int = 0
    tx_bytes: int = 0
    connected_at: Optional[float] = None

    @property
    def uptime_seconds(self) -> float:
        """Uptime of connection in seconds."""
        if not self.connected or not self.connected_at:
            return 0.0
        return max(0.0, time.time() - self.connected_at)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "connected": self.connected,
            "interface": self.interface,
            "ip_address": self.ip_address,
            "peer_ip": self.peer_ip,
            "dns_servers": self.dns_servers,
            "rx_bytes": self.rx_bytes,
            "tx_bytes": self.tx_bytes,
            "uptime_seconds": round(self.uptime_seconds, 1),
        }

    def __str__(self) -> str:
        if not self.connected:
            return "PPP Status: Disconnected"
        dns_str = ", ".join(self.dns_servers) if self.dns_servers else "None"
        return (
            f"PPP Status: Connected ({self.interface})\n"
            f"  • Local IP     : {self.ip_address or 'Unknown'}\n"
            f"  • Peer IP      : {self.peer_ip or 'Unknown'}\n"
            f"  • DNS Servers  : {dns_str}\n"
            f"  • Bandwidth    : RX {self.rx_bytes / 1024:.1f} KB | TX {self.tx_bytes / 1024:.1f} KB\n"
            f"  • Uptime       : {self.uptime_seconds:.0f}s"
        )


class PppController:
    """
    Manager for the cellular PPP data plane.
    """

    def __init__(
        self,
        data_port: Optional[Path] = None,
        helper: Optional[NetworkHelperClient] = None,
        route_mgr: Optional[RouteManager] = None,
        dns_mgr: Optional[DnsManager] = None,
    ) -> None:
        self.data_port = data_port
        self.helper = helper or NetworkHelperClient()
        self.route_mgr = route_mgr or RouteManager(self.helper)
        self.dns_mgr = dns_mgr or DnsManager()
        self._connected_at: Optional[float] = None

    def _resolve_data_port(self) -> Path:
        """Resolve physical data port (MI_00)."""
        if self.data_port and self.data_port.exists():
            return self.data_port

        ports = PortResolver().resolve()
        if ports.data and ports.data.exists():
            return ports.data
        raise RuntimeError("No cellular data port (MI_00) detected on system.")

    def connect(
        self,
        apn: str = "internet",
        default_route: bool = True,
        timeout: float = 20.0,
    ) -> bool:
        """
        Initiate dial-up cellular PPP data connection.
        """
        status = self.get_status()
        if status.connected:
            logger.info("Cellular PPP connection is already active on %s", status.interface)
            return True

        port = self._resolve_data_port()
        logger.info("Dialing cellular network via %s (APN: %s)...", port, apn)

        # 1. Snapshot existing routing table
        self.route_mgr.snapshot()

        # 2. Launch pppd daemon via privileged helper
        res = self.helper.start_ppp(str(port), apn=apn)
        if not res.get("success"):
            logger.error("Failed to launch pppd: %s", res)
            return False

        # 3. Wait for ppp0 interface and IP address assignment
        deadline = time.time() + timeout
        allocated_ip: Optional[str] = None

        while time.time() < deadline:
            time.sleep(0.5)
            stat = self.get_status()
            if stat.connected and stat.ip_address:
                allocated_ip = stat.ip_address
                break

        if not allocated_ip:
            logger.error("Timed out waiting for ppp0 IP address assignment.")
            self.disconnect()
            return False

        self._connected_at = time.time()
        logger.info("Cellular link established: IP %s", allocated_ip)

        # 4. Route management
        if default_route:
            self.route_mgr.set_cellular_default("ppp0", metric=50)

        # 5. DNS configuration
        self.dns_mgr.apply_cellular_dns("ppp0")

        return True

    def disconnect(self) -> bool:
        """
        Terminate active cellular PPP data connection and restore routes and DNS.
        """
        logger.info("Disconnecting cellular PPP session...")
        self.helper.stop_ppp()
        self._connected_at = None

        # Restore DNS and routes
        self.dns_mgr.restore_dns("ppp0")
        self.route_mgr.restore_routes()

        # Wait up to 3s for interface to disappear
        for _ in range(6):
            if not Path("/sys/class/net/ppp0").exists():
                break
            time.sleep(0.5)

        logger.info("Cellular PPP session terminated and routes restored.")
        return True

    def get_status(self) -> PppStatus:
        """Query live ppp0 interface state."""
        sysfs_net = Path("/sys/class/net/ppp0")
        if not sysfs_net.exists():
            return PppStatus(connected=False)

        rx_bytes = 0
        tx_bytes = 0
        try:
            rx_bytes = int((sysfs_net / "statistics" / "rx_bytes").read_text().strip())
            tx_bytes = int((sysfs_net / "statistics" / "tx_bytes").read_text().strip())
        except (OSError, ValueError):
            pass

        # Query IP address via ip -o -4 addr show ppp0
        ip_addr: Optional[str] = None
        peer_ip: Optional[str] = None
        try:
            res = subprocess.run(
                ["ip", "-o", "-4", "addr", "show", "ppp0"],
                capture_output=True,
                text=True,
                timeout=1.0,
            )
            if res.returncode == 0 and res.stdout.strip():
                # Format: 4: ppp0 inet 10.x.x.x peer 10.x.x.y/32 scope global ppp0
                m = re.search(r"inet\s+([0-9.]+)\s+peer\s+([0-9.]+)", res.stdout)
                if m:
                    ip_addr = m.group(1)
                    peer_ip = m.group(2)
                else:
                    m2 = re.search(r"inet\s+([0-9.]+)", res.stdout)
                    if m2:
                        ip_addr = m2.group(1)
        except (OSError, subprocess.SubprocessError):
            pass

        dns_servers = self.dns_mgr.get_peer_dns()

        return PppStatus(
            connected=bool(ip_addr),
            interface="ppp0",
            ip_address=ip_addr,
            peer_ip=peer_ip,
            dns_servers=dns_servers,
            rx_bytes=rx_bytes,
            tx_bytes=tx_bytes,
            connected_at=self._connected_at,
        )
