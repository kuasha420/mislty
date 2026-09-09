"""
mislty.net.qcwebs_client
~~~~~~~~~~~~~~~~~~~~~~~~

Reverse-engineered embedded QC-Webs GoForm HTTP Client and Smart Mode Switcher
for the Qualcomm MDM9600 / Aleka UV310.
Connects directly to the onboard GoAhead WebServer at 192.168.100.1 via local
WLAN or netns-isolated auxiliary interface (wlan1).
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

logger = logging.getLogger("mislty.net.qcwebs")


class QcWebsClient:
    """
    HTTP client for the embedded GoAhead/QC-Webs API on the modem.
    Provides un-suffixed SSID configuration, station scraping, real-time
    GoForm telemetry, and AP security configuration.
    """

    def __init__(
        self,
        host: str = "192.168.100.1",
        netns: Optional[str] = None,
        timeout: float = 3.0,
    ) -> None:
        self.host = host
        self.netns = netns
        self.timeout = timeout
        self.session_cookie: Optional[str] = None

    def _request(
        self,
        path: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> tuple[int, str]:
        """
        Dispatch HTTP request either directly or through the designated network namespace.
        """
        clean_path = path.lstrip("/")
        url = f"http://{self.host}/{clean_path}"
        post_data = urllib.parse.urlencode(data).encode("utf-8") if data is not None else None

        req_headers = {"User-Agent": "MisLTy-Desktop/1.0 (Linux; x86_64)"}
        if headers:
            req_headers.update(headers)
        if self.session_cookie:
            req_headers["Cookie"] = self.session_cookie

        if self.netns:
            # Route via ip netns exec <netns> curl
            cmd = ["sudo", "-n", "ip", "netns", "exec", self.netns, "curl", "-s", "-w", "\n%{http_code}"]
            cmd.extend(["--connect-timeout", str(int(self.timeout))])
            cmd.extend(["-m", str(int(self.timeout) + 2)])

            for k, v in req_headers.items():
                cmd.extend(["-H", f"{k}: {v}"])

            if method == "POST" and data is not None:
                cmd.extend(["-X", "POST", "--data", urllib.parse.urlencode(data)])
            elif method != "GET":
                cmd.extend(["-X", method])

            cmd.append(url)

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout + 3.0)
                if res.returncode != 0:
                    logger.debug("netns curl error: %s", res.stderr)
                    return 0, ""

                lines = res.stdout.rsplit("\n", 1)
                body = lines[0] if len(lines) > 1 else ""
                code_str = lines[-1].strip() if len(lines) > 1 else "0"
                status_code = int(code_str) if code_str.isdigit() else 0
                return status_code, body
            except Exception as exc:
                logger.debug("netns curl execution failed: %s", exc)
                return 0, ""

        # Direct HTTP socket
        req = urllib.request.Request(
            url,
            data=post_data,
            headers=req_headers,
            method=method,
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                # Capture set-cookie if present
                cookie_hdr = resp.headers.get("Set-Cookie")
                if cookie_hdr:
                    self.session_cookie = cookie_hdr.split(";")[0]
                return status, body
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode("utf-8", errors="replace")
        except Exception as exc:
            logger.debug("Direct HTTP request failed: %s", exc)
            return 0, ""

    def login(self, username: str = "admin", password: str = "admin") -> bool:
        """
        Authenticate against QC-Webs with LOGIN_NEW form action.
        """
        lucknum = int(time.time() * 1000)
        data = {
            "goformId": "LOGIN_NEW",
            "user": username,
            "psw": password,
            "lucknum": str(lucknum),
            "systemDate": str(lucknum),
            "save_login": "1",
        }
        status, body = self._request("/goform/goform_process", method="POST", data=data)
        if status in (200, 302) and ("location.replace" in body or "index.asp" in body or status == 302):
            self.session_cookie = f"lucknum={lucknum}"
            return True
        return False

    def get_realtime_statistics(self) -> Optional[Dict[str, Any]]:
        """
        Fetch and unpack live telemetry from /json/refresh_data.asp.
        Returns parsed rate and session data counters.
        """
        status, body = self._request("/json/refresh_data.asp", method="GET")
        if status != 200 or not body.strip():
            return None

        try:
            import json
            raw = json.loads(body)
        except Exception:
            # Fallback regex for non-standard JSON quotes
            match_stats = re.search(r'"realtime_statistics"\s*:\s*"([^"]+)"', body)
            match_net = re.search(r'"network_type"\s*:\s*"([^"]+)"', body)
            match_ppp = re.search(r'"ppp_status"\s*:\s*"([^"]+)"', body)
            raw = {
                "network_type": match_net.group(1) if match_net else "UNKNOWN",
                "realtime_statistics": match_stats.group(1) if match_stats else "",
                "ppp_status": match_ppp.group(1) if match_ppp else "unknown",
            }

        stat_str = raw.get("realtime_statistics", "")
        parts = stat_str.split(",") if stat_str else []

        def _to_int(val_str: str) -> int:
            try:
                return int(val_str.strip())
            except (ValueError, IndexError):
                return 0

        return {
            "network_type": raw.get("network_type", "LTE"),
            "ppp_status": raw.get("ppp_status", "unknown"),
            "cardstate": raw.get("cardstate", "unknown"),
            "roam": raw.get("roam", "roam_off"),
            "speed_up": _to_int(parts[0]) if len(parts) > 0 else 0,
            "speed_down": _to_int(parts[1]) if len(parts) > 1 else 0,
            "current_tx_bytes": _to_int(parts[2]) if len(parts) > 2 else 0,
            "current_rx_bytes": _to_int(parts[3]) if len(parts) > 3 else 0,
            "session_duration": _to_int(parts[4]) if len(parts) > 4 else 0,
            "total_tx_bytes": _to_int(parts[5]) if len(parts) > 5 else 0,
            "total_rx_bytes": _to_int(parts[6]) if len(parts) > 6 else 0,
            "total_uptime": _to_int(parts[7]) if len(parts) > 7 else 0,
        }

    def get_station_list(self) -> List[Dict[str, Any]]:
        """
        Scrape connected client devices from /station_list.asp.
        Returns array of records with station index and MAC address.
        """
        status, body = self._request("/station_list.asp", method="GET")
        if status != 200 or not body:
            return []

        stations: List[Dict[str, Any]] = []
        # Look for table rows: <tr><td ... class="head">1</td><td ... class="tail">D2:6F:5B:13:A8:B5</td></tr>
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", body, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
            if len(cells) >= 2:
                idx_str = re.sub(r"<[^>]+>", "", cells[0]).strip()
                mac_str = re.sub(r"<[^>]+>", "", cells[1]).strip()
                if re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac_str):
                    stations.append({
                        "index": int(idx_str) if idx_str.isdigit() else len(stations) + 1,
                        "mac": mac_str.upper(),
                        "hostname": f"Station {idx_str}" if idx_str.isdigit() else "Wireless Client",
                    })

        return stations

    def set_wifi_basic(
        self,
        ssid: str,
        broadcast: bool = True,
        mode: int = 0,
        channel: int = 11,
        max_stas: int = 8,
    ) -> bool:
        """
        Configure broadcast SSID cleanly without manufacturer BSSID suffix.
        """
        data = {
            "goformId": "WIFI_BASIC",
            "ssid": ssid,
            "broadcastssid": "1" if broadcast else "0",
            "wirelessmode": str(mode),
            "channel": str(channel),
            "Allow_MAX_STAs": str(max_stas),
        }
        status, body = self._request("/goform/goform_process", method="POST", data=data)
        return status in (200, 302)

    def set_wifi_security(
        self,
        passphrase: str,
        mode: str = "NONE",
        cipher: int = 2,
    ) -> bool:
        """
        Configure WPA2-PSK passphrase and AES cipher.
        """
        data = {
            "goformId": "WIFI_SECURITY",
            "security_shared_mode": mode,
            "cipher": str(cipher),
            "passphrase": passphrase,
        }
        status, body = self._request("/goform/goform_process", method="POST", data=data)
        return status in (200, 302)

    def set_wifi_sleep(self, enabled: bool = False, sleep_time: int = -1) -> bool:
        """
        Configure radio power-saving sleep timer (-1 for Always On).
        """
        data = {
            "goformId": "WIFI_SLEEP",
            "sleep_mode": "1" if enabled else "0",
            "sleep_time": str(sleep_time),
        }
        status, body = self._request("/goform/goform_process", method="POST", data=data)
        return status in (200, 302)

    def set_wan_connect(self, connect: bool = True) -> bool:
        """
        Initiate or terminate cellular WAN routing in Pocket Router mode.
        """
        data = {
            "goformId": "NET_CONNECT",
            "dial_mode": "auto_dial",
            "action": "connect" if connect else "disconnect",
            "wan_conn_which_page": "wan_operation",
        }
        status, body = self._request("/goform/goform_process", method="POST", data=data)
        return status in (200, 302)

    def device_reboot(self) -> bool:
        """Trigger device restart via GoForm reboot action."""
        status, _ = self._request("/goform/goform_process?goformId=device_reboot", method="GET")
        return status in (200, 302)


class SmartModeSwitcher:
    """
    Orchestrates rapid transitions between USB Cellular Modem (ppp0 host mode)
    and Standalone Pocket Router mode (firmware softAP WAN routing).
    """

    MODE_USB = "usb_modem"
    MODE_ROUTER = "pocket_router"

    def __init__(
        self,
        qcwebs_client: Optional[QcWebsClient] = None,
        ppp_controller: Optional[Any] = None,
        dispatcher: Optional[Any] = None,
    ) -> None:
        self.qcwebs = qcwebs_client if qcwebs_client is not None else QcWebsClient()
        self.ppp = ppp_controller
        self.dispatcher = dispatcher
        self._current_mode = self.MODE_USB

    @property
    def current_mode(self) -> str:
        return self._current_mode

    def switch_to_router_mode(self) -> Dict[str, Any]:
        """
        Handover cellular data routing to the onboard Pocket Router softAP.
        Tear down host ppp0 and engage firmware WAN auto-dial.
        """
        t0 = time.time()
        logger.info("Switching operational mode to Pocket Router (softAP WAN)...")

        # 1. Disconnect host PPP data plane if active
        if self.ppp:
            try:
                self.ppp.disconnect()
            except Exception as exc:
                logger.debug("PPP disconnect error during mode switch: %s", exc)

        # 2. Ensure Wi-Fi radio is powered on
        if self.dispatcher:
            try:
                self.dispatcher.execute("AT+WIFI=1", timeout=2.0)
                self.dispatcher.execute("AT+WRWIFI", timeout=2.0)
            except Exception:
                pass

        # 3. Trigger firmware WAN connection via QC-Webs
        ok = self.qcwebs.set_wan_connect(connect=True)
        elapsed = round(time.time() - t0, 3)
        self._current_mode = self.MODE_ROUTER

        return {
            "success": ok,
            "mode": self.MODE_ROUTER,
            "elapsed_seconds": elapsed,
            "message": f"Switched to Pocket Router mode in {elapsed}s",
        }

    def switch_to_usb_mode(self, apn: str = "internet") -> Dict[str, Any]:
        """
        Reclaim cellular data routing directly to the Linux host via ppp0.
        Disconnects firmware softAP WAN and dials ppp0.
        """
        t0 = time.time()
        logger.info("Switching operational mode to USB Cellular Modem (ppp0)...")

        # 1. Disconnect softAP WAN via QC-Webs
        try:
            self.qcwebs.set_wan_connect(connect=False)
        except Exception:
            pass

        # 2. Re-establish host PPP connection
        ppp_ok = True
        if self.ppp:
            try:
                ppp_ok = self.ppp.connect(apn=apn, default_route=True, timeout=15.0)
            except Exception as exc:
                logger.error("Failed to establish USB PPP connection: %s", exc)
                ppp_ok = False

        elapsed = round(time.time() - t0, 3)
        self._current_mode = self.MODE_USB

        return {
            "success": ppp_ok,
            "mode": self.MODE_USB,
            "elapsed_seconds": elapsed,
            "message": f"Switched to USB Cellular Modem mode in {elapsed}s",
        }
