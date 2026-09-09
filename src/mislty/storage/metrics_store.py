"""
mislty.storage.metrics_store
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Time-series telemetry recording and query engine for RF signal metrics and network bandwidth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional

from mislty.storage.database import DatabaseManager


@dataclass
class TelemetryRecord:
    """Represents a historical telemetry sample."""
    timestamp: float = field(default_factory=time.time)
    rssi: Optional[int] = None
    dbm: Optional[int] = None
    rat: Optional[str] = None
    lac: Optional[str] = None
    cell_id: Optional[str] = None
    tx_bytes: Optional[int] = None
    rx_bytes: Optional[int] = None
    tx_bps: Optional[float] = None
    rx_bps: Optional[float] = None

    def as_dict(self) -> Dict[str, Any]:
        """Serialize record to dictionary."""
        return {
            "timestamp": self.timestamp,
            "rssi": self.rssi,
            "dbm": self.dbm,
            "rat": self.rat,
            "lac": self.lac,
            "cell_id": self.cell_id,
            "tx_bytes": self.tx_bytes,
            "rx_bytes": self.rx_bytes,
            "tx_bps": self.tx_bps,
            "rx_bps": self.rx_bps,
        }


class MetricsStore:
    """
    Persistent store for radio frequency metrics and network usage statistics.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def record_metrics(self, record: TelemetryRecord) -> None:
        """Insert a telemetry sample into history."""
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO telemetry_history (timestamp, rssi, dbm, rat, lac, cell_id, tx_bytes, rx_bytes, tx_bps, rx_bps) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                (
                    record.timestamp,
                    record.rssi,
                    record.dbm,
                    record.rat,
                    record.lac,
                    record.cell_id,
                    record.tx_bytes,
                    record.rx_bytes,
                    record.tx_bps,
                    record.rx_bps,
                ),
            )

    def get_latest(self) -> Optional[TelemetryRecord]:
        """Retrieve the most recent telemetry sample."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, rssi, dbm, rat, lac, cell_id, tx_bytes, rx_bytes, tx_bps, rx_bps "
            "FROM telemetry_history ORDER BY timestamp DESC LIMIT 1;"
        )
        row = cursor.fetchone()
        if not row:
            return None

        return TelemetryRecord(
            timestamp=row["timestamp"],
            rssi=row["rssi"],
            dbm=row["dbm"],
            rat=row["rat"],
            lac=row["lac"],
            cell_id=row["cell_id"],
            tx_bytes=row["tx_bytes"],
            rx_bytes=row["rx_bytes"],
            tx_bps=row["tx_bps"],
            rx_bps=row["rx_bps"],
        )

    def get_recent(self, duration_seconds: float = 3600) -> List[TelemetryRecord]:
        """Retrieve telemetry samples within the last duration_seconds."""
        cutoff = time.time() - duration_seconds
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT timestamp, rssi, dbm, rat, lac, cell_id, tx_bytes, rx_bytes, tx_bps, rx_bps "
            "FROM telemetry_history WHERE timestamp >= ? ORDER BY timestamp ASC;",
            (cutoff,),
        )
        return [
            TelemetryRecord(
                timestamp=r["timestamp"],
                rssi=r["rssi"],
                dbm=r["dbm"],
                rat=r["rat"],
                lac=r["lac"],
                cell_id=r["cell_id"],
                tx_bytes=r["tx_bytes"],
                rx_bytes=r["rx_bytes"],
                tx_bps=r["tx_bps"],
                rx_bps=r["rx_bps"],
            )
            for r in cursor.fetchall()
        ]

    def prune_older_than(self, days: int = 7) -> int:
        """Prune telemetry history older than specified retention period."""
        cutoff = time.time() - (days * 86400)
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM telemetry_history WHERE timestamp < ?;", (cutoff,))
            return cursor.rowcount
