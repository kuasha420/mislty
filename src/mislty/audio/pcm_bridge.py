"""
mislty.audio.pcm_bridge
~~~~~~~~~~~~~~~~~~~~~~~

PipeWire PCM audio streaming bridge on MI_02 (/dev/mislty/voice),
ITU-T Q.23 DTMF tone synthesizer, and Telephony Call Engine with
the "Tragic Voice" CSFB network rejection handler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import math
from pathlib import Path
import re
import struct
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("mislty.audio")

# ITU-T Q.23 Standard DTMF Frequencies (Hz)
DTMF_FREQUENCIES: Dict[str, Tuple[float, float]] = {
    "1": (697.0, 1209.0),
    "2": (697.0, 1336.0),
    "3": (697.0, 1477.0),
    "A": (697.0, 1633.0),
    "4": (770.0, 1209.0),
    "5": (770.0, 1336.0),
    "6": (770.0, 1477.0),
    "B": (770.0, 1633.0),
    "7": (852.0, 1209.0),
    "8": (852.0, 1336.0),
    "9": (852.0, 1477.0),
    "C": (852.0, 1633.0),
    "*": (941.0, 1209.0),
    "0": (941.0, 1336.0),
    "#": (941.0, 1477.0),
    "D": (941.0, 1633.0),
}


def generate_dtmf_pcm(
    digit: str,
    duration_ms: int = 150,
    sample_rate: int = 8000,
    volume: float = 0.5,
) -> bytes:
    """
    Synthesize raw 16-bit linear PCM (signed little-endian, mono) DTMF audio tone.
    Uses standard dual-frequency sinusoidal superposition.
    """
    key = digit.upper()
    if key not in DTMF_FREQUENCIES:
        # Generate silence buffer if not a valid DTMF digit
        sample_count = int(sample_rate * (duration_ms / 1000.0))
        return b"\x00\x00" * sample_count

    f1, f2 = DTMF_FREQUENCIES[key]
    sample_count = int(sample_rate * (duration_ms / 1000.0))
    buffer = bytearray(sample_count * 2)

    omega1 = 2.0 * math.pi * f1 / sample_rate
    omega2 = 2.0 * math.pi * f2 / sample_rate
    max_amp = 32767.0 * max(0.0, min(1.0, volume))

    for i in range(sample_count):
        # Superposition of low-frequency and high-frequency sinusoids
        val = 0.5 * (math.sin(omega1 * i) + math.sin(omega2 * i)) * max_amp
        sample = int(max(-32768, min(32767, val)))
        struct.pack_into("<h", buffer, i * 2, sample)

    return bytes(buffer)


def play_pcm_buffer(pcm_data: bytes, sample_rate: int = 8000) -> bool:
    """
    Play a raw 16-bit linear mono PCM byte buffer via PipeWire (pw-cat)
    or fallback to paplay / aplay.
    """
    # 1. PipeWire pw-cat playback
    try:
        proc = subprocess.Popen(
            [
                "pw-cat",
                "-p",
                f"--rate={sample_rate}",
                "--channels=1",
                "--format=s16",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=pcm_data, timeout=2.0)
        return proc.returncode == 0
    except Exception:
        pass

    # 2. PulseAudio paplay fallback
    try:
        proc = subprocess.Popen(
            [
                "paplay",
                "--raw",
                f"--rate={sample_rate}",
                "--channels=1",
                "--format=s16le",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=pcm_data, timeout=2.0)
        return proc.returncode == 0
    except Exception:
        pass

    # 3. ALSA aplay fallback
    try:
        proc = subprocess.Popen(
            [
                "aplay",
                "-f", "S16_LE",
                "-r", str(sample_rate),
                "-c", "1",
                "-q",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        proc.communicate(input=pcm_data, timeout=2.0)
        return proc.returncode == 0
    except Exception:
        pass

    return False


def play_dtmf_tone(digit: str, duration_ms: int = 150) -> bool:
    """Synthesize and play DTMF tone asynchronously."""
    pcm = generate_dtmf_pcm(digit, duration_ms=duration_ms)

    def _worker():
        play_pcm_buffer(pcm, sample_rate=8000)

    threading.Thread(target=_worker, daemon=True).start()
    return True


# ---------------------------------------------------------------------------
# PipeWire PCM Audio Streaming Bridge
# ---------------------------------------------------------------------------

class PcmAudioBridge:
    """
    Bidirectional 8000 Hz, 16-bit linear PCM audio loopback bridge between
    Qualcomm MDM9600 MI_02 voice port and the Linux PipeWire audio server.
    """

    def __init__(self, voice_port: Optional[Path] = None, sample_rate: int = 8000) -> None:
        self.voice_port: Path = voice_port or Path("/dev/mislty/voice")
        self.sample_rate: int = sample_rate
        self.is_active: bool = False
        self._playback_proc: Optional[subprocess.Popen] = None
        self._record_proc: Optional[subprocess.Popen] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """Start bidirectional PCM streaming pipelines."""
        if self.is_active:
            return True

        if not self.voice_port.exists():
            logger.warning("Voice PCM port %s not found on host.", self.voice_port)
            return False

        self._stop_event.clear()
        self.is_active = True
        self._worker_thread = threading.Thread(target=self._stream_loop, daemon=True)
        self._worker_thread.start()
        logger.info("PipeWire PCM audio bridge started on %s (8000 Hz, S16_LE)", self.voice_port)
        return True

    def stop(self) -> None:
        """Terminate streaming audio pipelines."""
        self.is_active = False
        self._stop_event.set()

        if self._playback_proc:
            try:
                self._playback_proc.terminate()
            except Exception:
                pass
            self._playback_proc = None

        if self._record_proc:
            try:
                self._record_proc.terminate()
            except Exception:
                pass
            self._record_proc = None

        logger.info("PipeWire PCM audio bridge stopped.")

    def _stream_loop(self) -> None:
        """Background worker pumping PCM frames between voice serial port and PipeWire."""
        try:
            # Spawn PipeWire playback sink
            self._playback_proc = subprocess.Popen(
                [
                    "pw-cat",
                    "-p",
                    f"--rate={self.sample_rate}",
                    "--channels=1",
                    "--format=s16",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            # Open voice serial device in raw binary mode
            with open(self.voice_port, "rb+", buffering=0) as f_serial:
                while not self._stop_event.is_set():
                    data = f_serial.read(320)  # 20ms frame at 8000 Hz 16-bit
                    if data and self._playback_proc and self._playback_proc.stdin:
                        try:
                            self._playback_proc.stdin.write(data)
                            self._playback_proc.stdin.flush()
                        except (BrokenPipeError, OSError):
                            break
                    time.sleep(0.01)
        except Exception as exc:
            logger.debug("PCM streaming loop exited: %s", exc)
        finally:
            self.stop()


# ---------------------------------------------------------------------------
# Telephony Call Engine & "Tragic Voice" Lore Handler
# ---------------------------------------------------------------------------

@dataclass
class CallSession:
    """Represents an active or historic telephony call session."""
    number: str = ""
    state: str = "IDLE"  # IDLE, DIALING, ALERTING, CONNECTED, TERMINATED
    start_time: float = 0.0
    duration: int = 0
    error_code: Optional[str] = None
    is_tragic_voice: bool = False


TRAGIC_VOICE_LORE = {
    "title": "The Tragic Voice of MDM9600",
    "subtitle": "Circuit-Switched Fallback (CSFB) vs. The Pure-LTE Era",
    "narrative": (
        "In the golden era of 3G/HSPA+, Qualcomm MDM9600 was an engineering marvel. "
        "It featured a dedicated raw 8000 Hz, 16-bit linear PCM audio stream routed through USB Interface MI_02 "
        "(/dev/mislty/voice), allowing Linux computers to act as complete voice handsets.\n\n"
        "However, this portable dongle firmware lacks an IP Multimedia Subsystem (IMS) VoLTE stack. "
        "When you place a voice call today, the baseband requests Circuit-Switched Fallback (CSFB), "
        "asking the cellular tower to drop the connection back to 2G (GSM) or 3G (WCDMA).\n\n"
        "Across modern pure-LTE cellular networks (Grameenphone, Banglalink, Robi, Teletalk, and global carriers), "
        "3G has been decommissioned and legacy 2G is barred from CSFB handovers for data dongles. "
        "The carrier network core summarily refuses the fallback request, terminating the call with "
        "cause #31 (Normal, unspecified) or NO CARRIER.\n\n"
        "Your MisLTy audio bridge and feline dialer are fully functional, but the cellular world has moved on. "
        "The voice remains forever locked in silicon."
    ),
}


class TelephonyEngine:
    """
    Telephony session manager coordinating ATD dialing, ATH termination,
    PCM bridge activation, and CSFB rejection trapping.
    """

    def __init__(
        self,
        dispatcher: Optional[Any] = None,
        voice_port: Optional[Path] = None,
        on_state_change: Optional[Callable[[str, CallSession], None]] = None,
        on_tragic_voice: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.dispatcher = dispatcher
        self.voice_port: Path = voice_port or Path("/dev/mislty/voice")
        self.audio_bridge = PcmAudioBridge(voice_port=self.voice_port)
        self.current_call = CallSession()
        self.on_state_change = on_state_change
        self.on_tragic_voice = on_tragic_voice
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_stop = threading.Event()

    def dial(self, number: str) -> Dict[str, Any]:
        """
        Initiate an outbound voice call transaction (ATD<number>;).
        """
        clean_number = re.sub(r"[^\d+*#]", "", number.strip())
        if not clean_number:
            return {"success": False, "error": "Invalid phone number"}

        self.current_call = CallSession(
            number=clean_number,
            state="DIALING",
            start_time=time.time(),
            duration=0,
            is_tragic_voice=False,
        )
        self._notify_state_change()

        # Send DTMF chirp on dial start
        play_dtmf_tone(clean_number[0] if clean_number else "1", duration_ms=100)

        # Dispatch ATD command if dispatcher is available
        if self.dispatcher:
            cmd = f"ATD{clean_number};"
            resp = self.dispatcher.execute(cmd, timeout=5.0)
            if not resp.success:
                logger.warning("ATD failed: %s %s", resp.error, resp.lines)
                self._handle_csfb_rejection("ATD execution rejected by baseband")
                return {"success": False, "error": resp.error, "tragic_voice": True}

        # Start call progression monitor
        self._monitor_stop.clear()
        self._monitor_thread = threading.Thread(target=self._poll_call_progression, daemon=True)
        self._monitor_thread.start()

        return {"success": True, "state": "DIALING", "number": clean_number}

    def hangup(self) -> Dict[str, Any]:
        """
        Terminate any active or pending call session (ATH).
        """
        self._monitor_stop.set()
        self.audio_bridge.stop()

        if self.dispatcher:
            try:
                self.dispatcher.execute("ATH", timeout=3.0)
            except Exception:
                pass

        self.current_call.state = "TERMINATED"
        self._notify_state_change()

        # Reset to IDLE after brief termination notice
        def _reset():
            time.sleep(1.0)
            self.current_call = CallSession(state="IDLE")
            self._notify_state_change()

        threading.Thread(target=_reset, daemon=True).start()
        return {"success": True, "state": "IDLE"}

    def _poll_call_progression(self) -> None:
        """
        Monitor call status via AT+CLCC and trap CSFB rejection events.
        """
        dial_start = time.time()
        while not self._monitor_stop.is_set():
            time.sleep(1.0)

            # Update call duration
            if self.current_call.state in ("DIALING", "ALERTING", "CONNECTED"):
                self.current_call.duration = int(time.time() - self.current_call.start_time)
                self._notify_state_change()

            if not self.dispatcher:
                # In mock/offline mode, simulate CSFB rejection after 4 seconds
                if time.time() - dial_start >= 4.0:
                    self._handle_csfb_rejection("Pure-LTE CSFB Handover Refused (Simulated)")
                    break
                continue

            try:
                clcc = self.dispatcher.execute("AT+CLCC", timeout=2.0)
                if not clcc.lines:
                    # No active calls found in list! Check extended error
                    ceer = self.dispatcher.execute("AT+CEER", timeout=2.0)
                    reason = " ".join(ceer.lines) if ceer.lines else "NO CARRIER"
                    logger.info("Call disconnected or rejected: %s", reason)
                    self._handle_csfb_rejection(reason)
                    break

                # Parse CLCC state
                # Example: +CLCC: 1,0,2,0,0,"121",129
                line = clcc.lines[0]
                match = re.search(r"\+CLCC:\s*(\d+),(\d+),(\d+)", line)
                if match:
                    stat = int(match.group(3))
                    if stat == 0:  # Active
                        if self.current_call.state != "CONNECTED":
                            self.current_call.state = "CONNECTED"
                            self.audio_bridge.start()
                            self._notify_state_change()
                    elif stat == 3:  # Alerting
                        if self.current_call.state != "ALERTING":
                            self.current_call.state = "ALERTING"
                            self._notify_state_change()

                # If stuck in DIALING for over 8 seconds without alert, pure-LTE CSFB has stalled
                if self.current_call.state == "DIALING" and (time.time() - dial_start >= 8.0):
                    logger.info("Call stalled in DIALING state on pure-LTE carrier.")
                    self._handle_csfb_rejection("CSFB fallback stalled / timeout")
                    break

            except Exception as exc:
                logger.debug("CLCC monitor exception: %s", exc)
                break

    def _handle_csfb_rejection(self, reason: str) -> None:
        """Trigger Tragic Voice lore event when pure-LTE core rejects voice call."""
        self._monitor_stop.set()
        self.audio_bridge.stop()

        self.current_call.state = "TERMINATED"
        self.current_call.error_code = reason
        self.current_call.is_tragic_voice = True
        self._notify_state_change()

        event_data = {
            "title": TRAGIC_VOICE_LORE["title"],
            "subtitle": TRAGIC_VOICE_LORE["subtitle"],
            "number": self.current_call.number,
            "reason": reason,
            "narrative": TRAGIC_VOICE_LORE["narrative"],
            "timestamp": time.time(),
        }

        if self.on_tragic_voice:
            try:
                self.on_tragic_voice(event_data)
            except Exception as exc:
                logger.debug("on_tragic_voice callback failed: %s", exc)

    def _notify_state_change(self) -> None:
        """Dispatch state change callback."""
        if self.on_state_change:
            try:
                self.on_state_change(self.current_call.state, self.current_call)
            except Exception as exc:
                logger.debug("on_state_change callback failed: %s", exc)
