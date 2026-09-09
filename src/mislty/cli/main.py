"""
mislty: Command-line interface for the MisLTy Qualcomm MDM9600 Linux Suite.
"""

import sys
import time
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
    p_connect.add_argument("--apn", default="internet", help="Carrier APN (default: internet)")
    p_connect.add_argument("--timeout", type=float, default=20.0, help="Connection timeout in seconds")
    p_connect.add_argument("--default", action="store_true", help="Configure ppp0 as the primary default gateway")
    
    # disconnect
    subparsers.add_parser("disconnect", help="Terminate active ppp0 data session and restore routes")
    
    # wifi
    p_wifi = subparsers.add_parser("wifi", help="Control Broadcom Wi-Fi co-processor")
    p_wifi.add_argument("action", choices=["on", "off", "status", "ssid", "password", "clients"], help="Wi-Fi action")
    p_wifi.add_argument("param", nargs="?", default=None, help="SSID name or password value")
    
    # mode
    p_mode = subparsers.add_parser("mode", help="Switch between operational modes")
    p_mode.add_argument("target", choices=["router", "usb"], help="Target operational mode")
    
    # sms
    p_sms = subparsers.add_parser("sms", help="SMS messaging tools")
    sms_sub = p_sms.add_subparsers(dest="sms_action", help="SMS subcommands")
    
    p_sms_list = sms_sub.add_parser("list", help="List SMS conversation threads or messages")
    p_sms_list.add_argument("-t", "--thread", type=int, default=None, help="Thread ID to inspect")
    p_sms_list.add_argument("--json", action="store_true", help="Output in structured JSON format")

    p_sms_send = sms_sub.add_parser("send", help="Send SMS message")
    p_sms_send.add_argument("recipient", help="Recipient phone number (e.g. +8801XXXXXXXXX)")
    p_sms_send.add_argument("text", help="Text message content (up to 160 GSM-7 characters)")

    p_sms_sync = sms_sub.add_parser("sync", help="Sync and reconcile SMS from SIM storage into SQLite")
    p_sms_sync.add_argument("--no-purge", action="store_true", help="Do not purge ingested messages from SIM card")
    p_sms_sync.add_argument("--json", action="store_true", help="Output synced messages in structured JSON")

    
    # sim
    subparsers.add_parser("sim", help="Inspect SIM status, IMSI, and operator network")
    
    # at
    p_at = subparsers.add_parser("at", help="Send raw Hayes AT command to modem")
    p_at.add_argument("command", help="Raw AT command string (e.g. 'AT+CSQ')")
    p_at.add_argument("-t", "--timeout", type=float, default=3.0, help="Command timeout in seconds (default: 3.0)")
    p_at.add_argument("-p", "--port", default=None, help="Explicit serial port (defaults to resolved control port)")
    p_at.add_argument("--json", action="store_true", help="Output response in structured JSON format")

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

    if parsed.subcommand == "at":
        import json
        from mislty.core.port_resolver import PortResolver
        from mislty.core.serial_transport import SerialTransport
        from mislty.core.at_parser import AtDispatcher

        port_path = parsed.port
        if not port_path:
            resolver = PortResolver()
            ports = resolver.resolve()
            if not ports.control or not ports.control.exists():
                print("Error: Modem control port not found.", file=sys.stderr)
                sys.exit(1)
            port_path = ports.control

        transport = SerialTransport(port_path, timeout=parsed.timeout)
        dispatcher = AtDispatcher(transport)
        resp = dispatcher.execute(parsed.command, timeout=parsed.timeout)

        if parsed.json:
            print(json.dumps(resp.as_dict(), indent=2))
        else:
            if resp.lines:
                for line in resp.lines:
                    print(line)
            if not resp.success:
                err = resp.error or "ERROR"
                detail = f" ({resp.error_detail})" if resp.error_detail else ""
                print(f"{err}{detail}", file=sys.stderr)

        sys.exit(0 if resp.success else 1)

    if parsed.subcommand == "sms":
        import json
        from mislty.storage.database import DatabaseManager
        from mislty.storage.sms_store import SmsStore

        db = DatabaseManager()
        sms = SmsStore(db)

        if parsed.sms_action == "list":
            if parsed.thread is not None:
                messages = sms.get_thread_messages(parsed.thread)
                if parsed.json:
                    print(json.dumps([m.as_dict() for m in messages], indent=2))
                else:
                    if not messages:
                        print(f"No messages in thread #{parsed.thread}.")
                    else:
                        for m in messages:
                            dir_symbol = "➔" if m.direction == "OUT" else "⬅"
                            print(f"[{m.id}] {dir_symbol} {m.phone_number} ({time.ctime(m.timestamp)}): {m.body}")
            else:
                threads = sms.list_threads()
                if parsed.json:
                    print(json.dumps([t.as_dict() for t in threads], indent=2))
                else:
                    if not threads:
                        print("No conversation threads found in local storage. (Run 'mislty sms sync' to fetch from SIM)")
                    else:
                        print(f"{'ID':<4} {'Recipient':<18} {'Unread':<8} {'Snippet':<40}")
                        print("-" * 72)
                        for t in threads:
                            contact = f" ({t.contact_name})" if t.contact_name else ""
                            recip = f"{t.recipient_number}{contact}"[:17]
                            print(f"{t.id:<4} {recip:<18} {t.unread_count:<8} {t.snippet:<40}")
            sys.exit(0)

        elif parsed.sms_action == "sync":
            from mislty.core.port_resolver import PortResolver
            from mislty.core.serial_transport import SerialTransport
            from mislty.core.at_parser import AtDispatcher

            ports = PortResolver().resolve()
            if not ports.control or not ports.control.exists():
                print("Error: Modem control port not found.", file=sys.stderr)
                sys.exit(1)

            transport = SerialTransport(ports.control, timeout=3.0)
            dispatcher = AtDispatcher(transport)

            print("Syncing SMS messages from SIM storage (SM) into SQLite...")
            ingested = sms.reconcile_sim_inbox(dispatcher, purge_sim=not parsed.no_purge)
            transport.close()

            if parsed.json:
                print(json.dumps([m.as_dict() for m in ingested], indent=2))
            else:
                print(f"Successfully synced {len(ingested)} new message(s) into local database.")
                for m in ingested:
                    print(f"  • Ingested from {m.phone_number} (SIM slot {m.sim_index}): {m.body[:60]}...")
            sys.exit(0)

        elif not parsed.sms_action:
            p_sms.print_help()
            sys.exit(0)

    if parsed.subcommand == "status":
        import json
        from mislty.core.port_resolver import PortResolver
        from mislty.core.serial_transport import SerialTransport
        from mislty.core.at_parser import AtDispatcher
        from mislty.net.ppp_controller import PppController
        from mislty.net.wifi_manager import WifiManager

        resolver = PortResolver()
        ports = resolver.resolve()
        ppp_mgr = PppController()
        ppp_stat = ppp_mgr.get_status()

        status_data = {
            "hardware": {
                "ready": ports.is_ready,
                "control": str(ports.control) if ports.control else None,
                "data": str(ports.data) if ports.data else None,
                "voice": str(ports.voice) if ports.voice else None,
                "diag": str(ports.diag) if ports.diag else None,
                "aux_wifi": ports.aux_wifi,
            },
            "cellular_ppp": ppp_stat.as_dict(),
            "radio": {
                "signal_csq": None,
                "rssi_dbm": None,
                "operator": None,
            },
            "wifi": {
                "power": None,
                "ssid": None,
                "clients_count": 0,
            },
        }

        if ports.control and ports.control.exists():
            try:
                transport = SerialTransport(ports.control, timeout=2.0)
                dispatcher = AtDispatcher(transport)

                csq = dispatcher.execute("AT+CSQ", timeout=2.0)
                if csq.success and csq.lines:
                    for line in csq.lines:
                        if "+CSQ:" in line:
                            val = line.split(":")[-1].strip().split(",")[0]
                            try:
                                raw_csq = int(val)
                                status_data["radio"]["signal_csq"] = raw_csq
                                if raw_csq != 99:
                                    status_data["radio"]["rssi_dbm"] = -113 + (raw_csq * 2)
                            except ValueError:
                                pass

                cops = dispatcher.execute("AT+COPS?", timeout=2.0)
                if cops.success and cops.lines:
                    for line in cops.lines:
                        if "+COPS:" in line and '"' in line:
                            status_data["radio"]["operator"] = line.split('"')[1]

                wifi = WifiManager(dispatcher)
                status_data["wifi"]["power"] = wifi.get_radio_power()
                status_data["wifi"]["ssid"] = wifi.get_ssid_serial()

                transport.close()
            except Exception:
                pass

        if ports.aux_wifi_netns:
            try:
                wifi = WifiManager()
                clients = wifi.get_connected_clients(netns=ports.aux_wifi_netns)
                status_data["wifi"]["clients_count"] = len(clients)
            except Exception:
                pass

        if parsed.json:
            print(json.dumps(status_data, indent=2))
        else:
            print("MisLTy Modem & Network Status")
            print("=" * 40)
            print(f"Hardware Ports : {'Ready' if status_data['hardware']['ready'] else 'Incomplete'}")
            print(f"  • Control    : {status_data['hardware']['control'] or 'None'}")
            print(f"  • Data       : {status_data['hardware']['data'] or 'None'}")
            print(f"  • Aux Wi-Fi  : {status_data['hardware']['aux_wifi'] or 'None'}")

            csq_str = f"{status_data['radio']['signal_csq']} ({status_data['radio']['rssi_dbm']} dBm)" if status_data['radio']['signal_csq'] is not None else "Unknown"
            print("\nCellular Radio")
            print(f"  • Operator   : {status_data['radio']['operator'] or 'Unknown'}")
            print(f"  • Signal CSQ : {csq_str}")

            wifi_pwr = "ON" if status_data["wifi"]["power"] else ("OFF" if status_data["wifi"]["power"] is False else "Unknown")
            print("\nBroadcom Wi-Fi")
            print(f"  • Radio Power: {wifi_pwr}")
            print(f"  • SSID       : {status_data['wifi']['ssid'] or 'Unknown'}")
            print(f"  • Clients    : {status_data['wifi']['clients_count']} connected")

            print(f"\n{ppp_stat}")
        sys.exit(0)

    if parsed.subcommand == "connect":
        from mislty.net.ppp_controller import PppController
        controller = PppController()
        print(f"Connecting cellular data link (APN: {parsed.apn}, default route: {parsed.default})...")
        ok = controller.connect(apn=parsed.apn, default_route=parsed.default, timeout=parsed.timeout)
        if ok:
            stat = controller.get_status()
            print(f"Connected! Interface: {stat.interface}, IP: {stat.ip_address}")
            if stat.dns_servers:
                print(f"DNS Servers: {', '.join(stat.dns_servers)}")
            sys.exit(0)
        else:
            print("Failed to establish cellular data connection.", file=sys.stderr)
            sys.exit(1)

    if parsed.subcommand == "disconnect":
        from mislty.net.ppp_controller import PppController
        controller = PppController()
        print("Terminating cellular PPP session and restoring network routes...")
        controller.disconnect()
        print("Disconnected.")
        sys.exit(0)

    if parsed.subcommand == "wifi":
        from mislty.core.port_resolver import PortResolver
        from mislty.core.serial_transport import SerialTransport
        from mislty.core.at_parser import AtDispatcher
        from mislty.net.wifi_manager import WifiManager

        ports = PortResolver().resolve()
        transport = None
        dispatcher = None
        if ports.control and ports.control.exists():
            try:
                transport = SerialTransport(ports.control, timeout=3.0)
                dispatcher = AtDispatcher(transport)
            except Exception as exc:
                print(f"Warning: Could not open control port: {exc}", file=sys.stderr)

        wifi = WifiManager(dispatcher)
        try:
            if parsed.action == "on":
                print("Enabling Wi-Fi radio...")
                ok = wifi.set_radio_power(True)
                print("Wi-Fi radio enabled." if ok else "Failed to enable Wi-Fi radio.", file=sys.stdout if ok else sys.stderr)
                sys.exit(0 if ok else 1)
            elif parsed.action == "off":
                print("Disabling Wi-Fi radio...")
                ok = wifi.set_radio_power(False)
                print("Wi-Fi radio disabled." if ok else "Failed to disable Wi-Fi radio.", file=sys.stdout if ok else sys.stderr)
                sys.exit(0 if ok else 1)
            elif parsed.action == "status":
                pwr = wifi.get_radio_power()
                ssid = wifi.get_ssid_serial()
                state_str = "ON" if pwr else ("OFF" if pwr is False else "Unknown")
                print(f"Wi-Fi Radio: {state_str}")
                print(f"SSID: {ssid or 'Unknown'}")
                sys.exit(0)
            elif parsed.action == "ssid":
                if not parsed.param:
                    ssid = wifi.get_ssid_serial()
                    print(f"Current SSID: {ssid or 'Unknown'}")
                else:
                    print(f"Configuring SSID: '{parsed.param}'...")
                    netns = ports.aux_wifi_netns
                    ok = wifi.set_clean_ssid_web(parsed.param, netns=netns)
                    if not ok:
                        ok = wifi.set_credentials_serial(parsed.param)
                    print(f"SSID configured to '{parsed.param}'." if ok else "Failed to configure SSID.", file=sys.stdout if ok else sys.stderr)
                    sys.exit(0 if ok else 1)
            elif parsed.action == "password":
                if not parsed.param:
                    print("Error: Password parameter required.", file=sys.stderr)
                    sys.exit(1)
                ssid = wifi.get_ssid_serial() or "TypeScript 420"
                print("Configuring Wi-Fi WPA2 password...")
                ok = wifi.set_credentials_serial(ssid, password=parsed.param)
                print("Wi-Fi password configured." if ok else "Failed to configure password.", file=sys.stdout if ok else sys.stderr)
                sys.exit(0 if ok else 1)
            elif parsed.action == "clients":
                netns = ports.aux_wifi_netns
                clients = wifi.get_connected_clients(netns=netns)
                if not clients:
                    print("No connected Wi-Fi clients detected.")
                else:
                    print(f"{'Hostname':<20} {'IP Address':<18} {'MAC Address':<18}")
                    print("-" * 58)
                    for c in clients:
                        print(f"{c['hostname']:<20} {c['ip']:<18} {c['mac']:<18}")
                sys.exit(0)
        finally:
            if transport:
                transport.close()




if __name__ == "__main__":
    main()
