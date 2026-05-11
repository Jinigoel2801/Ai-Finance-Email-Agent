from __future__ import annotations

import argparse
import signal
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

load_dotenv()

from agent.ingestor import load_invoices
from agent.tasks import process_invoice

def run_daily_job() -> None:
    """Load all overdue invoices and enqueue each as a Celery task."""
    print("\n[Scheduler] Running daily invoice job …")
    try:
        records = load_invoices("data/invoices.csv")
        print(f"   Found {len(records)} overdue invoice(s).")
        for record in records:
            process_invoice.delay(record.model_dump(mode="json"))
            print(f"   → Queued {record.invoice_no} ({record.days_overdue}d overdue)")
        print("All tasks enqueued.\n")
    except Exception as exc:
        print(f"Job failed: {exc}\n")

def main() -> None:
    """Entry point for the scheduler CLI."""
    parser = argparse.ArgumentParser(
        description="Schedule or manually trigger the invoice email agent."
    )
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Immediately run the daily job instead of waiting for the cron schedule.",
    )
    args = parser.parse_args()

    if args.run_now:
        print("Manual trigger requested — running job now.")
        run_daily_job()
        return

    scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    scheduler.add_job(run_daily_job, "cron", hour=9, minute=0, id="daily_email_job")
    scheduler.start()
    print("Scheduler started — daily job at 09:00 IST.  Press Ctrl+C to exit.")

    def _shutdown(signum, frame):
        print("\nShutting down scheduler …")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()