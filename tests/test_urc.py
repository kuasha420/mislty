"""
Unit and integration tests for mislty.core.urc_demuxer.
"""

import os
import pty
import threading
import time
import pytest

from mislty.core.urc_demuxer import (
    UrcDemuxer,
    UrcEvent,
    SmsReceivedEvent,
    IncomingCallEvent,
    CallTerminatedEvent,
    NetworkRegistrationEvent,
    ModeChangeEvent,
    SignalChangeEvent,
    RawUrcEvent,
)
from mislty.core.serial_transport import SerialTransport
from mislty.core.at_parser import AtDispatcher


def test_urc_sms_parsing():
    """Verify parsing of incoming SMS notification URCs."""
    demuxer = UrcDemuxer()
    evt1 = demuxer.parse_line('+CMTI: "SM", 5')
    assert isinstance(evt1, SmsReceivedEvent)
    assert evt1.storage == "SM"
    assert evt1.index == 5

    evt2 = demuxer.parse_line('+CMTI: "ME", 12')
    assert isinstance(evt2, SmsReceivedEvent)
    assert evt2.storage == "ME"
    assert evt2.index == 12


def test_urc_call_events():
    """Verify parsing of incoming call, caller ID, and termination URCs."""
    demuxer = UrcDemuxer()

    ring_evt = demuxer.parse_line("RING")
    assert isinstance(ring_evt, IncomingCallEvent)
    assert ring_evt.caller_id is None

    clip_evt = demuxer.parse_line('+CLIP: "+8801712345678", 145')
    assert isinstance(clip_evt, IncomingCallEvent)
    assert clip_evt.caller_id == "+8801712345678"
    assert clip_evt.number_type == 145

    term1 = demuxer.parse_line("NO CARRIER")
    assert isinstance(term1, CallTerminatedEvent)
    assert term1.reason == "NO CARRIER"

    term2 = demuxer.parse_line("BUSY")
    assert isinstance(term2, CallTerminatedEvent)
    assert term2.reason == "BUSY"


def test_urc_network_registration():
    """Verify parsing of +CREG, +CGREG, and +CEREG registration transitions."""
    demuxer = UrcDemuxer()

    creg_evt = demuxer.parse_line("+CREG: 1")
    assert isinstance(creg_evt, NetworkRegistrationEvent)
    assert creg_evt.domain == "CS"
    assert creg_evt.status == 1
    assert creg_evt.is_registered is True
    assert creg_evt.is_roaming is False

    cereg_evt = demuxer.parse_line('+CEREG: 2, 5, "1234", "5678", 7')
    assert isinstance(cereg_evt, NetworkRegistrationEvent)
    assert cereg_evt.domain == "EPS"
    assert cereg_evt.status == 5
    assert cereg_evt.is_registered is True
    assert cereg_evt.is_roaming is True
    assert cereg_evt.lac == "1234"
    assert cereg_evt.ci == "5678"
    assert cereg_evt.act == 7


def test_urc_mode_and_signal():
    """Verify parsing of Qualcomm ^MODE and ^RSSI indications."""
    demuxer = UrcDemuxer()

    mode_evt = demuxer.parse_line("^MODE: 8, 1")
    assert isinstance(mode_evt, ModeChangeEvent)
    assert mode_evt.mode == 8
    assert mode_evt.technology == "LTE"

    rssi_full = demuxer.parse_line("^RSSI: 31")
    assert isinstance(rssi_full, SignalChangeEvent)
    assert rssi_full.rssi == 31
    assert rssi_full.bars == 5
    assert rssi_full.dbm == -51

    rssi_weak = demuxer.parse_line("^RSSI: 8")
    assert isinstance(rssi_weak, SignalChangeEvent)
    assert rssi_weak.rssi == 8
    assert rssi_weak.bars == 1
    assert rssi_weak.dbm == -97


def test_pub_sub_subscriptions():
    """Verify typed and global subscriptions and unsubscriptions."""
    demuxer = UrcDemuxer()
    sms_events = []
    all_events = []

    unsub_sms = demuxer.subscribe(SmsReceivedEvent, lambda e: sms_events.append(e))
    unsub_all = demuxer.subscribe_all(lambda e: all_events.append(e))

    # Trigger events
    demuxer.feed_line('+CMTI: "SM", 1')
    demuxer.feed_line('^RSSI: 20')

    assert len(sms_events) == 1
    assert sms_events[0].index == 1
    assert len(all_events) == 2

    # Unsubscribe and verify no new events delivered to SMS subscriber
    unsub_sms()
    demuxer.feed_line('+CMTI: "SM", 2')

    assert len(sms_events) == 1
    assert len(all_events) == 3

    unsub_all()


def test_fault_tolerant_subscriber():
    """Verify that a failing subscriber does not halt other subscribers."""
    demuxer = UrcDemuxer()
    successful_runs = []

    def bad_subscriber(evt):
        raise RuntimeError("Intentional test fault in subscriber")

    def good_subscriber(evt):
        successful_runs.append(evt)

    demuxer.subscribe(SignalChangeEvent, bad_subscriber)
    demuxer.subscribe(SignalChangeEvent, good_subscriber)

    # Should not raise exception
    demuxer.feed_line("^RSSI: 25")
    assert len(successful_runs) == 1
    assert successful_runs[0].rssi == 25


def test_background_listener_pty():
    """Verify background listener thread captures URCs asynchronously on a PTY."""
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    try:
        transport = SerialTransport(slave_name, baudrate=115200, timeout=0.1, exclusive_lock=False)
        transport.open()

        demuxer = UrcDemuxer()
        received = []
        event_arrived = threading.Event()

        def on_event(evt):
            received.append(evt)
            event_arrived.set()

        demuxer.subscribe(SmsReceivedEvent, on_event)
        demuxer.start_listener(transport, poll_interval=0.02)

        # Write URC to master end of PTY
        os.write(master_fd, b'+CMTI: "SM", 99\r\n')

        # Wait for delivery
        assert event_arrived.wait(timeout=2.0) is True
        assert len(received) == 1
        assert received[0].index == 99

        demuxer.stop_listener()
        transport.close()
    finally:
        os.close(master_fd)
        os.close(slave_fd)


def test_interleaved_urc_with_at_dispatcher():
    """Verify that AtDispatcher routes interleaved URCs directly into UrcDemuxer."""
    master_fd, slave_fd = pty.openpty()
    slave_name = os.ttyname(slave_fd)

    try:
        transport = SerialTransport(slave_name, baudrate=115200, timeout=1.0, exclusive_lock=False)
        demuxer = UrcDemuxer()
        sms_events = []
        demuxer.subscribe(SmsReceivedEvent, lambda e: sms_events.append(e))

        dispatcher = AtDispatcher(transport, urc_callback=demuxer.feed_line)
        transport.open()

        # In a separate thread, simulate modem responding to AT+CSQ with an interleaved +CMTI URC
        def modem_reply():
            # Read command from master
            time.sleep(0.05)
            cmd = os.read(master_fd, 1024)
            # Reply with command echo, interleaved URC, result line, and OK
            reply = b"AT+CSQ\r\n+CMTI: \"SM\", 7\r\n+CSQ: 29,99\r\nOK\r\n"
            os.write(master_fd, reply)

        t = threading.Thread(target=modem_reply, daemon=True)
        t.start()

        resp = dispatcher.execute("AT+CSQ", timeout=1.0)
        t.join(timeout=1.0)

        assert resp.success is True
        assert resp.lines == ["+CSQ: 29,99"]
        assert len(sms_events) == 1
        assert sms_events[0].index == 7
        assert sms_events[0].storage == "SM"

        transport.close()
    finally:
        os.close(master_fd)
        os.close(slave_fd)

