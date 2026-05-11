"""
agent/tasks.py — Celery Task Definitions.

Defines the ``process_invoice`` task which orchestrates the full
pipeline for a single invoice: stage classification → email generation
→ dispatch → audit logging.  Retries up to 3 times on transient
failures with a 60-second backoff.
"""

from __future__ import annotations

from celery_app import celery_app
from agent.ingestor import InvoiceRecord
from agent.tone_engine import get_stage, TONE_MAP
from agent.email_gen import generate_email
from agent.sender import send_email
from agent.audit import log_email

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_invoice(self, invoice_dict: dict) -> None:
    """Process a single overdue invoice through the full email pipeline.

    Parameters
    ----------
    invoice_dict:
        Serialised ``InvoiceRecord`` (as produced by ``.model_dump()``).
    """
    record: InvoiceRecord | None = None
    try:
        record = InvoiceRecord(**invoice_dict)
        stage = get_stage(record.days_overdue)

        if stage == "ESCALATE":
            log_email(
                record,
                stage="ESCALATE",
                tone="Human review required",
                subject="N/A",
                send_status="escalated",
                error_msg=None,
            )
            print(
                f"     [ESCALATED] {record.invoice_no} — "
                f"{record.client_name} flagged for legal/finance review "
                f"({record.days_overdue} days overdue)"
            )
            return

        tone_info = TONE_MAP[stage]
        email = generate_email(record, stage, tone_info)
        result = send_email(email, record)

        log_email(
            record,
            stage=stage,
            tone=tone_info["tone"],
            subject=email.subject,
            send_status=result["status"],
            error_msg=result.get("error"),
        )

    except Exception as exc:
        if record is not None:
            log_email(
                record,
                stage="ERROR",
                tone="N/A",
                subject="N/A",
                send_status="failed",
                error_msg=str(exc),
            )
        print(f"     Task failed for invoice: {exc}")
        raise self.retry(exc=exc)