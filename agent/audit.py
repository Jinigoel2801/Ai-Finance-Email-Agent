"""
agent/audit.py — SQLite Audit Trail.

Maintains a persistent SQLite database (``audit_log.db``) that records
every email attempt — whether sent, dry-run, failed, or escalated.
Contact emails are masked (``r***@domain.com``) before storage to
protect PII. Provides helpers to query the full log and retrieve
aggregate summaries for the dashboard.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.ingestor import InvoiceRecord

DB_PATH = Path("audit_log.db")

_CREATE_TABLE_SQL = """\
CREATE TABLE IF NOT EXISTS email_audit (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp     TEXT    NOT NULL,
    invoice_no    TEXT    NOT NULL,
    client_name   TEXT    NOT NULL,
    masked_email  TEXT    NOT NULL,
    amount_due    REAL    NOT NULL,
    days_overdue  INTEGER NOT NULL,
    stage         TEXT    NOT NULL,
    tone          TEXT    NOT NULL,
    subject       TEXT    NOT NULL,
    send_status   TEXT    NOT NULL,
    error_msg     TEXT
);
"""

def _get_connection() -> sqlite3.Connection:
    """Return a connection to the audit database, creating the table if needed."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    return conn

def mask_email(email: str) -> str:
    """Mask an email address for PII protection.

    Example: ``rajesh.sharma@technovate.in`` → ``r***@technovate.in``
    """
    if "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    if len(local) == 0:
        return f"***@{domain}"
    return f"{local[0]}***@{domain}"

def log_email(
    record: InvoiceRecord,
    stage: str,
    tone: str,
    subject: str,
    send_status: str,
    error_msg: Optional[str],
) -> None:
    """Insert one audit row for an email attempt.

    Parameters
    ----------
    record:
        The invoice record processed.
    stage:
        Escalation stage (``"stage_1"`` … ``"stage_4"`` or ``"ESCALATE"``
        or ``"ERROR"``).
    tone:
        Human-readable tone label.
    subject:
        Email subject line (or ``"N/A"`` for escalations/errors).
    send_status:
        One of ``"sent"``, ``"dry_run"``, ``"failed"``, ``"escalated"``.
    error_msg:
        Error details if the attempt failed; ``None`` otherwise.
    """
    conn = _get_connection()
    try:
        conn.execute(
            """\
            INSERT INTO email_audit
                (timestamp, invoice_no, client_name, masked_email,
                 amount_due, days_overdue, stage, tone, subject,
                 send_status, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                record.invoice_no,
                record.client_name,
                mask_email(record.contact_email),
                record.amount_due,
                record.days_overdue,
                stage,
                tone,
                subject,
                send_status,
                error_msg,
            ),
        )
        conn.commit()
    finally:
        conn.close()

def get_all_logs() -> List[Dict[str, Any]]:
    """Return every audit row as a list of dicts, newest first."""
    conn = _get_connection()
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute(
            "SELECT * FROM email_audit ORDER BY id DESC"
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()

def get_summary() -> Dict[str, int]:
    """Return aggregate counts by send status.

    Returns
    -------
    dict
        Keys: ``sent``, ``dry_run``, ``failed``, ``escalated``.
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """\
            SELECT send_status, COUNT(*) as cnt
            FROM email_audit
            GROUP BY send_status
            """
        )
        raw = {row[0]: row[1] for row in cursor.fetchall()}
        return {
            "sent": raw.get("sent", 0),
            "dry_run": raw.get("dry_run", 0),
            "failed": raw.get("failed", 0),
            "escalated": raw.get("escalated", 0),
        }
    finally:
        conn.close()