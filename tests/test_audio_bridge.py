"""
tests.test_audio_bridge
~~~~~~~~~~~~~~~~~~~~~~~

Unit tests for PipeWire PCM Audio Bridge, ITU-T Q.23 DTMF synthesis,
and TelephonyCallEngine with CSFB Tragic Voice rejection handling.
"""

from __future__ import annotations

import struct
from unittest.mock import MagicMock, patch
import pytest

from mislty.audio.pcm_bridge import (
    DTMF_FREQUENCIES,
    CallSession,
    PcmAudioBridge,
    TelephonyEngine,
    generate_dtmf_pcm,
    play_dtmf_tone,
    play_pcm_buffer,
)
from mislty.core.at_parser import AtResponse


# ---------------------------------------------------------------------------
# DTMF Synthesis Tests
# ---------------------------------------------------------------------------

def test_dtmf_pcm_generation_structure():
    """Verify 8000 Hz 16-bit linear PCM byte buffer generation for valid DTMF digits."""
    # 150 ms tone at 8000 Hz = 1200 samples = 2400 bytes
    pcm = generate_dtmf_pcm("5", duration_ms=150, sample_rate=8000, volume=0.5)
    assert isinstance(pcm, bytes)
    assert len(pcm) == 2400

    # Unpack samples to verify range and non-silence
    samples = struct.unpack(f"<{len(pcm)//2}h", pcm)
    assert len(samples) == 1200
    assert max(samples) > 1000
    assert min(samples) < -1000
    assert max(samples) <= 32767
    assert min(samples) >= -32768


def test_dtmf_pcm_all_keypad_digits():
    """Verify all 16 ITU-T standard DTMF symbols generate valid buffers."""
    for key in DTMF_FREQUENCIES:
        pcm = generate_dtmf_pcm(key, duration_ms=50, sample_rate=8000)
        assert len(pcm) == 800


def test_dtmf_pcm_invalid_digit_silence():
    """Verify invalid symbols generate zero-filled silence buffer."""
    pcm = generate_dtmf_pcm("Z", duration_ms=100, sample_rate=8000)
    assert len(pcm) == 1600
    assert pcm == b"\x00" * 1600


# ---------------------------------------------------------------------------
# Audio Server Playback Tests
# ---------------------------------------------------------------------------

def test_play_pcm_buffer_pipewire():
    """Verify pw-cat invocation for PCM playback."""
    pcm = b"\x00" * 320
    with patch("subprocess.Popen") as mock_popen:
        proc = MagicMock()
        proc.communicate.return_value = (b"", b"")
        proc.returncode = 0
        mock_popen.return_value = proc

        ok = play_pcm_buffer(pcm, sample_rate=8000)
        assert ok is True
        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "pw-cat" in cmd
        assert "--rate=8000" in cmd


def test_play_dtmf_tone_thread():
    """Verify play_dtmf_tone runs without blocking."""
    with patch("mislty.audio.pcm_bridge.play_pcm_buffer") as mock_play:
        mock_play.return_value = True
        ok = play_dtmf_tone("9", duration_ms=50)
        assert ok is True


# ---------------------------------------------------------------------------
# Telephony Call Engine & CSFB Trap Tests
# ---------------------------------------------------------------------------

def test_telephony_engine_dial_and_hangup(tmp_path):
    """Verify call session state progression from IDLE to DIALING and TERMINATED."""
    mock_disp = MagicMock()
    mock_disp.execute.return_value = AtResponse(command="ATD121;", success=True, lines=[], raw_text="OK")

    state_history = []

    def on_state(state, session):
        state_history.append((state, session.number))

    voice_file = tmp_path / "voice"
    voice_file.write_bytes(b"")

    engine = TelephonyEngine(dispatcher=mock_disp, voice_port=voice_file, on_state_change=on_state)
    assert engine.current_call.state == "IDLE"

    # Dial
    res = engine.dial("+8801712345678")
    assert res["success"] is True
    assert res["number"] == "+8801712345678"
    assert engine.current_call.state == "DIALING"
    mock_disp.execute.assert_any_call("ATD+8801712345678;", timeout=5.0)

    # Hangup
    hang_res = engine.hangup()
    assert hang_res["success"] is True
    mock_disp.execute.assert_any_call("ATH", timeout=3.0)


def test_telephony_engine_csfb_rejection_trap(tmp_path):
    """Verify CSFB rejection on pure-LTE carrier triggers Tragic Voice lore event."""
    mock_disp = MagicMock()
    # ATD succeeds, but subsequent CLCC returns empty and CEER shows NO CARRIER
    mock_disp.execute.side_effect = [
        AtResponse(command="ATD121;", success=True, lines=[], raw_text="OK"),
        AtResponse(command="AT+CLCC", success=True, lines=[], raw_text="OK"),  # Call dropped
        AtResponse(command="AT+CEER", success=True, lines=["+CEER: 31 (Normal, unspecified)"], raw_text="OK"),
    ]

    tragic_events = []

    def on_tragic(event):
        tragic_events.append(event)

    voice_file = tmp_path / "voice"
    voice_file.write_bytes(b"")

    engine = TelephonyEngine(
        dispatcher=mock_disp,
        voice_port=voice_file,
        on_tragic_voice=on_tragic,
    )

    engine.dial("121")

    # Force synchronous progression poll
    engine._poll_call_progression()

    assert len(tragic_events) == 1
    event = tragic_events[0]
    assert "Tragic Voice" in event["title"]
    assert "31" in event["reason"]
    assert engine.current_call.is_tragic_voice is True
