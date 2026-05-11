"""
agent/sender.py — Email Dispatch Module (Dry-Run or SMTP).

Supports two modes controlled by the ``DRY_RUN`` environment variable:

* **dry-run** (default): Prints the email to the console and appends it
  as a JSON entry to ``dry_run_log.json``.
* **real send**: Delivers the email over SMTP using credentials from
  environment variables.

Always returns a status dict regardless of mode.
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict

from agent.email_gen import EmailOutput
from agent.ingestor import InvoiceRecord

DRY_RUN_LOG_PATH = Path("dry_run_log.json")

def _is_dry_run() -> bool:
    """Return ``True`` unless ``DRY_RUN`` is explicitly set to a falsy value."""
    return os.getenv("DRY_RUN", "true").strip().lower() in ("true", "1", "yes", "")

def send_email(
    email: EmailOutput,
    record: InvoiceRecord,
) -> Dict[str, Any]:
    """Send (or mock-send) *email* for the given *record*.

    Parameters
    ----------
    email:
        The generated email (subject + body).
    record:
        The invoice record this email pertains to.

    Returns
    -------
    dict
        ``{"status": "sent"|"dry_run"|"failed", "error": None|str}``
    """
    if _is_dry_run():
        return _dry_run_send(email, record)
    else:
        return _real_send(email, record)

def _dry_run_send(email: EmailOutput, record: InvoiceRecord) -> Dict[str, Any]:
    """Print the email preview, persist to the dry-run log file, then send via SMTP."""
    sender_email = os.getenv("SENDER_EMAIL", "finance@yourcompany.com")
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = os.getenv("SMTP_PORT", "587")
    smtp_user = os.getenv("SMTP_USER", "<your_smtp_user>")

    separator = "=" * 60
    print(f"\n{separator}")
    print("     DRY RUN MODE WITH REAL EMAIL SENDING ENABLED")
    print(separator)
    print(f"  To      : {record.contact_email}")
    print(f"  Subject : {email.subject}")
    print(f"  Invoice : {record.invoice_no}")
    print(separator)
    print(email.body)
    print(separator)
    print("       Sending via SMTP:")
    print(f"      SMTP {smtp_host}:{smtp_port}  |  From: {sender_email}  |  To: {record.contact_email}")
    print(f"      Auth user : {smtp_user}")
    print(f"      Subject   : {email.subject}")
    print(f"{separator}\n")

    entry: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "to": record.contact_email,
        "invoice_no": record.invoice_no,
        "subject": email.subject,
        "body": email.body,
    }

    log_entries: list[Dict[str, Any]] = []
    if DRY_RUN_LOG_PATH.exists():
        try:
            log_entries = json.loads(DRY_RUN_LOG_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            log_entries = []

    log_entries.append(entry)
    DRY_RUN_LOG_PATH.write_text(
        json.dumps(log_entries, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return _real_send(email, record)

def _real_send(email: EmailOutput, record: InvoiceRecord) -> Dict[str, Any]:
    """Send the email via SMTP using environment-configured credentials."""
    try:
        smtp_host: str = os.environ["SMTP_HOST"]
        smtp_port: int = int(os.environ["SMTP_PORT"])
        smtp_user: str = os.environ["SMTP_USER"]
        smtp_password: str = os.environ["SMTP_PASSWORD"]
        sender_email: str = os.environ["SENDER_EMAIL"]

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = record.contact_email
        msg["Subject"] = email.subject
        msg.attach(MIMEText(email.body, "plain", "utf-8"))

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_password)
            server.sendmail(sender_email, [record.contact_email], msg.as_string())

        print(f"     Email sent to {record.contact_email} for {record.invoice_no}")
        return {"status": "sent", "error": None}

    except Exception as exc:
        print(f"     Failed to send email to {record.contact_email}: {exc}")
        return {"status": "failed", "error": str(exc)}