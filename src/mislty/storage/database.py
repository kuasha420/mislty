"""
mislty.storage.database
~~~~~~~~~~~~~~~~~~~~~~~

SQLite storage engine with Write-Ahead Logging (WAL) and automated forward schema migrations.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import threading
from typing import Generator, Optional, Union


DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "mislty" / "mislty.db"

CURRENT_SCHEMA_VERSION = 1

SCHEMA_V1 = """
-- Schema Version 1: Core SMS, Contacts, Threads, and Telemetry

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS threads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_number TEXT NOT NULL UNIQUE,
    contact_name TEXT,
    snippet TEXT,
    unread_count INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    thread_id INTEGER NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK(direction IN ('IN', 'OUT')),
    phone_number TEXT NOT NULL,
    body TEXT NOT NULL,
    timestamp REAL NOT NULL,
    sim_index INTEGER,
    status TEXT NOT NULL DEFAULT 'DELIVERED',
    is_read INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS telemetry_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    rssi INTEGER,
    dbm INTEGER,
    rat TEXT,
    lac TEXT,
    cell_id TEXT,
    tx_bytes INTEGER,
    rx_bytes INTEGER,
    tx_bps REAL,
    rx_bps REAL
);

-- Indexes for lightning fast lookups
CREATE INDEX IF NOT EXISTS idx_messages_thread ON messages(thread_id);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
CREATE INDEX IF NOT EXISTS idx_threads_updated ON threads(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry_history(timestamp DESC);
"""


class DatabaseManager:
    """
    Thread-safe SQLite database manager configuring WAL mode and automated migrations.
    """

    def __init__(self, db_path: Optional[Union[str, Path]] = None) -> None:
        if db_path is None or str(db_path) == "":
            self.db_path = DEFAULT_DB_PATH
        elif str(db_path) == ":memory:":
            self.db_path = Path(":memory:")
        else:
            self.db_path = Path(db_path)

        self._is_memory = str(self.db_path) == ":memory:"
        self._local = threading.local()
        self._init_lock = threading.Lock()
        self._migrated = False

        if not self._is_memory:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.migrate()

    def get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local SQLite connection configured with WAL and busy timeout.
        """
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=10.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row

            # Apply performance PRAGMAs
            cursor = conn.cursor()
            if not self._is_memory:
                cursor.execute("PRAGMA journal_mode = WAL;")
            cursor.execute("PRAGMA synchronous = NORMAL;")
            cursor.execute("PRAGMA foreign_keys = ON;")
            cursor.execute("PRAGMA busy_timeout = 5000;")
            cursor.close()

            self._local.conn = conn

        return conn

    def migrate(self) -> None:
        """
        Apply pending schema migrations up to CURRENT_SCHEMA_VERSION.
        """
        with self._init_lock:
            if self._migrated and not self._is_memory:
                return

            conn = self.get_connection()
            with conn:
                cursor = conn.cursor()
                cursor.execute(
                    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY, applied_at REAL NOT NULL);"
                )
                cursor.execute("SELECT MAX(version) FROM schema_version;")
                row = cursor.fetchone()
                current_ver = row[0] if row and row[0] is not None else 0

                if current_ver < 1:
                    cursor.executescript(SCHEMA_V1)
                    cursor.execute(
                        "INSERT OR REPLACE INTO schema_version (version, applied_at) VALUES (1, strftime('%s', 'now'));"
                    )

                self._migrated = True

    def close(self) -> None:
        """Close connection for current thread."""
        conn = getattr(self._local, "conn", None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error:
                pass
            self._local.conn = None
