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
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable ANSI colors and visual formatting in terminal output",
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

    # relay
    p_relay = subparsers.add_parser("relay", help="Assist Wi-Fi Hotspot Relay control (Issue #22)")
    relay_sub = p_relay.add_subparsers(dest="relay_action", help="Relay subcommands")

    p_relay_list = relay_sub.add_parser("list", help="List detected WLAN devices and identify candidate assist adapters")
    p_relay_list.add_argument("--json", action="store_true", help="Output in structured JSON")

    p_relay_start = relay_sub.add_parser("start", help="Start assist Wi-Fi hotspot relay and route over WAN")
    p_relay_start.add_argument("-i", "--interface", default="wlan1", help="Target assist WLAN interface (default: wlan1)")
    p_relay_start.add_argument("-s", "--ssid", default="MisLTy 4G Share", help="Hotspot broadcast SSID")
    p_relay_start.add_argument("-p", "--password", default="mislty420", help="WPA2-PSK passphrase (min 8 chars)")
    p_relay_start.add_argument("-b", "--band", choices=["bg", "a"], default="bg", help="Wi-Fi frequency band (default: bg [2.4GHz])")
    p_relay_start.add_argument("-c", "--channel", type=int, default=11, help="Wi-Fi channel (default: 11)")
    p_relay_start.add_argument("-w", "--wan", default="ppp0", help="WAN upstream interface (default: ppp0)")
    p_relay_start.add_argument("--json", action="store_true", help="Output in structured JSON")

    p_relay_stop = relay_sub.add_parser("stop", help="Stop assist Wi-Fi hotspot relay and teardown NAT")
    p_relay_stop.add_argument("--json", action="store_true", help="Output in structured JSON")

    p_relay_status = relay_sub.add_parser("status", help="Query live hotspot relay telemetry and uptime")
    p_relay_status.add_argument("--json", action="store_true", help="Output in structured JSON")

    p_relay_clients = relay_sub.add_parser("clients", help="List connected wireless client stations")
    p_relay_clients.add_argument("--json", action="store_true", help="Output in structured JSON")

    # gui
    subparsers.add_parser("gui", help="Launch MisLTy Desktop GUI Application")

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

    if parsed.subcommand == "gui":
        from mislty.gui.app import main as gui_main
        sys.exit(gui_main())

    import json
    from mislty.ipc.client import MisltyClient

    client = MisltyClient()

    try:
        if parsed.subcommand == "at":
            if parsed.port:
                from mislty.core.serial_transport import SerialTransport
                from mislty.core.at_parser import AtDispatcher
                transport = SerialTransport(parsed.port, timeout=parsed.timeout)
                dispatcher = AtDispatcher(transport)
                resp = dispatcher.execute(parsed.command, timeout=parsed.timeout).as_dict()
                transport.close()
            else:
                resp = client.execute_at(parsed.command, timeout=parsed.timeout)

            if parsed.json:
                print(json.dumps(resp, indent=2))
            else:
                lines = resp.get("lines", [])
                for line in lines:
                    print(line)
                if not resp.get("success"):
                    err = resp.get("error") or "ERROR"
                    detail = f" ({resp.get('error_detail')})" if resp.get("error_detail") else ""
                    print(f"{err}{detail}", file=sys.stderr)
            sys.exit(0 if resp.get("success") else 1)

        elif parsed.subcommand == "status":
            from mislty.cli.formatter import TerminalFormatter
            fmt = TerminalFormatter(force_color=False if parsed.no_color else None)

            status_data = client.get_status()
            if parsed.json:
                print(json.dumps(status_data, indent=2))
            else:
                daemon_info = status_data.get("daemon", {})
                hw_info = status_data.get("hardware", {})
                ppp_info = status_data.get("cellular_ppp", {})
                wifi_info = status_data.get("wifi", {})

                print(fmt.bold("MisLTy Cellular & Wi-Fi Station"))
                print(fmt.dim("=" * 45))
                backend_str = fmt.cyan(client.active_transport, bold=True)
                print(f"IPC Transport  : {backend_str}")

                hw_ready = bool(hw_info.get("is_present") or hw_info.get("control"))
                hw_badge = fmt.green("[Ready]", bold=True) if hw_ready else fmt.yellow("[Incomplete]", bold=True)
                print(f"Hardware State : {hw_badge}")
                print(f"  • Control    : {hw_info.get('control') or 'None'}")
                print(f"  • Data       : {hw_info.get('data') or 'None'}")
                print(f"  • Aux Wi-Fi  : {hw_info.get('aux_wifi') or 'None'}")

                csq = daemon_info.get("rssi")
                dbm = daemon_info.get("dbm")
                radio_online = bool(daemon_info.get("carrier") or (csq and csq > 0))
                print(f"\n{fmt.bold('Cellular Baseband')} : {fmt.format_badge(radio_online)}")
                print(f"  • Operator   : {fmt.bold(daemon_info.get('carrier') or 'Unknown')}")
                print(f"  • RAT / Mode : {daemon_info.get('technology') or 'Unknown'}")
                print(f"  • RF Signal  : {fmt.format_signal_meter(csq, dbm)}")

                wifi_pwr = bool(wifi_info.get("power"))
                print(f"\n{fmt.bold('Broadcom Wi-Fi')}   : {fmt.format_badge(wifi_pwr)}")
                print(f"  • Broadcast  : {fmt.bold(wifi_info.get('ssid') or 'Unknown')}")
                print(f"  • Clients    : {wifi_info.get('clients_count', 0)} connected")

                ppp_connected = bool(ppp_info.get("connected"))
                print(f"\n{fmt.bold('PPP Data Plane')}   : {fmt.format_badge(ppp_connected, on_text='CONNECTED', off_text='DISCONNECTED')}")
                if ppp_connected:
                    print(f"  • Interface  : {fmt.bold(ppp_info.get('interface', 'ppp0'))}")
                    print(f"  • Local IP   : {fmt.green(ppp_info.get('ip_address') or 'Unknown')}")
                    print(f"  • Peer IP    : {ppp_info.get('peer_ip') or 'Unknown'}")
                    dns_str = ", ".join(ppp_info.get("dns_servers", [])) or "None"
                    print(f"  • DNS        : {dns_str}")
                    rx_str = fmt.format_bytes(ppp_info.get("rx_bytes", 0))
                    tx_str = fmt.format_bytes(ppp_info.get("tx_bytes", 0))
                    print(f"  • Bandwidth  : RX {rx_str} | TX {tx_str}")
                    print(f"  • Uptime     : {ppp_info.get('uptime_seconds', 0):.0f}s")
            sys.exit(0)

        elif parsed.subcommand == "connect":
            print(f"Connecting cellular data link (APN: {parsed.apn}, default route: {parsed.default})...")
            res = client.connect(apn=parsed.apn, default_route=parsed.default, timeout=parsed.timeout)
            if res.get("success"):
                stat = res.get("status", {})
                ip = stat.get("ip_address") or "Allocated"
                print(f"Connected! Interface: {stat.get('interface', 'ppp0')}, IP: {ip}")
                sys.exit(0)
            else:
                print("Failed to establish cellular data connection.", file=sys.stderr)
                sys.exit(1)

        elif parsed.subcommand == "disconnect":
            print("Terminating cellular PPP session and restoring network routes...")
            client.disconnect()
            print("Disconnected.")
            sys.exit(0)

        elif parsed.subcommand == "wifi":
            from mislty.cli.formatter import TerminalFormatter
            fmt = TerminalFormatter(force_color=False if parsed.no_color else None)

            if parsed.action == "on":
                print("Enabling Wi-Fi radio...")
                res = client.set_wifi_power(True)
                ok = res.get("success", False)
                print(fmt.green("Wi-Fi radio enabled.") if ok else fmt.red("Failed to enable Wi-Fi radio."), file=sys.stdout if ok else sys.stderr)
                sys.exit(0 if ok else 1)
            elif parsed.action == "off":
                print("Disabling Wi-Fi radio...")
                res = client.set_wifi_power(False)
                ok = res.get("success", False)
                print(fmt.green("Wi-Fi radio disabled.") if ok else fmt.red("Failed to disable Wi-Fi radio."), file=sys.stdout if ok else sys.stderr)
                sys.exit(0 if ok else 1)
            elif parsed.action == "status":
                status = client.get_status()
                wifi_info = status.get("wifi", {})
                pwr = wifi_info.get("power")
                state_str = "ON" if pwr else ("OFF" if pwr is False else "Unknown")
                print(f"Wi-Fi Radio: {state_str}")
                print(f"SSID: {wifi_info.get('ssid') or 'Unknown'}")
                sys.exit(0)
            elif parsed.action == "ssid":
                if not parsed.param:
                    status = client.get_status()
                    print(f"Current SSID: {status.get('wifi', {}).get('ssid') or 'Unknown'}")
                else:
                    print(f"Configuring SSID: '{parsed.param}'...")
                    res = client.set_wifi_credentials(parsed.param)
                    ok = res.get("success", False)
                    print(fmt.green(f"SSID configured to '{parsed.param}'.") if ok else fmt.red("Failed to configure SSID."), file=sys.stdout if ok else sys.stderr)
                    sys.exit(0 if ok else 1)
            elif parsed.action == "password":
                if not parsed.param:
                    print("Error: Password parameter required.", file=sys.stderr)
                    sys.exit(1)
                status = client.get_status()
                ssid = status.get("wifi", {}).get("ssid") or "TypeScript 420"
                print("Configuring Wi-Fi WPA2 password...")
                res = client.set_wifi_credentials(ssid, password=parsed.param)
                ok = res.get("success", False)
                print(fmt.green("Wi-Fi password configured.") if ok else fmt.red("Failed to configure password."), file=sys.stdout if ok else sys.stderr)
                sys.exit(0 if ok else 1)
            elif parsed.action == "clients":
                clients = client.get_wifi_clients()
                if not clients:
                    print("No connected Wi-Fi clients detected.")
                else:
                    rows = [[c.get("hostname", "Unknown"), c.get("ip", ""), c.get("mac", "")] for c in clients]
                    print(fmt.format_table(["Hostname", "IP Address", "MAC Address"], rows))
                sys.exit(0)

        elif parsed.subcommand == "sms":
            from mislty.cli.formatter import TerminalFormatter
            fmt = TerminalFormatter(force_color=False if parsed.no_color else None)

            if parsed.sms_action == "list":
                items = client.list_sms(thread_id=parsed.thread)
                if parsed.json:
                    print(json.dumps(items, indent=2))
                else:
                    if parsed.thread is not None:
                        if not items:
                            print(f"No messages in thread #{parsed.thread}.")
                        else:
                            rows = []
                            for m in items:
                                dir_symbol = "➔" if m.get("direction") == "OUT" else "⬅"
                                t_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(m.get("timestamp", 0)))
                                rows.append([str(m.get("id")), dir_symbol, m.get("phone_number", ""), t_str, m.get("body", "")])
                            print(fmt.format_table(["ID", "Dir", "Phone Number", "Timestamp", "Message Body"], rows))
                    else:
                        if not items:
                            print("No conversation threads found. (Run 'mislty sms sync' to fetch from SIM)")
                        else:
                            rows = []
                            for t in items:
                                contact = f" ({t.get('contact_name')})" if t.get("contact_name") else ""
                                recip = f"{t.get('recipient_number')}{contact}"
                                updated = time.strftime("%b %d %H:%M", time.localtime(t.get("updated_at", 0)))
                                rows.append([str(t.get("id")), recip, str(t.get("unread_count", 0)), updated, t.get("snippet", "")])
                            print(fmt.format_table(["ID", "Recipient", "Unread", "Updated", "Latest Snippet"], rows))
                sys.exit(0)

            elif parsed.sms_action == "send":
                print(f"Sending SMS to {parsed.recipient}...")
                res = client.send_sms(parsed.recipient, parsed.text)
                if res.get("success"):
                    print(fmt.green(f"SMS sent successfully (Message ID: {res.get('message_id')})."))
                    sys.exit(0)
                else:
                    print(fmt.red(f"Failed to send SMS: {res.get('error') or 'Error'}"), file=sys.stderr)
                    sys.exit(1)

            elif parsed.sms_action == "sync":
                print("Syncing SMS messages from SIM storage (SM) into SQLite...")
                ingested = client.sync_sms(purge_sim=not parsed.no_purge)
                if parsed.json:
                    print(json.dumps(ingested, indent=2))
                else:
                    print(fmt.green(f"Successfully synced {len(ingested)} new message(s)."))
                    for m in ingested:
                        print(f"  • Ingested from {m.get('phone_number')} (SIM slot {m.get('sim_index')}): {m.get('body', '')[:60]}...")
                sys.exit(0)

            elif not parsed.sms_action:
                p_sms.print_help()
                sys.exit(0)

        elif parsed.subcommand == "sim":
            from mislty.cli.formatter import TerminalFormatter
            fmt = TerminalFormatter(force_color=False if parsed.no_color else None)

            resp_cimi = client.execute_at("AT+CIMI")
            resp_cpin = client.execute_at("AT+CPIN?")
            resp_cops = client.execute_at("AT+COPS?")

            imsi = "Unknown"
            if resp_cimi.get("lines"):
                for l in resp_cimi["lines"]:
                    if l.strip().isdigit():
                        imsi = l.strip()

            cpin = "Unknown"
            if resp_cpin.get("lines"):
                for l in resp_cpin["lines"]:
                    if "+CPIN:" in l:
                        cpin = l.split(":")[-1].strip()

            operator = "Unknown"
            if resp_cops.get("lines"):
                for l in resp_cops["lines"]:
                    if "+COPS:" in l and '"' in l:
                        operator = l.split('"')[1]

            print(fmt.bold("SIM Card & Subscription Status"))
            print(fmt.dim("=" * 45))
            pin_badge = fmt.green(cpin) if cpin == "READY" else fmt.yellow(cpin)
            print(f"  • PIN Status : {pin_badge}")
            print(f"  • IMSI       : {fmt.bold(imsi)}")
            print(f"  • Operator   : {fmt.cyan(operator, bold=True)}")
            sys.exit(0)

        elif parsed.subcommand == "relay":
            from mislty.cli.formatter import TerminalFormatter
            fmt = TerminalFormatter(force_color=False if parsed.no_color else None)

            if parsed.relay_action == "list":
                devs = client.list_wlan_devices()
                if parsed.json:
                    print(json.dumps(devs, indent=2))
                else:
                    print(fmt.bold("Discovered Host Wireless Adapters"))
                    print(fmt.dim("=" * 60))
                    rows = []
                    for d in devs:
                        if d.get("is_in_use") or d.get("is_primary"):
                            conn = d.get("active_connection")
                            label = f"PROTECTED ({conn})" if conn else "PROTECTED (Host Link)"
                            role = fmt.cyan(label)
                        elif d.get("is_candidate"):
                            role = fmt.green("CANDIDATE (Relay Hotspot)")
                        else:
                            role = fmt.yellow("Unsupported")
                        rows.append([
                            d.get("iface", ""),
                            f"{d.get('vendor', '')} {d.get('model', '')}".strip() or "Unknown Adapter",
                            d.get("driver", ""),
                            d.get("mac", ""),
                            role,
                        ])
                    print(fmt.format_table(["Interface", "Hardware Model", "Driver", "MAC Address", "Role / Status"], rows))
                sys.exit(0)

            elif parsed.relay_action == "start":
                print(f"Starting Wi-Fi Hotspot Relay on {parsed.interface} (SSID: '{parsed.ssid}')...")
                try:
                    res = client.start_hotspot_relay(
                        interface=parsed.interface,
                        ssid=parsed.ssid,
                        password=parsed.password,
                        band=parsed.band,
                        channel=parsed.channel,
                        wan_iface=parsed.wan,
                    )
                except Exception as exc:
                    print(fmt.red(f"Failed to start Hotspot Relay: {exc}"), file=sys.stderr)
                    sys.exit(1)
                if parsed.json:
                    print(json.dumps(res, indent=2))
                else:
                    if res.get("active"):
                        print(fmt.green(f"Hotspot Relay ACTIVE on {res.get('interface')}!"))
                        print(f"  • SSID     : {fmt.bold(res.get('ssid', ''))}")
                        print(f"  • IP Subnet: {fmt.cyan(res.get('ip_address', '10.42.0.1'))}/24")
                        print(f"  • Upstream : {fmt.bold(res.get('wan_iface', 'ppp0'))}")
                        print(f"  • Channel  : {res.get('channel', 11)} ({res.get('band', 'bg').upper()})")
                        sys.exit(0)
                    else:
                        print(fmt.red("Failed to start Hotspot Relay."), file=sys.stderr)
                        sys.exit(1)

            elif parsed.relay_action == "stop":
                print("Stopping Hotspot Relay and flushing forwarding rules...")
                res = client.stop_hotspot_relay()
                if parsed.json:
                    print(json.dumps(res, indent=2))
                else:
                    print(fmt.green("Hotspot Relay deactivated and routes restored."))
                sys.exit(0)

            elif parsed.relay_action == "status":
                stat = client.get_hotspot_relay_status()
                if parsed.json:
                    print(json.dumps(stat, indent=2))
                else:
                    active_str = fmt.green("ACTIVE") if stat.get("active") else fmt.yellow("INACTIVE")
                    print(fmt.bold("Assist Wi-Fi Hotspot Relay Telemetry"))
                    print(fmt.dim("=" * 45))
                    print(f"  • State      : {active_str}")
                    if stat.get("active"):
                        print(f"  • Interface  : {stat.get('interface')}")
                        print(f"  • SSID       : {fmt.bold(stat.get('ssid', ''))}")
                        print(f"  • IP Address : {stat.get('ip_address')}")
                        print(f"  • Upstream   : {stat.get('wan_iface')}")
                        print(f"  • Clients    : {stat.get('client_count', 0)}")
                        print(f"  • Uptime     : {stat.get('uptime_seconds', 0)}s")
                sys.exit(0)

            elif parsed.relay_action == "clients":
                clients = client.get_hotspot_relay_clients()
                if parsed.json:
                    print(json.dumps(clients, indent=2))
                else:
                    if not clients:
                        print("No wireless stations currently associated with assist hotspot.")
                    else:
                        rows = []
                        for c in clients:
                            sig = f"{c.get('signal_dbm')} dBm" if c.get("signal_dbm") is not None else "N/A"
                            rx_mb = f"{c.get('rx_bytes', 0) / (1024 * 1024):.2f} MB"
                            tx_mb = f"{c.get('tx_bytes', 0) / (1024 * 1024):.2f} MB"
                            rows.append([
                                c.get("mac", ""),
                                c.get("ip") or "Assigning...",
                                sig,
                                rx_mb,
                                tx_mb,
                            ])
                        print(fmt.format_table(["MAC Address", "IP Address", "Signal", "RX", "TX"], rows))
                sys.exit(0)

            elif not parsed.relay_action:
                p_relay.print_help()
                sys.exit(0)

    finally:
        client.close()


if __name__ == "__main__":
    main()
