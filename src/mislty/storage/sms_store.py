"""
mislty.storage.sms_store
~~~~~~~~~~~~~~~~~~~~~~~~

Threaded SMS conversation repository and automated SIM storage reconciliation engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from mislty.storage.database import DatabaseManager
from mislty.core.at_parser import AtCommand, AtDispatcher, AtResponse

logger = logging.getLogger("mislty.sms")


@dataclass
class SmsMessage:
    """Represents an individual SMS message in a conversation thread."""
    id: Optional[int] = None
    thread_id: int = 0
    direction: str = "IN"  # "IN" or "OUT"
    phone_number: str = ""
    body: str = ""
    timestamp: float = field(default_factory=time.time)
    sim_index: Optional[int] = None
    status: str = "DELIVERED"
    is_read: bool = False

    def as_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary."""
        return {
            "id": self.id,
            "thread_id": self.thread_id,
            "direction": self.direction,
            "phone_number": self.phone_number,
            "body": self.body,
            "timestamp": self.timestamp,
            "sim_index": self.sim_index,
            "status": self.status,
            "is_read": self.is_read,
        }


@dataclass
class SmsThread:
    """Represents a conversational thread grouped by phone number."""
    id: int
    recipient_number: str
    contact_name: Optional[str] = None
    snippet: str = ""
    unread_count: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def as_dict(self) -> Dict[str, Any]:
        """Serialize thread to dictionary."""
        return {
            "id": self.id,
            "recipient_number": self.recipient_number,
            "contact_name": self.contact_name,
            "snippet": self.snippet,
            "unread_count": self.unread_count,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def normalize_phone_number(number: str) -> str:
    """Normalize phone number by removing spaces, hyphens, and parentheses."""
    cleaned = re.sub(r"[^\d+]", "", number.strip())
    return cleaned if cleaned else number.strip()


def parse_sim_timestamp(date_str: str) -> float:
    """
    Parse 3GPP AT+CMGL timestamp (format: 'YY/MM/DD,HH:MM:SS+ZZ').
    Falls back to current time on parse failure.
    """
    try:
        # e.g. "26/09/05,15:32:15+24"
        parts = date_str.split("+")[0].split("-")[0]
        dt = datetime.strptime(parts, "%y/%m/%d,%H:%M:%S")
        return dt.replace(tzinfo=timezone.utc).timestamp()
    except Exception:
        return time.time()


class SmsStore:
    """
    Conversational SMS repository and SIM memory reconciliation manager.
    """

    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def get_or_create_thread(
        self,
        phone_number: str,
        contact_name: Optional[str] = None,
    ) -> SmsThread:
        """
        Retrieve existing thread for phone number or create a new thread.
        """
        clean_number = normalize_phone_number(phone_number)
        conn = self.db.get_connection()

        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, recipient_number, contact_name, snippet, unread_count, created_at, updated_at "
                "FROM threads WHERE recipient_number = ?;",
                (clean_number,),
            )
            row = cursor.fetchone()

            if row:
                thread = SmsThread(
                    id=row["id"],
                    recipient_number=row["recipient_number"],
                    contact_name=row["contact_name"],
                    snippet=row["snippet"] or "",
                    unread_count=row["unread_count"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                if contact_name and contact_name != thread.contact_name:
                    cursor.execute(
                        "UPDATE threads SET contact_name = ? WHERE id = ?;",
                        (contact_name, thread.id),
                    )
                    thread.contact_name = contact_name
                return thread

            # Create new thread
            now = time.time()
            cursor.execute(
                "INSERT INTO threads (recipient_number, contact_name, snippet, unread_count, created_at, updated_at) "
                "VALUES (?, ?, '', 0, ?, ?);",
                (clean_number, contact_name, now, now),
            )
            thread_id = cursor.lastrowid
            return SmsThread(
                id=thread_id,
                recipient_number=clean_number,
                contact_name=contact_name,
                snippet="",
                unread_count=0,
                created_at=now,
                updated_at=now,
            )

    def save_message(
        self,
        direction: str,
        phone_number: str,
        body: str,
        timestamp: Optional[float] = None,
        sim_index: Optional[int] = None,
        status: str = "DELIVERED",
        is_read: bool = False,
    ) -> SmsMessage:
        """
        Store a message, automatically updating thread metadata and unread counters.
        """
        clean_number = normalize_phone_number(phone_number)
        msg_time = timestamp if timestamp is not None else time.time()
        thread = self.get_or_create_thread(clean_number)

        snippet = body[:80].replace("\n", " ")
        unread_inc = 1 if (direction.upper() == "IN" and not is_read) else 0

        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (thread_id, direction, phone_number, body, timestamp, sim_index, status, is_read) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?);",
                (
                    thread.id,
                    direction.upper(),
                    clean_number,
                    body,
                    msg_time,
                    sim_index,
                    status,
                    1 if is_read else 0,
                ),
            )
            msg_id = cursor.lastrowid

            # Update thread snippet, updated_at, and unread count
            cursor.execute(
                "UPDATE threads SET snippet = ?, unread_count = unread_count + ?, updated_at = ? "
                "WHERE id = ?;",
                (snippet, unread_inc, msg_time, thread.id),
            )

        return SmsMessage(
            id=msg_id,
            thread_id=thread.id,
            direction=direction.upper(),
            phone_number=clean_number,
            body=body,
            timestamp=msg_time,
            sim_index=sim_index,
            status=status,
            is_read=is_read,
        )

    def list_threads(self, limit: int = 50, offset: int = 0) -> List[SmsThread]:
        """List active conversation threads ordered by most recent update."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, recipient_number, contact_name, snippet, unread_count, created_at, updated_at "
            "FROM threads ORDER BY updated_at DESC LIMIT ? OFFSET ?;",
            (limit, offset),
        )
        return [
            SmsThread(
                id=r["id"],
                recipient_number=r["recipient_number"],
                contact_name=r["contact_name"],
                snippet=r["snippet"] or "",
                unread_count=r["unread_count"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in cursor.fetchall()
        ]

    def get_thread_messages(
        self,
        thread_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[SmsMessage]:
        """List messages within a conversation thread ordered chronologically."""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, thread_id, direction, phone_number, body, timestamp, sim_index, status, is_read "
            "FROM messages WHERE thread_id = ? ORDER BY timestamp ASC LIMIT ? OFFSET ?;",
            (thread_id, limit, offset),
        )
        return [
            SmsMessage(
                id=r["id"],
                thread_id=r["thread_id"],
                direction=r["direction"],
                phone_number=r["phone_number"],
                body=r["body"],
                timestamp=r["timestamp"],
                sim_index=r["sim_index"],
                status=r["status"],
                is_read=bool(r["is_read"]),
            )
            for r in cursor.fetchall()
        ]

    def mark_thread_read(self, thread_id: int) -> None:
        """Mark all messages in thread as read and zero out unread counter."""
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE messages SET is_read = 1 WHERE thread_id = ?;", (thread_id,))
            cursor.execute("UPDATE threads SET unread_count = 0 WHERE id = ?;", (thread_id,))

    def delete_message(self, message_id: int) -> bool:
        """Delete a single message."""
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM messages WHERE id = ?;", (message_id,))
            return cursor.rowcount > 0

    def delete_thread(self, thread_id: int) -> bool:
        """Delete an entire conversation thread and all its messages."""
        conn = self.db.get_connection()
        with conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM threads WHERE id = ?;", (thread_id,))
            return cursor.rowcount > 0

    def reconcile_sim_inbox(
        self,
        dispatcher: AtDispatcher,
        purge_sim: bool = True,
    ) -> List[SmsMessage]:
        """
        Reconcile messages stored in SIM card memory (SM) into SQLite.
        If purge_sim is True, deletes successfully synced messages from SIM storage
        using AT+CMGD to keep SIM memory free and prevent full-storage rejections.
        """
        # 1. Switch preferred storage to SIM ("SM") and configure text mode
        dispatcher.execute('AT+CPMS="SM","SM","SM"')
        dispatcher.execute("AT+CMGF=1")

        # 2. Query all messages from SIM
        resp = dispatcher.execute('AT+CMGL="ALL"')
        if not resp.success:
            logger.error("Failed to query SIM SMS messages: %s", resp.error)
            return []

        ingested: List[SmsMessage] = []
        cmgl_pattern = re.compile(
            r'^\+CMGL:\s*(\d+),\s*"([^"]+)",\s*"([^"]+)"(?:,[^,]*)?,\s*"([^"]+)"'
        )


        current_index: Optional[int] = None
        current_sender: Optional[str] = None
        current_date: Optional[str] = None
        current_body_lines: List[str] = []

        def _commit_current():
            nonlocal current_index, current_sender, current_date, current_body_lines
            if current_index is not None and current_sender is not None:
                body = "\n".join(current_body_lines).strip()
                tstamp = parse_sim_timestamp(current_date or "")

                # Check if message already exists in database
                conn = self.db.get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id FROM messages WHERE phone_number = ? AND body = ? AND abs(timestamp - ?) < 300;",
                    (normalize_phone_number(current_sender), body, tstamp),
                )
                if not cursor.fetchone():
                    msg = self.save_message(
                        direction="IN",
                        phone_number=current_sender,
                        body=body,
                        timestamp=tstamp,
                        sim_index=current_index,
                        is_read=False,
                    )
                    ingested.append(msg)

                # Purge from SIM if requested
                if purge_sim:
                    del_resp = dispatcher.execute(f"AT+CMGD={current_index}")
                    if del_resp.success:
                        logger.info("Purged reconciled message index %d from SIM", current_index)
                    else:
                        logger.warning("Failed to purge SIM index %d: %s", current_index, del_resp.error)

            current_index = None
            current_sender = None
            current_date = None
            current_body_lines = []

        for line in resp.lines:
            m = cmgl_pattern.match(line.strip())
            if m:
                _commit_current()
                current_index = int(m.group(1))
                # group(2) is status ("REC READ", "REC UNREAD")
                current_sender = m.group(3)
                current_date = m.group(4)
            else:
                if current_index is not None:
                    current_body_lines.append(line)

        # Commit final message in buffer
        _commit_current()

        return ingested
