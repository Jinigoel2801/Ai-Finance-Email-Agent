"""
agent/email_gen.py — LLM-Powered Email Generation (Groq + Llama 3.3).

Uses the Groq Python SDK to call Llama 3.3 70B and generate personalised
overdue-payment reminder emails. The prompt is dynamically populated with
invoice details and tone instructions. The LLM response is validated with
Pydantic to ensure it contains both a subject line and an email body.
Input fields are sanitised before prompt insertion to mitigate prompt-
injection attacks.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Dict

from groq import Groq
from pydantic import BaseModel, ValidationError

from agent.ingestor import InvoiceRecord

class EmailOutput(BaseModel):
    """Validated structure returned by the LLM."""

    subject: str
    body: str

SYSTEM_PROMPT: str = (
    "You are a professional finance communication assistant. "
    "Your job is to write overdue payment reminder emails.\n"
    "You MUST return ONLY a valid JSON object with exactly two keys: "
    '"subject" and "body". \n'
    "No markdown, no explanation, no preamble. Just the JSON object.\n"
    "All invoice details provided must appear in the email.\n"
    "Never fabricate or omit any field."
)

USER_PROMPT_TEMPLATE: str = """\
Write a payment reminder email with the following details:

Tone: {tone}
Instruction: {instruction}

Invoice Details:
- Client Name: {client_name}
- Invoice Number: {invoice_no}
- Amount Due: ₹{amount_due}
- Original Due Date: {due_date}
- Days Overdue: {days_overdue}
- Payment Link: {payment_link}

Sender Details:
- Sender Name: {sender_name}
(Make sure to sign off the email with the Sender Name).

Return ONLY this JSON structure:
{{
  "subject": "...",
  "body": "..."
}}
"""

def _sanitize(value: str) -> str:
    """Strip characters that could be used for prompt injection.

    Removes ``<``, ``>``, ``"``, and newlines, then trims whitespace.
    """
    cleaned = re.sub(r'[<>"\n\r]', "", value)
    return cleaned.strip()

def generate_email(
    record: InvoiceRecord,
    stage: str,
    tone_info: Dict[str, str],
) -> EmailOutput:
    """Call Groq (Llama 3.3 70B) to generate a personalised follow-up email.

    Parameters
    ----------
    record:
        The overdue invoice record.
    stage:
        Current escalation stage (e.g. ``"stage_2"``).
    tone_info:
        Dict with ``tone`` and ``instruction`` keys from
        :data:`agent.tone_engine.TONE_MAP`.

    Returns
    -------
    EmailOutput
        Validated email with ``subject`` and ``body``.

    Raises
    ------
    ValueError
        If the LLM response cannot be parsed as valid JSON matching
        the ``EmailOutput`` schema.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    sender_name = os.environ.get("SENDER_NAME", "Finance Team")

    user_prompt = USER_PROMPT_TEMPLATE.format(
        tone=tone_info["tone"],
        instruction=tone_info["instruction"],
        client_name=_sanitize(record.client_name),
        invoice_no=_sanitize(record.invoice_no),
        amount_due=f"{record.amount_due:,.2f}",
        due_date=record.due_date.isoformat(),
        days_overdue=record.days_overdue,
        payment_link=record.payment_link,
        sender_name=sender_name,
    )

    max_retries = 3
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                max_tokens=1024,
            )
            break
        except Exception as api_err:
            if "429" in str(api_err) and attempt < max_retries:
                wait = 15 * (attempt + 1)
                print(f"  ⏳  Rate limited — retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise

    raw_text: str = response.choices[0].message.content.strip()

    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)
        raw_text = raw_text.strip()

    try:
        data = json.loads(raw_text)
        email = EmailOutput(**data)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(
            f"Failed to parse LLM response as EmailOutput.\n"
            f"Stage: {stage} | Invoice: {record.invoice_no}\n"
            f"Raw response:\n{raw_text}\n"
            f"Error: {exc}"
        ) from exc

    return email