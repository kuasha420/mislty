"""
Unit and integration tests for mislty.core.daemon (DaemonEngine).
"""

import time
import pytest

from mislty.core.daemon import DaemonEngine, DaemonState
from mislty.core.urc_demuxer import SignalChangeEvent, ModeChangeEvent, SysinfoEvent, NetworkRegistrationEvent


def test_daemon_state_defaults():
    """Verify DaemonState serialization and initial values."""
    state = DaemonState()
    assert state.is_running is False
    assert state.connected is False
    assert state.rssi == 0
    assert state.bars == 0
    assert state.technology == "SEARCHING"
    d = state.as_dict()
    assert d["is_running"] is False
    assert d["technology"] == "SEARCHING"


def test_daemon_urc_integration():
    """Verify that URC events automatically update DaemonEngine state."""
    engine = DaemonEngine(db_path=":memory:", poll_interval=10.0)

    # Trigger signal URC
    engine.demuxer.feed_line("^RSSI: 28")
    assert engine.state.rssi == 28
    assert engine.state.bars == 5
    assert engine.state.dbm == -57

    # Trigger sysinfo URC
    engine.demuxer.feed_line("^SYSINFO: 2,3,0,8,1,,0")
    assert engine.state.technology == "LTE"

    # Trigger network registration URC
    engine.demuxer.feed_line("+CREG: 1")
    assert engine.state.registration_status == 1

    engine.stop()


@pytest.mark.hardware
def test_daemon_live_lifecycle():
    """Verify live DaemonEngine connection, telemetry polling, and clean shutdown."""
    engine = DaemonEngine(db_path=":memory:", poll_interval=1.0)
    engine.start()

    assert engine.state.is_running is True

    # Allow 2.5 seconds for at least one telemetry poll cycle
    time.sleep(2.5)

    if engine.state.connected:
        assert engine.state.rssi > 0
        assert engine.state.carrier is not None
        assert engine.state.last_poll_time > 0

        latest = engine.metrics_store.get_latest()
        assert latest is not None
        assert latest.rssi == engine.state.rssi

    engine.stop()
    assert engine.state.is_running is False
    assert engine.state.connected is False
