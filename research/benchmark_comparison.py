#!/usr/bin/env python3
import subprocess
import time
import json
import re

def sh(cmd):
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

print("=================================================================")
print("  MisLTy Comparative Performance Benchmark: Wi-Fi vs. USB PPP   ")
print("=================================================================")

results = {}

# --- SECTION 1: Wi-Fi Pocket Router Mode ---
print("\n[1/3] Benchmarking 4G Pocket Router Mode (Wi-Fi 802.11n)...")

# Cellular Telemetry
_, csq, _ = sh("python3 bin/ufi-modem at 'AT+CSQ'")
_, cops, _ = sh("python3 bin/ufi-modem at 'AT+COPS?'")
_, cereg, _ = sh("python3 bin/ufi-modem at 'AT+CEREG?'")

rssi = 99
for line in csq.splitlines():
    if "+CSQ:" in line:
        val = line.split(":", 1)[-1].strip().split(",")[0]
        if val.isdigit():
            rssi = int(val)
dbm = -113 + (rssi * 2) if rssi != 99 else -999

op = "Unknown"
for line in cops.splitlines():
    if "+COPS:" in line and '"' in line:
        op = line.split('"')[1]

# Wi-Fi Link Details
_, link_out, _ = sh("sudo ip netns exec wifi-client iw dev wlan1 link")
sig_wifi = "N/A"
tx_rate = "N/A"
rx_rate = "N/A"
for l in link_out.splitlines():
    if "signal:" in l:
        sig_wifi = l.split(":", 1)[-1].strip()
    if "tx bitrate:" in l:
        tx_rate = l.split(":", 1)[-1].strip()
    if "rx bitrate:" in l:
        rx_rate = l.split(":", 1)[-1].strip()

# Local Gateway Ping (10 packets to 192.168.100.1)
print("  Pinging local gateway (192.168.100.1)...")
_, ping_gw_out, _ = sh("sudo ip netns exec wifi-client ping -c 10 -i 0.2 192.168.100.1")
gw_rtt = "N/A"
for l in ping_gw_out.splitlines():
    if "rtt min/avg/max/mdev" in l:
        gw_rtt = l.split("=", 1)[-1].strip()

# Local Web UI HTTP latency
_, curl_http, _ = sh("sudo ip netns exec wifi-client curl -s -o /dev/null -w '%{time_total}\\n' http://192.168.100.1/login.asp")

# Remote Internet Ping (10 packets to 8.8.8.8)
print("  Pinging remote internet (8.8.8.8)...")
_, ping_rem_out, _ = sh("sudo ip netns exec wifi-client ping -c 10 -i 0.2 8.8.8.8")
rem_rtt = "N/A"
for l in ping_rem_out.splitlines():
    if "rtt min/avg/max/mdev" in l:
        rem_rtt = l.split("=", 1)[-1].strip()

# Remote Internet Download Throughput (10 MB via Cloudflare)
print("  Downloading 10 MB payload over Wi-Fi...")
rc_dl, dl_out, _ = sh("sudo ip netns exec wifi-client curl -o /dev/null -s -w '%{speed_download} %{time_total}\\n' https://speed.cloudflare.com/__down?bytes=10000000")

speed_wifi_bps = 0.0
time_wifi_s = 0.0
if rc_dl == 0 and dl_out:
    parts = dl_out.split()
    if len(parts) >= 2:
        speed_wifi_bps = float(parts[0])
        time_wifi_s = float(parts[1])

speed_wifi_mbps = (speed_wifi_bps * 8) / 1_000_000

# Remote Internet Upload Throughput (2 MB via Cloudflare)
print("  Uploading 2 MB payload over Wi-Fi...")
rc_ul, ul_out, _ = sh("sudo ip netns exec wifi-client curl -o /dev/null -s -w '%{speed_upload}\\n' -X POST --data-binary @/tmp/bench_payload.bin https://speed.cloudflare.com/__up")
speed_wifi_ul_mbps = (float(ul_out) * 8) / 1_000_000 if rc_ul == 0 and ul_out else 0.0

results["wifi"] = {
    "carrier": op,
    "rssi": rssi,
    "dbm": dbm,
    "wifi_sig": sig_wifi,
    "wifi_tx": tx_rate,
    "wifi_rx": rx_rate,
    "gw_rtt": gw_rtt,
    "rem_rtt": rem_rtt,
    "dl_mbps": speed_wifi_mbps,
    "dl_time": time_wifi_s,
    "ul_mbps": speed_wifi_ul_mbps,
    "http_ttfb": curl_http
}

# --- SECTION 2: Transition to USB Tethered Modem Mode ---
print("\n[2/3] Transitioning to USB Tethered Modem Mode (AT+WIFI=0 -> pppd)...")
t_trans0 = time.time()
sh("python3 bin/ufi-modem at 'AT+WIFI=0'")
time.sleep(1)
sh("sudo python3 bin/ufi-modem connect")
t_trans = time.time() - t_trans0

# Verify ppp0 UP
_, ppp_out, _ = sh("ip a show ppp0")
ppp_ip = "N/A"
for l in ppp_out.splitlines():
    if "inet " in l:
        ppp_ip = l.strip().split()[1]

print(f"  Connected ppp0 with IP: {ppp_ip} in {t_trans:.2f}s")

# --- SECTION 3: Benchmarking USB Tethered Modem Mode ---
print("\n[3/3] Benchmarking USB Tethered Modem Mode (ppp0)...")

# Remote Internet Ping (10 packets to 8.8.8.8 over ppp0)
print("  Pinging remote internet (8.8.8.8) over ppp0...")
_, ppp_ping_out, _ = sh("ping -I ppp0 -c 10 -i 0.2 8.8.8.8")
ppp_rem_rtt = "N/A"
for l in ppp_ping_out.splitlines():
    if "rtt min/avg/max/mdev" in l:
        ppp_rem_rtt = l.split("=", 1)[-1].strip()

# Remote Internet Download Throughput (10 MB via Cloudflare over ppp0)
print("  Downloading 10 MB payload over ppp0...")
rc_pdl, pdl_out, _ = sh("curl --interface ppp0 -o /dev/null -s -w '%{speed_download} %{time_total}\\n' https://speed.cloudflare.com/__down?bytes=10000000")
speed_ppp_bps = 0.0
time_ppp_s = 0.0
if rc_pdl == 0 and pdl_out:
    parts = pdl_out.split()
    if len(parts) >= 2:
        speed_ppp_bps = float(parts[0])
        time_ppp_s = float(parts[1])

speed_ppp_mbps = (speed_ppp_bps * 8) / 1_000_000

# Remote Internet Upload Throughput (2 MB via Cloudflare over ppp0)
print("  Uploading 2 MB payload over ppp0...")
rc_pul, pul_out, _ = sh("curl --interface ppp0 -o /dev/null -s -w '%{speed_upload}\\n' -X POST --data-binary @/tmp/bench_payload.bin https://speed.cloudflare.com/__up")
speed_ppp_ul_mbps = (float(pul_out) * 8) / 1_000_000 if rc_pul == 0 and pul_out else 0.0

results["ppp"] = {
    "carrier": op,
    "rssi": rssi,
    "dbm": dbm,
    "ip": ppp_ip,
    "rem_rtt": ppp_rem_rtt,
    "dl_mbps": speed_ppp_mbps,
    "dl_time": time_ppp_s,
    "ul_mbps": speed_ppp_ul_mbps,
    "trans_time": t_trans
}

# --- SUMMARY REPORT ---
print("\n" + "="*65)
print("                  BENCHMARK SUMMARY REPORT                       ")
print("="*65)
print(json.dumps(results, indent=2))

# Cleanup ppp0 & restore Wi-Fi
sh("sudo python3 bin/ufi-modem disconnect")
sh("python3 bin/ufi-modem at 'AT+WIFI=1'")
