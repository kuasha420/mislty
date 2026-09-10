"""
mislty.core.sms
~~~~~~~~~~~~~~~

Standards-compliant 3GPP TS 23.038 / GSM 03.38 SMS character encoding,
multi-part segment calculation, and Freedesktop desktop notifications.
"""

from __future__ import annotations

import logging
import math
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger("mislty.sms")

# 3GPP TS 23.038 standard GSM 7-bit basic character set
GSM7_BASIC_CHARS = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ"
    " !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿"
    "abcdefghijklmnopqrstuvwxyzäöñüà\t\f"
)

# GSM 7-bit extended character set (escaped by 0x1B, costs 2 septets per char)
GSM7_EXTENDED_CHARS = set("^{}\\[~]|€")


def is_gsm7(text: str) -> bool:
    """
    Check whether all characters in the string belong to the standard
    GSM 7-bit default alphabet or extension table.
    """
    for char in text:
        if char not in GSM7_BASIC_CHARS and char not in GSM7_EXTENDED_CHARS:
            return False
    return True


def count_gsm7_septets(text: str) -> int:
    """
    Calculate the total number of septets required to encode the string in GSM-7.
    Characters in the basic table count as 1; characters in the extension table
    require an ESC prefix and count as 2 septets.
    """
    count = 0
    for char in text:
        if char in GSM7_EXTENDED_CHARS:
            count += 2
        else:
            count += 1
    return count


def calculate_sms_segments(text: str) -> Dict[str, Any]:
    """
    Calculate SMS character usage, multi-part concatenation segments, and encoding.

    Standard rules:
    - GSM-7:
        Single message: <= 160 characters (basic=1, ext=2)
        Concatenated: 153 characters per segment (7 septets for UDH)
    - UCS-2 (Unicode):
        Single message: <= 70 UTF-16 code units
        Concatenated: 67 UTF-16 code units per segment (3 code units for UDH)
    """
    if not text:
        return {
            "encoding": "GSM-7",
            "chars_count": 0,
            "segments": 0,
            "max_per_segment": 160,
            "chars_left_in_segment": 160,
            "is_unicode": False,
            "summary": "0/160 (0 SMS)",
        }

    fits_gsm = is_gsm7(text)

    if fits_gsm:
        encoding = "GSM-7"
        is_unicode = False
        count = count_gsm7_septets(text)

        if count <= 160:
            segments = 1
            max_per_segment = 160
            chars_left = 160 - count
        else:
            max_per_segment = 153
            segments = math.ceil(count / 153)
            remainder = count % 153
            chars_left = (153 - remainder) if remainder != 0 else 0
    else:
        encoding = "UCS-2"
        is_unicode = True
        # UTF-16 code units count (surrogate pairs count as 2)
        count = len(text.encode("utf-16-be")) // 2

        if count <= 70:
            segments = 1
            max_per_segment = 70
            chars_left = 70 - count
        else:
            max_per_segment = 67
            segments = math.ceil(count / 67)
            remainder = count % 67
            chars_left = (67 - remainder) if remainder != 0 else 0

    encoding_label = " Unicode" if is_unicode else ""
    summary = f"{count}/{max_per_segment} ({segments} SMS{encoding_label})"

    return {
        "encoding": encoding,
        "chars_count": count,
        "segments": segments,
        "max_per_segment": max_per_segment,
        "chars_left_in_segment": chars_left,
        "is_unicode": is_unicode,
        "summary": summary,
    }


def send_desktop_notification(
    title: str,
    message: str,
    app_name: str = "MisLTy",
    icon: str = "mail-unread",
    timeout_ms: int = 5000,
) -> bool:
    """
    Dispatch a Freedesktop desktop notification to the user's notification daemon.
    Tries direct D-Bus invocation on org.freedesktop.Notifications first,
    falling back to notify-send CLI.
    """
    # 1. Try D-Bus org.freedesktop.Notifications
    try:
        import dbus
        bus = dbus.SessionBus()
        notify_obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
        notify_iface = dbus.Interface(notify_obj, "org.freedesktop.Notifications")
        notify_iface.Notify(
            app_name,
            dbus.UInt32(0),
            icon,
            title,
            message,
            dbus.Array([], signature="s"),
            dbus.Dictionary({}, signature="sv"),
            dbus.Int32(timeout_ms),
        )
        logger.debug("Desktop notification sent via D-Bus: %s - %s", title, message)
        return True
    except Exception as exc:
        logger.debug("D-Bus notification failed: %s, trying notify-send", exc)

    # 2. Try notify-send executable
    try:
        res = subprocess.run(
            [
                "notify-send",
                "-a", app_name,
                "-i", icon,
                "-t", str(timeout_ms),
                title,
                message,
            ],
            capture_output=True,
            timeout=2.0,
            check=False,
        )
        return res.returncode == 0
    except Exception as exc:
        logger.debug("notify-send failed: %s", exc)
        return False
