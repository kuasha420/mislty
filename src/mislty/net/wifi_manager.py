"""
mislty.net.wifi_manager
~~~~~~~~~~~~~~~~~~~~~~~

Broadcom Wi-Fi co-processor supervisor and embedded QC-Webs Web UI integration.
Provides hardware radio switching, NVRAM credential writing, clean un-suffixed
SSID configuration via GoForm API, and DHCP client discovery.
"""

from __future__ import annotations

import logging
import re
import subprocess
from typing import Any, Dict, List, Optional
import urllib.parse
import urllib.request

from mislty.core.at_parser import AtDispatcher

logger = logging.getLogger("mislty.net.wifi")


class WifiManager:
    """
    Supervisor for the Broadcom 802.11n Wi-Fi co-processor.
    """

    def __init__(self, dispatcher: Optional[AtDispatcher] = None) -> None:
        self.dispatcher = dispatcher

    def get_radio_power(self) -> Optional[bool]:
        """Query physical radio power state via AT+WIFI?."""
        if not self.dispatcher:
            return None

        resp = self.dispatcher.execute("AT+WIFI?", timeout=2.0)
        if resp.success and resp.lines:
            # Format: +WIFI: 1 or +WIFI: 0
            for line in resp.lines:
                if "+WIFI:" in line:
                    val = line.split(":")[-1].strip()
                    return val == "1"
        return None

    def set_radio_power(self, enable: bool) -> bool:
        """Toggle physical Wi-Fi radio power on/off and commit to NVRAM."""
        if not self.dispatcher:
            return False

        val = 1 if enable else 0
        resp1 = self.dispatcher.execute(f"AT+WIFI={val}", timeout=3.0)
        resp2 = self.dispatcher.execute("AT+WRWIFI", timeout=3.0)
        return resp1.success and resp2.success

    def get_ssid_serial(self) -> Optional[str]:
        """Query SSID via serial AT^SSID?."""
        if not self.dispatcher:
            return None

        resp = self.dispatcher.execute("AT^SSID?", timeout=2.0)
        if resp.success and resp.lines:
            for line in resp.lines:
                if "^SSID:" in line:
                    match = re.search(r'wl_ssid=([^\r\n]+)', line)
                    if match:
                        return match.group(1).strip()
                    parts = line.split(":")[-1].strip()
                    return parts
        return None

    def set_credentials_serial(self, ssid: str, password: Optional[str] = None) -> bool:
        """
        Configure SSID and WPA2-PSK passphrase via baseband serial commands.
        Note: Factory AT^SSID command appends the 3-character MAC suffix to the SSID.
        For clean un-suffixed SSID, use set_clean_ssid_web().
        """
        if not self.dispatcher:
            return False

        s1 = self.dispatcher.execute(f'AT^SSID="{ssid}"', timeout=3.0)
        s2 = True
        if password:
            s2 = self.dispatcher.execute(f'AT+WIFIWPAPSK="{password}"', timeout=3.0).success
        s3 = self.dispatcher.execute("AT+WRWIFI", timeout=3.0)
        return s1.success and s2 and s3.success

    def set_clean_ssid_web(
        self,
        ssid: str,
        host: str = "192.168.100.1",
        netns: Optional[str] = None,
        timeout: float = 3.0,
    ) -> bool:
        """
        Configure a clean, un-suffixed broadcast SSID directly via the embedded
        QC-Webs GoForm API (POST /goform/goform_process).
        Bypasses factory MAC suffixing and commits to NVRAM.
        """
        url = f"http://{host}/goform/goform_process"
        payload = urllib.parse.urlencode({"goformId": "WIFI_BASIC", "ssid": ssid}).encode("utf-8")

        if netns:
            # Execute curl within target network namespace
            cmd = [
                "sudo", "-n", "ip", "netns", "exec", netns,
                "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
                "-X", "POST", "-d", f"goformId=WIFI_BASIC&ssid={urllib.parse.quote_plus(ssid)}",
                url,
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
                if res.returncode == 0 and res.stdout.strip() in ("200", "302"):
                    if self.dispatcher:
                        self.dispatcher.execute("AT+WRWIFI", timeout=3.0)
                    return True
            except Exception as exc:
                logger.warning("Netns curl to QC-Webs failed: %s", exc)
                return False

        # Direct HTTP request
        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 302):
                    if self.dispatcher:
                        self.dispatcher.execute("AT+WRWIFI", timeout=3.0)
                    return True
        except Exception as exc:
            logger.warning("Direct HTTP post to QC-Webs failed: %s", exc)

        return False

    def get_connected_clients(
        self,
        host: str = "192.168.100.1",
        netns: Optional[str] = None,
        timeout: float = 2.0,
    ) -> List[Dict[str, str]]:
        """
        Discover active connected Wi-Fi client devices from the embedded QC-Webs
        DHCP lease table (dhcp_tbl.asp).
        """
        url = f"http://{host}/dhcp_tbl.asp"
        html_content = ""

        if netns:
            cmd = [
                "sudo", "-n", "ip", "netns", "exec", netns,
                "curl", "-s", "--connect-timeout", str(int(timeout)), url,
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 1.0)
                if res.returncode == 0:
                    html_content = res.stdout
            except Exception:
                pass
        else:
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        html_content = resp.read().decode("utf-8", errors="replace")
            except Exception:
                pass

        clients: List[Dict[str, str]] = []
        if not html_content:
            return clients

        # Parse HTML table rows from dhcp_tbl.asp
        # Format typical: <td>hostname</td><td>IP</td><td>MAC</td>
        rows = re.findall(r"<tr>(.*?)</tr>", html_content, re.DOTALL | re.IGNORECASE)
        for row in rows:
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL | re.IGNORECASE)
            if len(cells) >= 3:
                h_name = cells[0].strip()
                ip_addr = cells[1].strip()
                mac_addr = cells[2].strip()
                if re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", ip_addr) and re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac_addr):
                    clients.append({
                        "hostname": h_name or "Unknown",
                        "ip": ip_addr,
                        "mac": mac_addr,
                    })

        return clients
