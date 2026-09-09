"""
Unit tests for mislty.storage (DatabaseManager, SmsStore, MetricsStore).
"""

from pathlib import Path
import time
import pytest

from mislty.storage.database import DatabaseManager
from mislty.storage.sms_store import SmsStore, SmsMessage, SmsThread, normalize_phone_number
from mislty.storage.metrics_store import MetricsStore, TelemetryRecord
from mislty.core.at_parser import AtResponse


class MockAtDispatcher:
    """Mock dispatcher for SIM reconciliation testing."""

    def __init__(self, cmgl_lines: list[str]) -> None:
        self.cmgl_lines = cmgl_lines
        self.commands_executed: list[str] = []

    def execute(self, cmd, timeout=None):
        cmd_str = cmd.command if hasattr(cmd, "command") else str(cmd)
        self.commands_executed.append(cmd_str)

        if cmd_str == 'AT+CMGL="ALL"':
            return AtResponse(
                command=cmd_str,
                success=True,
                lines=self.cmgl_lines,
                raw_text="\n".join(self.cmgl_lines),
            )
        elif cmd_str.startswith("AT+CMGD="):
            return AtResponse(
                command=cmd_str,
                success=True,
                lines=[],
                raw_text="OK",
            )
        return AtResponse(
            command=cmd_str,
            success=True,
            lines=[],
            raw_text="OK",
        )


def test_database_manager_memory():
    """Verify in-memory database creation and automatic migrations."""
    db = DatabaseManager(":memory:")
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_version;")
    assert cursor.fetchone()[0] == 1


def test_database_manager_file_wal(tmp_path):
    """Verify file-based SQLite runs in WAL mode."""
    db_file = tmp_path / "test.db"
    db = DatabaseManager(db_file)
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0].lower()
    assert mode == "wal"
    db.close()


def test_sms_thread_and_message_crud():
    """Verify SMS thread grouping, message insertion, and unread accounting."""
    db = DatabaseManager(":memory:")
    sms = SmsStore(db)

    # 1. Normalize numbers
    t1 = sms.get_or_create_thread("+880 171-234 5678", contact_name="Alice")
    t2 = sms.get_or_create_thread("+8801712345678")
    assert t1.id == t2.id
    assert t2.contact_name == "Alice"

    # 2. Save inbound message
    m1 = sms.save_message(
        direction="IN",
        phone_number="+8801712345678",
        body="Hello from Alice!",
    )
    assert m1.thread_id == t1.id
    assert m1.direction == "IN"
    assert m1.is_read is False

    # Check thread updated
    threads = sms.list_threads()
    assert len(threads) == 1
    assert threads[0].unread_count == 1
    assert threads[0].snippet == "Hello from Alice!"

    # 3. Save outbound reply
    m2 = sms.save_message(
        direction="OUT",
        phone_number="+8801712345678",
        body="Hey Alice, reply back.",
    )
    assert m2.direction == "OUT"

    # Outbound shouldn't increment unread count
    threads = sms.list_threads()
    assert threads[0].unread_count == 1

    # 4. Get thread messages
    msgs = sms.get_thread_messages(t1.id)
    assert len(msgs) == 2
    assert msgs[0].body == "Hello from Alice!"
    assert msgs[1].body == "Hey Alice, reply back."

    # 5. Mark thread read
    sms.mark_thread_read(t1.id)
    threads = sms.list_threads()
    assert threads[0].unread_count == 0

    # 6. Delete message and thread
    assert sms.delete_message(m1.id) is True
    assert len(sms.get_thread_messages(t1.id)) == 1
    assert sms.delete_thread(t1.id) is True
    assert len(sms.list_threads()) == 0


def test_sim_inbox_reconciliation():
    """Verify parsing and reconciliation of messages from SIM storage."""
    db = DatabaseManager(":memory:")
    sms = SmsStore(db)

    sim_cmgl_output = [
        '+CMGL: 1,"REC READ","+8801700000001",,"26/09/01,12:00:00+24"',
        "Sim message one content",
        '+CMGL: 2,"REC UNREAD","+8801700000002",,"26/09/02,14:30:00+24"',
        "Sim message two content line 1",
        "Sim message two content line 2",
    ]

    mock_disp = MockAtDispatcher(sim_cmgl_output)
    ingested = sms.reconcile_sim_inbox(mock_disp, purge_sim=True)

    assert len(ingested) == 2
    assert ingested[0].phone_number == "+8801700000001"
    assert ingested[0].body == "Sim message one content"
    assert ingested[0].sim_index == 1

    assert ingested[1].phone_number == "+8801700000002"
    assert "Sim message two content line 1\nSim message two content line 2" == ingested[1].body
    assert ingested[1].sim_index == 2

    # Verify AT+CMGD was executed for index 1 and 2
    assert "AT+CMGD=1" in mock_disp.commands_executed
    assert "AT+CMGD=2" in mock_disp.commands_executed

    # Re-running reconciliation shouldn't duplicate
    re_ingested = sms.reconcile_sim_inbox(mock_disp, purge_sim=False)
    assert len(re_ingested) == 0


def test_metrics_store():
    """Verify TelemetryRecord storage, latest retrieval, and pruning."""
    db = DatabaseManager(":memory:")
    store = MetricsStore(db)

    now = time.time()
    store.record_metrics(
        TelemetryRecord(
            timestamp=now - 100,
            rssi=20,
            dbm=-73,
            rat="LTE",
            lac="1A2B",
            cell_id="3C4D",
            tx_bytes=1000,
            rx_bytes=5000,
            tx_bps=120.5,
            rx_bps=850.0,
        )
    )

    store.record_metrics(
        TelemetryRecord(
            timestamp=now,
            rssi=30,
            dbm=-53,
            rat="LTE",
            lac="1A2B",
            cell_id="3C4D",
            tx_bytes=2000,
            rx_bytes=10000,
            tx_bps=250.0,
            rx_bps=1500.0,
        )
    )

    latest = store.get_latest()
    assert latest is not None
    assert latest.rssi == 30
    assert latest.dbm == -53

    recent = store.get_recent(duration_seconds=300)
    assert len(recent) == 2

    # Pruning
    pruned = store.prune_older_than(days=1)
    assert pruned == 0  # None older than 1 day
