"""
agent/tone_engine.py — Escalation Stage & Tone Mapping.

Pure business-logic module (no LLM calls). Maps the number of days an
invoice is overdue to one of four escalation stages or an ESCALATE flag.
Each stage carries a pre-defined tone descriptor, urgency level, and
detailed writing instruction for the email generator.
"""

from __future__ import annotations

from typing import Dict

TONE_MAP: Dict[str, Dict[str, str]] = {
    "stage_1": {
        "tone": "Warm and Friendly",
        "urgency": "low",
        "instruction": (
            "Write a gentle, warm reminder. Assume the client simply forgot. "
            "Be polite and helpful. End with a payment link."
        ),
    },
    "stage_2": {
        "tone": "Polite but Firm",
        "urgency": "medium",
        "instruction": (
            "Payment is still pending. Be polite but make clear this needs "
            "attention. Ask them to confirm a payment date."
        ),
    },
    "stage_3": {
        "tone": "Formal and Serious",
        "urgency": "high",
        "instruction": (
            "This is escalating. Use formal language. Mention that continued "
            "non-payment may affect credit terms. Demand a response within "
            "48 hours."
        ),
    },
    "stage_4": {
        "tone": "Stern and Urgent",
        "urgency": "critical",
        "instruction": (
            "This is the final reminder before legal escalation. Be stern "
            "and direct. State clearly that failure to pay within 24 hours "
            "will result in escalation to legal/recovery team."
        ),
    },
}

def get_stage(days_overdue: int) -> str:
    """Return the escalation stage for a given number of overdue days.

    Parameters
    ----------
    days_overdue:
        Number of calendar days past the invoice due date.

    Returns
    -------
    str
        One of ``"stage_1"``, ``"stage_2"``, ``"stage_3"``,
        ``"stage_4"``, or ``"ESCALATE"``.
    """
    if days_overdue > 30:
        return "ESCALATE"
    elif days_overdue >= 22:
        return "stage_4"
    elif days_overdue >= 15:
        return "stage_3"
    elif days_overdue >= 8:
        return "stage_2"
    else:
        return "stage_1"