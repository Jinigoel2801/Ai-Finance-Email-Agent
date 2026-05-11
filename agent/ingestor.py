"""
agent/ingestor.py — Invoice Data Ingestion Module.

Reads invoice records from a CSV file, validates required columns,
computes the number of days each invoice is overdue, and returns
a list of validated Pydantic InvoiceRecord objects. Only invoices
that are actually overdue (days_overdue > 0) are included in the
returned list.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import List

import pandas as pd
from pydantic import BaseModel, EmailStr

class InvoiceRecord(BaseModel):
    """Validated invoice record with computed days_overdue field."""

    invoice_no: str
    client_name: str
    amount_due: float
    due_date: date
    contact_email: EmailStr
    follow_up_count: int
    payment_link: str
    days_overdue: int

REQUIRED_COLUMNS: list[str] = [
    "invoice_no",
    "client_name",
    "amount_due",
    "due_date",
    "contact_email",
    "follow_up_count",
    "payment_link",
]

def load_invoices(csv_path: str | os.PathLike = "data/invoices.csv") -> List[InvoiceRecord]:
    """Read invoices from *csv_path*, validate, compute overdue days, and
    return only overdue records as ``InvoiceRecord`` objects.

    Parameters
    ----------
    csv_path:
        Path to the invoices CSV file.

    Returns
    -------
    List[InvoiceRecord]
        Validated, overdue invoice records sorted by days_overdue descending.

    Raises
    ------
    FileNotFoundError
        If *csv_path* does not exist.
    ValueError
        If required columns are missing or contain null values.
    """
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"Invoice file not found: {path.resolve()}")

    df = pd.read_csv(path)

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(
            f"Missing required columns in {path.name}: {', '.join(missing_cols)}"
        )

    for col in REQUIRED_COLUMNS:
        null_count = df[col].isna().sum()
        if null_count > 0:
            raise ValueError(
                f"Column '{col}' has {null_count} null value(s) in {path.name}. "
                "All fields are required."
            )

    today = date.today()
    df["due_date"] = pd.to_datetime(df["due_date"]).dt.date
    df["days_overdue"] = df["due_date"].apply(lambda d: (today - d).days)

    overdue_df = df[df["days_overdue"] > 0].copy()

    overdue_df = overdue_df.sort_values("days_overdue", ascending=False)

    records: List[InvoiceRecord] = []
    for _, row in overdue_df.iterrows():
        record = InvoiceRecord(
            invoice_no=str(row["invoice_no"]).strip(),
            client_name=str(row["client_name"]).strip(),
            amount_due=float(row["amount_due"]),
            due_date=row["due_date"],
            contact_email=str(row["contact_email"]).strip(),
            follow_up_count=int(row["follow_up_count"]),
            payment_link=str(row["payment_link"]).strip(),
            days_overdue=int(row["days_overdue"]),
        )
        records.append(record)

    return records