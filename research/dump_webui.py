#!/usr/bin/env python3
import urllib.request
import urllib.parse
import http.cookiejar
import os
import re

OUT_DIR = "research/webui_dump"
os.makedirs(OUT_DIR, exist_ok=True)

cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

# Login
login_data = urllib.parse.urlencode({"goformId": "LOGIN_NEW", "user": "admin", "psw": "admin"}).encode()
opener.open("http://192.168.100.1/goform/goform_process", data=login_data, timeout=3)

def fetch(path):
    clean_path = path.lstrip("/ ")
    url = f"http://192.168.100.1/{clean_path}"
    try:
        req = urllib.request.Request(url)
        with opener.open(req, timeout=3) as resp:
            if resp.status == 200:
                data = resp.read()
                out_path = os.path.join(OUT_DIR, clean_path)
                os.makedirs(os.path.dirname(out_path), exist_ok=True)
                with open(out_path, "wb") as f:
                    f.write(data)
                print(f"Downloaded: {clean_path} ({len(data)} bytes)")
                return data
    except Exception as e:
        pass
    return None

pages = [
    "index.html", "index.asp", "login.asp", "home.asp",
    "network_connect.asp", "reset_factory.asp", "dhcp_setting.asp", "update_password.asp",
    "connection_mode.asp", "network_select.asp", "apn_setting.asp",
    "wifi_profile.asp", "wifi_security.asp", "wifi_standby.asp", "station_list.asp",
    "data_statistics.asp", "basic_status.asp", "network_status.asp",
    "help_en.html", "help_cn.html", "help_tw.html",
    "favicon.ico", "xml/apn_list.xml"
]

downloaded = set()
for p in pages:
    data = fetch(p)
    if data:
        downloaded.add(p)

names = [p.replace(".asp", "").replace(".html", "") for p in pages if ".asp" in p or ".html" in p]
for l in ["en", "cn", "tw"]:
    for n in names:
        fetch(f"lang/{l}/{n}.xml")

for root, _, files in os.walk(OUT_DIR):
    for f in files:
        if f.endswith((".asp", ".html", ".css", ".js")):
            filepath = os.path.join(root, f)
            with open(filepath, "r", errors="ignore") as fp:
                content = fp.read()
                links = re.findall(r"['\"](res/[^'\"\s>]+)['\"]", content)
                for link in links:
                    if link not in downloaded:
                        fetch(link)
                        downloaded.add(link)

print("Dump complete!")
