"""
mislty.net.route_manager
~~~~~~~~~~~~~~~~~~~~~~~~

Non-destructive routing table manager.
Captures snapshots of pre-connection default routes and manages metric-based
preemption and atomic restoration on disconnection.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional

from mislty.net.helper_client import NetworkHelperClient

logger = logging.getLogger("mislty.net.route")


@dataclass
class RouteEntry:
    """Represents a default gateway route entry."""
    gateway: Optional[str] = None
    dev: str = ""
    metric: int = 600
    proto: Optional[str] = None
    src: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "gateway": self.gateway,
            "dev": self.dev,
            "metric": self.metric,
            "proto": self.proto,
            "src": self.src,
        }


class RouteManager:
    """
    Manages non-destructive default route switching for MisLTy.
    """

    def __init__(self, helper: Optional[NetworkHelperClient] = None) -> None:
        self.helper = helper or NetworkHelperClient()
        self._saved_default_routes: List[RouteEntry] = []

    def get_default_routes(self) -> List[RouteEntry]:
        """Query currently active default routes from kernel."""
        entries: List[RouteEntry] = []
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
                    if not parts or parts[0] != "default":
                        continue

                    gw = parts[parts.index("via") + 1] if "via" in parts else None
                    dev = parts[parts.index("dev") + 1] if "dev" in parts else ""
                    metric = int(parts[parts.index("metric") + 1]) if "metric" in parts else 0
                    proto = parts[parts.index("proto") + 1] if "proto" in parts else None
                    src = parts[parts.index("src") + 1] if "src" in parts else None

                    entries.append(RouteEntry(gateway=gw, dev=dev, metric=metric, proto=proto, src=src))
        except (OSError, subprocess.SubprocessError) as exc:
            logger.warning("Failed to query default routes: %s", exc)

        return entries

    def snapshot(self) -> None:
        """Capture current default routes before activating cellular link."""
        current_routes = self.get_default_routes()
        # Filter out existing ppp0 routes if any
        non_ppp_routes = [r for r in current_routes if not r.dev.startswith("ppp")]
        if non_ppp_routes:
            self._saved_default_routes = non_ppp_routes
            logger.info("Saved default route snapshot: %s", [r.as_dict() for r in non_ppp_routes])

    def set_cellular_default(self, dev: str = "ppp0", metric: int = 50) -> bool:
        """
        Activate cellular default route with high priority metric (50),
        preempting existing Wi-Fi/Ethernet default route without deleting it.
        """
        if not self._saved_default_routes:
            self.snapshot()

        logger.info("Injecting cellular default route via %s (metric %d)", dev, metric)
        try:
            return self.helper.set_default_route(dev, metric=metric)
        except Exception as exc:
            logger.error("Failed to set cellular default route: %s", exc)
            return False

    def restore_routes(self) -> bool:
        """
        Restore original default routes captured during snapshot.
        """
        if not self._saved_default_routes:
            logger.debug("No saved default routes to restore.")
            return True

        success = True
        for entry in self._saved_default_routes:
            if entry.gateway and entry.dev:
                logger.info("Restoring original route via %s dev %s (metric %d)", entry.gateway, entry.dev, entry.metric)
                try:
                    res = self.helper.restore_default_route(entry.gateway, entry.dev, metric=entry.metric)
                    if not res:
                        success = False
                except Exception as exc:
                    logger.error("Failed to restore route for %s: %s", entry.dev, exc)
                    success = False

        self._saved_default_routes.clear()
        return success
