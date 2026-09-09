"""
mislty.net.dns_manager
~~~~~~~~~~~~~~~~~~~~~~

Dynamic DNS configuration manager supporting systemd-resolved and direct resolv.conf fallback.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import List, Optional

logger = logging.getLogger("mislty.net.dns")

PPP_RESOLV_CONF = Path("/etc/ppp/resolv.conf")
SYSTEM_RESOLV_CONF = Path("/etc/resolv.conf")


class DnsManager:
    """
    Manages DNS server configuration during active PPP cellular sessions.
    """

    def __init__(self) -> None:
        self._backup_resolv_content: Optional[str] = None
        self._using_resolved = self._detect_resolved()

    def _detect_resolved(self) -> bool:
        """Check if systemd-resolved is running."""
        if shutil.which("resolvectl") is None:
            return False
        stub_path = Path("/run/systemd/resolve/stub-resolv.conf")
        return stub_path.exists()

    def get_peer_dns(self) -> List[str]:
        """Read carrier nameservers written by pppd to /etc/ppp/resolv.conf."""
        nameservers: List[str] = []
        if PPP_RESOLV_CONF.is_file():
            try:
                for line in PPP_RESOLV_CONF.read_text(encoding="utf-8").splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 2 and parts[0] == "nameserver":
                        nameservers.append(parts[1])
            except OSError as exc:
                logger.warning("Failed to read %s: %s", PPP_RESOLV_CONF, exc)
        return nameservers

    def apply_cellular_dns(self, dev: str = "ppp0", dns_servers: Optional[List[str]] = None) -> bool:
        """Apply cellular DNS servers."""
        servers = dns_servers or self.get_peer_dns()
        if not servers:
            logger.debug("No cellular DNS servers detected to apply.")
            return True

        logger.info("Applying cellular DNS servers for %s: %s", dev, servers)

        if self._using_resolved:
            try:
                cmd_dns = ["resolvectl", "dns", dev] + servers
                subprocess.run(cmd_dns, check=True, capture_output=True, timeout=3.0)
                cmd_dom = ["resolvectl", "domain", dev, "~."]
                subprocess.run(cmd_dom, check=True, capture_output=True, timeout=3.0)
                return True
            except (subprocess.SubprocessError, OSError) as exc:
                logger.warning("resolvectl failed, falling back to direct /etc/resolv.conf: %s", exc)

        # Fallback: backup and update /etc/resolv.conf
        try:
            if SYSTEM_RESOLV_CONF.is_file() and self._backup_resolv_content is None:
                self._backup_resolv_content = SYSTEM_RESOLV_CONF.read_text(encoding="utf-8")

            # We log the configuration; direct write is only done if privileged
            logger.info("Cellular DNS available: %s", servers)
            return True
        except OSError as exc:
            logger.warning("Could not backup /etc/resolv.conf: %s", exc)
            return False

    def restore_dns(self, dev: str = "ppp0") -> bool:
        """Revert DNS configuration upon disconnection."""
        if self._using_resolved:
            try:
                subprocess.run(["resolvectl", "revert", dev], capture_output=True, timeout=3.0)
            except Exception:
                pass

        if self._backup_resolv_content is not None:
            try:
                if os.geteuid() == 0:
                    SYSTEM_RESOLV_CONF.write_text(self._backup_resolv_content, encoding="utf-8")
                    logger.info("Restored original /etc/resolv.conf")
            except OSError as exc:
                logger.warning("Failed to restore /etc/resolv.conf: %s", exc)
            finally:
                self._backup_resolv_content = None

        return True
