"""
main.py — CLI Entry Point for the Finance Email Agent.

Supports four modes of operation:
    --dry-run       Process all overdue invoices in dry-run mode (default).
    --send          Process all overdue invoices and send real emails.
    --summary       Print the audit log summary table.
    --invoice ID    Process a single specific invoice by its invoice_no.

Prints a formatted summary table after processing.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

from dotenv import load_dotenv

load_dotenv()

from agent.ingestor import InvoiceRecord, load_invoices
from agent.tone_engine import get_stage, TONE_MAP
from agent.email_gen import generate_email
from agent.sender import send_email
from agent.audit import log_email, get_all_logs, get_summary

def _process_record(record: InvoiceRecord) -> dict:
    """Run the full pipeline for a single invoice record.

    Returns a summary dict for the results table.
    """
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
            f"  ⚠️  [ESCALATED] {record.invoice_no} — "
            f"{record.client_name} flagged for legal/finance review"
        )
        return {
            "invoice_no": record.invoice_no,
            "client": record.client_name,
            "days_overdue": record.days_overdue,
            "stage": "ESCALATE",
            "status": "escalated",
        }

    tone_info = TONE_MAP[stage]

    try:
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
        return {
            "invoice_no": record.invoice_no,
            "client": record.client_name,
            "days_overdue": record.days_overdue,
            "stage": stage,
            "status": result["status"],
        }
    except Exception as exc:
        log_email(
            record,
            stage=stage,
            tone=tone_info["tone"],
            subject="N/A",
            send_status="failed",
            error_msg=str(exc),
        )
        print(f"  ❌  Error processing {record.invoice_no}: {exc}")
        return {
            "invoice_no": record.invoice_no,
            "client": record.client_name,
            "days_overdue": record.days_overdue,
            "stage": stage,
            "status": "failed",
        }

def _print_summary_table(results: list[dict]) -> None:
    """Pretty-print a summary table of processing results."""
    if not results:
        print("\n  No records processed.\n")
        return

    header = f"  {'Invoice':<16} {'Client':<22} {'Days':>5} {'Stage':<10} {'Status':<10}"
    separator = "  " + "─" * 65
    print(f"\n{separator}")
    print(header)
    print(separator)
    for r in results:
        status_icon = {
            "sent": "✅",
            "dry_run": "📝",
            "escalated": "⚠️",
            "failed": "❌",
        }.get(r["status"], "❓")

        print(
            f"  {r['invoice_no']:<16} {r['client']:<22} "
            f"{r['days_overdue']:>5} {r['stage']:<10} "
            f"{status_icon} {r['status']:<10}"
        )
    print(separator)

def _print_audit_summary() -> None:
    """Print aggregate audit log statistics."""
    summary = get_summary()
    print("\n  📊  Audit Log Summary")
    print("  " + "─" * 30)
    print(f"  ✅  Sent       : {summary['sent']}")
    print(f"  📝  Dry Run    : {summary['dry_run']}")
    print(f"  ❌  Failed     : {summary['failed']}")
    print(f"  ⚠️   Escalated  : {summary['escalated']}")
    total = sum(summary.values())
    print(f"  ──────────────────────────────")
    print(f"  📦  Total      : {total}")
    print()

def main() -> None:
    """Parse CLI arguments and run the appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Finance Credit Follow-Up Email Agent — CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
examples:
  python main.py --dry-run                        Process all overdue invoices (dry run)
  python main.py --send                           Process all overdue invoices (real send)
  python main.py --send --invoice INV-2025-001    Send real email for one invoice
  python main.py --summary                        Print audit log summary
        """,
    )
    parser.add_argument("--dry-run", action="store_true", help="Process invoices in dry-run mode (default).")
    parser.add_argument("--send", action="store_true", help="Process invoices and send real emails via SMTP.")
    parser.add_argument("--summary", action="store_true", help="Print audit log summary table.")
    parser.add_argument("--invoice", type=str, metavar="ID", help="Process a single invoice by its invoice_no.")

    args = parser.parse_args()

    if not (args.dry_run or args.send or args.summary or args.invoice):
        parser.print_help()
        sys.exit(1)

    if args.summary:
        _print_audit_summary()
        logs = get_all_logs()
        if logs:
            results = [
                {
                    "invoice_no": l["invoice_no"],
                    "client": l["client_name"],
                    "days_overdue": l["days_overdue"],
                    "stage": l["stage"],
                    "status": l["send_status"],
                }
                for l in logs
            ]
            _print_summary_table(results)
        return

    if args.send:
        os.environ["DRY_RUN"] = "false"
        print("🚀  Mode: REAL SEND")
    else:
        os.environ["DRY_RUN"] = "true"
        print("📝  Mode: DRY RUN")

    records = load_invoices("data/invoices.csv")
    print(f"📂  Loaded {len(records)} overdue invoice(s).\n")

    if args.invoice:
        target = [r for r in records if r.invoice_no == args.invoice]
        if not target:
            print(f"  ❌  Invoice '{args.invoice}' not found or not overdue.")
            sys.exit(1)
        records = target

    results: list[dict] = []
    for i, record in enumerate(records):
        result = _process_record(record)
        results.append(result)

        if i < len(records) - 1 and result["status"] != "escalated":
            print("  ⏳  Waiting 10s (rate limit)...")
            time.sleep(10)

    _print_summary_table(results)
    print("  Done. All actions logged to audit_log.db\n")

if __name__ == "__main__":
    main()