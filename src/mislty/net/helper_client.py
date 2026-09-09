"""
mislty.net.helper_client
~~~~~~~~~~~~~~~~~~~~~~~~

Python client interface for the privileged network helper.
Automatically executes commands via Polkit (pkexec) or direct root permissions.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union


logger = logging.getLogger("mislty.net.client")


class HelperClientError(Exception):
    """Base exception for network helper client errors."""
    pass


class HelperAuthError(HelperClientError):
    """Raised when Polkit authorization fails or permission is denied."""
    pass


class NetworkHelperClient:
    """
    Client for executing privileged network operations via Polkit or root.
    """

    CANDIDATE_PATHS = [
        Path("/usr/libexec/mislty-net-helper"),
        Path("/usr/local/bin/mislty-net-helper"),
        Path(__file__).resolve().parent.parent.parent.parent / "bin" / "mislty-net-helper",
    ]

    def __init__(self, helper_path: Optional[Union[str, Path]] = None) -> None:
        if helper_path:
            self.helper_path = Path(helper_path)
        else:
            self.helper_path = self._discover_helper_path()

    def _discover_helper_path(self) -> Path:
        """Locate the network helper binary on the filesystem."""
        for candidate in self.CANDIDATE_PATHS:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return candidate

        # Fallback to shutil.which
        which_path = shutil.which("mislty-net-helper")
        if which_path:
            return Path(which_path)

        return self.CANDIDATE_PATHS[0]

    @property
    def is_root(self) -> bool:
        """True if the current process is already running as root."""
        return os.geteuid() == 0

    @property
    def is_polkit_available(self) -> bool:
        """True if pkexec binary is available on system PATH."""
        return shutil.which("pkexec") is not None

    def run_action(self, action: str, *args: str, timeout: float = 10.0) -> Dict[str, Any]:
        """
        Execute an action on the privileged helper.
        Uses pkexec when non-root.
        """
        if not self.helper_path.exists():
            raise HelperClientError(f"Network helper binary not found at {self.helper_path}")

        cmd: List[str] = []
        if self.is_root:
            cmd = [str(self.helper_path), action, *args]
        elif self.is_polkit_available:
            cmd = ["pkexec", str(self.helper_path), action, *args]
        else:
            # Fallback to sudo -n if available
            cmd = ["sudo", "-n", str(self.helper_path), action, *args]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except OSError as exc:
            raise HelperClientError(f"Failed to launch privileged helper: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise HelperClientError(f"Privileged helper timed out after {timeout}s") from exc

        if res.returncode == 126 or res.returncode == 127:
            # pkexec authorization dismissed or denied
            raise HelperAuthError(f"Polkit authentication dismissed or denied: {res.stderr.strip()}")

        if res.returncode != 0:
            err_msg = res.stderr.strip() or f"Process exited with code {res.returncode}"
            try:
                err_data = json.loads(res.stderr.strip())
                err_msg = err_data.get("message", err_msg)
            except (json.JSONDecodeError, ValueError):
                pass
            raise HelperClientError(f"Helper action '{action}' failed: {err_msg}")

        try:
            return json.loads(res.stdout.strip())
        except (json.JSONDecodeError, ValueError) as exc:
            raise HelperClientError(f"Invalid JSON returned by helper: {res.stdout.strip()}") from exc

    def check_auth(self) -> bool:
        """Verify that caller has permission to run privileged operations."""
        try:
            data = self.run_action("check-auth")
            return data.get("status") == "authorized"
        except (HelperClientError, HelperAuthError):
            return False

    def set_default_route(self, dev: str, metric: int = 50) -> bool:
        """Set default gateway route on dev with specified metric."""
        res = self.run_action("set-default-route", dev, "--metric", str(metric))
        return bool(res.get("success"))

    def restore_default_route(self, gw: str, dev: str, metric: int = 600) -> bool:
        """Restore default gateway route via gw on dev."""
        res = self.run_action("restore-default-route", gw, dev, "--metric", str(metric))
        return bool(res.get("success"))

    def enable_nat(self, wan_iface: str, lan_iface: str) -> bool:
        """Enable IPv4 forwarding and NAT masquerade."""
        res = self.run_action("enable-nat", wan_iface, lan_iface)
        return bool(res.get("success"))

    def disable_nat(self, wan_iface: str, lan_iface: str) -> bool:
        """Disable IPv4 forwarding and NAT masquerade."""
        res = self.run_action("disable-nat", wan_iface, lan_iface)
        return bool(res.get("success"))

    def start_ppp(self, dev: str, apn: str = "internet") -> Dict[str, Any]:
        """Launch pppd daemon on dev with carrier APN."""
        return self.run_action("start-ppp", dev, "--apn", apn)

    def stop_ppp(self) -> bool:
        """Terminate active pppd processes."""
        res = self.run_action("stop-ppp")
        return bool(res.get("success"))

