"""
celery_app.py — Celery Application Configuration.

Configures Celery with a Redis broker and result backend.
Applies a rate limit to the ``process_invoice`` task to prevent
email-sending from triggering spam filters.
"""

from __future__ import annotations

import os

from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "finance_email_agent",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["agent.tasks"],
)

celery_app.conf.update(

    task_routes={
        "agent.tasks.process_invoice": {"rate_limit": "10/m"},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
)