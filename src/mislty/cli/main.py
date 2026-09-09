"""
mislty: Command-line interface for the MisLTy Qualcomm MDM9600 Linux Suite.
"""

import sys
import argparse
import mislty

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mislty",
        description="Production Linux CLI Suite for Qualcomm MDM9600 / Aleka UV310 4G LTE Modems",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Purrfect Software Limited (PSL) - Software out of time, for hardware out of time."
    )
    parser.add_argument(
        "-V", "--version",
        action="version",
        version=f"%(prog)s {mislty.__version__} (Qualcomm MDM9600 / Aleka UV310)"
    )
    
    subparsers = parser.add_subparsers(dest="subcommand", help="Operational Subcommands")
    
    # status
    p_status = subparsers.add_parser("status", help="Query modem, SIM, RF signal, Wi-Fi, and network status")
    p_status.add_argument("--json", action="store_true", help="Output status in structured JSON format")
    
    # connect
    p_connect = subparsers.add_parser("connect", help="Establish USB cellular data connection (ppp0)")
    p_connect.add_argument("--default", action="store_true", help="Configure ppp0 as the primary default gateway")
    
    # disconnect
    subparsers.add_parser("disconnect", help="Terminate active ppp0 data session and restore routes")
    
    # wifi
    p_wifi = subparsers.add_parser("wifi", help="Control Broadcom Wi-Fi co-processor")
    p_wifi.add_argument("action", choices=["on", "off", "status", "ssid", "password"], help="Wi-Fi action")
    p_wifi.add_argument("param", nargs="?", default=None, help="SSID name or password value")
    
    # mode
    p_mode = subparsers.add_parser("mode", help="Switch between operational modes")
    p_mode.add_argument("target", choices=["router", "usb"], help="Target operational mode")
    
    # sms
    p_sms = subparsers.add_parser("sms", help="SMS messaging tools")
    sms_sub = p_sms.add_subparsers(dest="sms_action", help="SMS subcommands")
    sms_sub.add_parser("list", help="List SMS messages")
    p_sms_send = sms_sub.add_parser("send", help="Send SMS message")
    p_sms_send.add_argument("recipient", help="Recipient phone number (e.g. +8801XXXXXXXXX)")
    p_sms_send.add_argument("text", help="Text message content (up to 160 GSM-7 characters)")
    
    # sim
    subparsers.add_parser("sim", help="Inspect SIM status, IMSI, and operator network")
    
    # at
    p_at = subparsers.add_parser("at", help="Send raw Hayes AT command to modem")
    p_at.add_argument("command", help="Raw AT command string (e.g. 'AT+CSQ')")

    # ports
    p_ports = subparsers.add_parser("ports", help="Resolve and inspect modem hardware endpoints")
    p_ports.add_argument("--json", action="store_true", help="Output ports mapping in structured JSON")
    p_ports.add_argument("--no-udev", action="store_true", help="Bypass udev and crawl sysfs directly")

    return parser


def main(args=None):
    parser = build_parser()
    parsed = parser.parse_args(args)
    if not parsed.subcommand:
        parser.print_help()
        sys.exit(0)

    if parsed.subcommand == "ports":
        import json
        from mislty.core.port_resolver import PortResolver
        resolver = PortResolver()
        ports = resolver.resolve(prefer_udev=not parsed.no_udev)
        if parsed.json:
            print(json.dumps(ports.as_dict(), indent=2))
        else:
            print(ports)
        sys.exit(0 if ports.is_ready else 1)

    print(f"mislty: subcommand '{parsed.subcommand}' called (pipeline active).")


if __name__ == "__main__":
    main()
