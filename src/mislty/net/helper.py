"""
mislty.net.helper
~~~~~~~~~~~~~~~~~

Privileged Network Helper executed under Polkit (pkexec) or root.
Enforces strict argument validation and executes bounded networking operations:
routing table adjustments, PPP process control, and NAT forwarding.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
from typing import Any, Dict, List, Optional, Union


logger = logging.getLogger("mislty.net.helper")

# Strict validation patterns
RE_IFACE = re.compile(r"^[a-zA-Z0-9_.-]{2,16}$")
RE_DEV_NODE = re.compile(r"^/dev/(?:mislty/)?[a-zA-Z0-9_.-]+$")
RE_APN = re.compile(r"^[a-zA-Z0-9_.-]{1,64}$")


class HelperError(Exception):
    """Base exception for privileged helper failures."""
    pass


class ValidationError(HelperError):
    """Raised when an argument fails security validation."""
    pass


def validate_interface(iface: str) -> str:
    """Validate network interface name."""
    if not RE_IFACE.match(iface):
        raise ValidationError(f"Invalid interface name: {iface}")
    return iface


def validate_dev_node(dev_path: str) -> str:
    """Validate character device node path."""
    if not RE_DEV_NODE.match(dev_path):
        raise ValidationError(f"Invalid device node path: {dev_path}")
    return dev_path


def validate_ip(ip_str: str) -> str:
    """Validate IPv4 address."""
    try:
        ipaddress.IPv4Address(ip_str)
        return ip_str
    except ValueError as exc:
        raise ValidationError(f"Invalid IP address {ip_str}: {exc}") from exc


def validate_metric(metric_val: Union[int, str]) -> int:
    """Validate routing metric."""
    try:
        val = int(metric_val)
        if 0 <= val <= 20000:
            return val
    except (ValueError, TypeError):
        pass
    raise ValidationError(f"Invalid routing metric: {metric_val}")


def execute_cmd(cmd: List[str]) -> subprocess.CompletedProcess:
    """Execute command safely without shell expansion."""
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return res
    except OSError as exc:
        raise HelperError(f"Failed to execute {cmd[0]}: {exc}") from exc


# Action Handlers

def handle_check_auth() -> Dict[str, Any]:
    """Verify caller authorization and EUID."""
    return {"status": "authorized", "euid": os.geteuid()}


def handle_set_default_route(dev: str, metric: int) -> Dict[str, Any]:
    """Replace default route with higher priority route on specified dev."""
    valid_dev = validate_interface(dev)
    valid_metric = validate_metric(metric)

    res = execute_cmd(["ip", "route", "replace", "default", "dev", valid_dev, "metric", str(valid_metric)])
    if res.returncode != 0:
        raise HelperError(f"ip route replace failed: {res.stderr.strip()}")
    return {"success": True, "action": "set-default-route", "dev": valid_dev, "metric": valid_metric}


def handle_restore_default_route(gw: str, dev: str, metric: int = 600) -> Dict[str, Any]:
    """Restore default route via gateway on dev."""
    valid_gw = validate_ip(gw)
    valid_dev = validate_interface(dev)
    valid_metric = validate_metric(metric)

    res = execute_cmd([
        "ip", "route", "replace", "default", "via", valid_gw, "dev", valid_dev, "metric", str(valid_metric)
    ])
    if res.returncode != 0:
        raise HelperError(f"ip route replace failed: {res.stderr.strip()}")
    return {
        "success": True,
        "action": "restore-default-route",
        "gw": valid_gw,
        "dev": valid_dev,
        "metric": valid_metric,
    }


def handle_enable_nat(wan_iface: str, lan_iface: str) -> Dict[str, Any]:
    """Enable IP forwarding and NAT masquerade between WAN and LAN interfaces."""
    w_iface = validate_interface(wan_iface)
    l_iface = validate_interface(lan_iface)

    # 1. Enable IPv4 forwarding
    try:
        Path("/proc/sys/net/ipv4/ip_forward").write_text("1\n")
    except OSError as exc:
        raise HelperError(f"Failed to enable ip_forward: {exc}") from exc

    # 2. Add iptables MASQUERADE if not already present
    check_res = execute_cmd(["iptables", "-t", "nat", "-C", "POSTROUTING", "-o", w_iface, "-j", "MASQUERADE"])
    if check_res.returncode != 0:
        add_res = execute_cmd(["iptables", "-t", "nat", "-A", "POSTROUTING", "-o", w_iface, "-j", "MASQUERADE"])
        if add_res.returncode != 0:
            raise HelperError(f"iptables nat rule failed: {add_res.stderr.strip()}")

    # 3. Add forward rules
    execute_cmd(["iptables", "-A", "FORWARD", "-i", l_iface, "-o", w_iface, "-j", "ACCEPT"])
    execute_cmd(["iptables", "-A", "FORWARD", "-i", w_iface, "-o", l_iface, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"])

    return {"success": True, "action": "enable-nat", "wan": w_iface, "lan": l_iface}


def handle_disable_nat(wan_iface: str, lan_iface: str) -> Dict[str, Any]:
    """Remove NAT masquerade and forwarding rules."""
    w_iface = validate_interface(wan_iface)
    l_iface = validate_interface(lan_iface)

    execute_cmd(["iptables", "-t", "nat", "-D", "POSTROUTING", "-o", w_iface, "-j", "MASQUERADE"])
    execute_cmd(["iptables", "-D", "FORWARD", "-i", l_iface, "-o", w_iface, "-j", "ACCEPT"])
    execute_cmd(["iptables", "-D", "FORWARD", "-i", w_iface, "-o", l_iface, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"])

    return {"success": True, "action": "disable-nat", "wan": w_iface, "lan": l_iface}


RUN_DIR = Path("/run/mislty")
PPP_PID_FILE = RUN_DIR / "pppd.pid"
CHAT_FILE = RUN_DIR / "chat-mislty"


def handle_start_ppp(dev: str, apn: str = "internet") -> Dict[str, Any]:
    """Configure chat script and launch pppd daemon."""
    valid_dev = validate_dev_node(dev)
    if not RE_APN.match(apn):
        raise ValidationError(f"Invalid APN: {apn}")

    RUN_DIR.mkdir(parents=True, exist_ok=True)

    chat_content = f"""ABORT "BUSY"
ABORT "NO CARRIER"
ABORT "NO DIALTONE"
ABORT "ERROR"
TIMEOUT 15
"" AT
OK AT+CGDCONT=1,"IP","{apn}"
OK "ATD*99#"
CONNECT ""
"""
    CHAT_FILE.write_text(chat_content, encoding="utf-8")
    os.chmod(CHAT_FILE, 0o600)

    cmd = [
        "pppd",
        valid_dev,
        "115200",
        "connect", f"/usr/bin/chat -v -f {CHAT_FILE}",
        "noauth",
        "nodefaultroute",
        "usepeerdns",
        "hide-password",
        "noipdefault",
        "ipcp-accept-local",
        "ipcp-accept-remote",
        "lcp-echo-failure", "4",
        "lcp-echo-interval", "5",
        "maxfail", "3",
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    PPP_PID_FILE.write_text(f"{proc.pid}\n", encoding="utf-8")

    return {"success": True, "action": "start-ppp", "pid": proc.pid, "dev": valid_dev, "apn": apn}


def handle_stop_ppp() -> Dict[str, Any]:
    """Terminate active pppd processes gracefully."""
    killed = False
    if PPP_PID_FILE.is_file():
        try:
            pid = int(PPP_PID_FILE.read_text(encoding="utf-8").strip())
            os.kill(pid, signal.SIGTERM)
            killed = True
        except (OSError, ValueError):
            pass
        finally:
            try:
                PPP_PID_FILE.unlink(missing_ok=True)
            except OSError:
                pass

    res = execute_cmd(["killall", "-TERM", "pppd"])
    if res.returncode == 0:
        killed = True

    return {"success": True, "action": "stop-ppp", "killed": killed}


def build_parser() -> argparse.ArgumentParser:
    """Build argument parser for privileged network helper."""
    parser = argparse.ArgumentParser(
        prog="mislty-net-helper",
        description="MisLTy Privileged Network Helper",
    )
    subparsers = parser.add_subparsers(dest="action", required=True)

    # check-auth
    subparsers.add_parser("check-auth", help="Verify Polkit root execution")

    # start-ppp
    p_start_ppp = subparsers.add_parser("start-ppp", help="Launch pppd on dev with apn")
    p_start_ppp.add_argument("dev", help="Serial device node (e.g. /dev/mislty/data)")
    p_start_ppp.add_argument("--apn", default="internet", help="Carrier APN")

    # stop-ppp
    subparsers.add_parser("stop-ppp", help="Terminate pppd daemon")

    # set-default-route
    p_set_route = subparsers.add_parser("set-default-route", help="Set default route via dev")
    p_set_route.add_argument("dev", help="Interface name (e.g. ppp0)")
    p_set_route.add_argument("--metric", type=int, default=50, help="Routing metric")

    # restore-default-route
    p_restore = subparsers.add_parser("restore-default-route", help="Restore default route via gateway")
    p_restore.add_argument("gw", help="Gateway IP address")
    p_restore.add_argument("dev", help="Interface name (e.g. wlan0)")
    p_restore.add_argument("--metric", type=int, default=600, help="Routing metric")

    # enable-nat
    p_en_nat = subparsers.add_parser("enable-nat", help="Enable NAT masquerade")
    p_en_nat.add_argument("wan", help="WAN interface (e.g. ppp0)")
    p_en_nat.add_argument("lan", help="LAN interface (e.g. wlan1)")

    # disable-nat
    p_dis_nat = subparsers.add_parser("disable-nat", help="Disable NAT masquerade")
    p_dis_nat.add_argument("wan", help="WAN interface")
    p_dis_nat.add_argument("lan", help="LAN interface")

    return parser


def main(args=None) -> None:
    parser = build_parser()
    parsed = parser.parse_args(args)

    if os.geteuid() != 0:
        print(json.dumps({"error": "PERMISSION_DENIED", "message": "mislty-net-helper must be executed as root via pkexec"}), file=sys.stderr)
        sys.exit(1)

    try:
        if parsed.action == "check-auth":
            result = handle_check_auth()
        elif parsed.action == "start-ppp":
            result = handle_start_ppp(parsed.dev, parsed.apn)
        elif parsed.action == "stop-ppp":
            result = handle_stop_ppp()
        elif parsed.action == "set-default-route":
            result = handle_set_default_route(parsed.dev, parsed.metric)
        elif parsed.action == "restore-default-route":
            result = handle_restore_default_route(parsed.gw, parsed.dev, parsed.metric)
        elif parsed.action == "enable-nat":
            result = handle_enable_nat(parsed.wan, parsed.lan)
        elif parsed.action == "disable-nat":
            result = handle_disable_nat(parsed.wan, parsed.lan)
        else:
            parser.print_help()
            sys.exit(1)

        print(json.dumps(result, indent=2))
        sys.exit(0)
    except (ValidationError, HelperError) as exc:
        print(json.dumps({"error": type(exc).__name__, "message": str(exc)}), file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(json.dumps({"error": "UNEXPECTED_ERROR", "message": str(exc)}), file=sys.stderr)
        sys.exit(2)



if __name__ == "__main__":
    main()
