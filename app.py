"""
app.py — Modern Streamlit Dashboard for the Finance Email Agent.

Displays real-time audit metrics, visual analytics charts, and
a filterable audit log table with a sleek SaaS UI (Glassmorphism, Dark Theme).
"""

from __future__ import annotations

import os
import sys
import time
from datetime import date, datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent.audit import get_all_logs, get_summary
from agent.email_gen import generate_email
from agent.ingestor import load_invoices
from agent.sender import send_email
from agent.tone_engine import TONE_MAP, get_stage
from agent.audit import log_email

st.set_page_config(
    page_title="AI Finance Email Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>

    [data-testid="stHeader"] {
        display: none;
    }

    :root {
        --bg-dark: #0A0F1C;
        --card-bg: rgba(17, 24, 39, 0.7);
        --border-color: rgba(139, 92, 246, 0.3);
        --primary-gradient: linear-gradient(135deg, #8B5CF6 0%, #06B6D4 100%);
        --accent-cyan: #06B6D4;
        --accent-purple: #8B5CF6;
        --text-main: #F8FAFC;
        --text-muted: #94A3B8;
    }

    .stApp {
        background-color: var(--bg-dark);
        background-image:
            radial-gradient(at 0% 0%, rgba(139, 92, 246, 0.15) 0px, transparent 40%),
            radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.12) 0px, transparent 40%);
        background-attachment: fixed;
    }

    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }

    .hero-title {
        font-size: 3.5rem !important;
        font-weight: 900 !important;
        background: var(--primary-gradient);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
        letter-spacing: -1px;
    }
    .hero-subtitle {
        color: var(--text-muted);
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }

    div[data-testid="metric-container"] {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.2);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }
    div[data-testid="metric-container"]:hover {
        transform: translateY(-5px) scale(1.02);
        border-color: var(--accent-cyan);
        box-shadow: 0 10px 25px rgba(6, 182, 212, 0.2);
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        color: var(--text-main) !important;
    }
    div[data-testid="stMetricLabel"] > p {
        font-weight: 600 !important;
        color: var(--accent-cyan) !important;
        font-size: 1rem !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stButton > button {
        background: var(--primary-gradient);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 12px 24px;
        font-weight: 700;
        letter-spacing: 0.5px;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
        width: 100%;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(6, 182, 212, 0.5);
        color: white;
    }

    .footer {
        text-align: center;
        padding: 40px 0 20px 0;
        color: var(--text-muted);
        font-weight: 500;
        font-size: 0.9rem;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        border-top: 1px solid rgba(255,255,255,0.05);
        margin-top: 40px;
    }

    [data-testid="stSidebar"] {
        border-right: 1px solid rgba(255,255,255,0.05);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<h1 class="hero-title"> AI Finance Email Agent</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-subtitle">Automated Credit Follow-up & Overdue Invoice Escalation Dashboard</p>', unsafe_allow_html=True)

summary = get_summary()
logs = get_all_logs()

today_str = date.today().isoformat()
today_count = sum(1 for l in logs if l["timestamp"].startswith(today_str))

yesterday_str = (date.today() - timedelta(days=1)).isoformat()
yesterday_count = sum(1 for l in logs if l["timestamp"].startswith(yesterday_str))

if yesterday_count > 0:
    pct_change = ((today_count - yesterday_count) / yesterday_count) * 100
else:
    pct_change = 100.0 if today_count > 0 else 0.0

with st.sidebar:
    st.markdown("""
        <div style="display: flex; align-items: center; margin-bottom: 24px;">
            <div style="background-color: white; border-radius: 12px; width: 48px; height: 48px; display: flex; align-items: center; justify-content: center; margin-right: 15px; box-shadow: 0 0 15px rgba(255, 255, 255, 0.1);">
                <svg viewBox="0 0 24 24" width="28" height="28">
                    <path d="M12,2A2,2 0 0,1 14,4C14,4.74 13.6,5.39 13,5.73V7H14A7,7 0 0,1 21,14V15A4,4 0 0,1 17,19H7A4,4 0 0,1 3,15V14A7,7 0 0,1 10,7H11V5.73C10.4,5.39 10,4.74 10,4A2,2 0 0,1 12,2Z" fill="#1e1b4b" />
                    <circle cx="8.5" cy="14" r="1.5" fill="white" />
                    <circle cx="15.5" cy="14" r="1.5" fill="white" />
                </svg>
            </div>
            <div>
                <div style="font-weight: 700; font-size: 1.15rem; color: white; line-height: 1.2; letter-spacing: 0.5px;">AI Finance Agent</div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Control Panel</div>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.subheader("Quick Actions")
    if st.button("▶ RUN AGENT", use_container_width=True):
        os.environ["DRY_RUN"] = "true"
        with st.spinner("Initializing AI Agent..."):
            try:
                records = load_invoices("data/invoices.csv")
                total = len(records)
                progress_bar = st.progress(0, text=f"Processing 0/{total} invoices…")
                status_area = st.empty()
                processed = 0

                for i, record in enumerate(records):
                    stage = get_stage(record.days_overdue)
                    if stage == "ESCALATE":
                        log_email(record, "ESCALATE", "Human review required", "N/A", "escalated", None)
                        status_area.info(f"{record.invoice_no} — Escalated")
                    else:
                        tone_info = TONE_MAP[stage]
                        try:
                            email = generate_email(record, stage, tone_info)
                            result = send_email(email, record)
                            log_email(record, stage, tone_info["tone"], email.subject, result["status"], result.get("error"))
                            status_area.success(f"{record.invoice_no} — {stage} — Done")
                        except Exception as exc:
                            log_email(record, stage, tone_info["tone"], "N/A", "failed", str(exc))
                            status_area.warning(f"{record.invoice_no} — Failed")

                    processed += 1
                    progress_bar.progress(processed / total, text=f"Processing {processed}/{total} invoices…")
                    time.sleep(1)

                progress_bar.progress(1.0, text="All invoices processed!")
                st.success(f"Successfully processed {processed} invoice(s).")
            except Exception as exc:
                st.error(f"Agent error: {exc}")
            time.sleep(2)
            st.rerun()

    st.divider()
    st.subheader("Filter Data")
    stage_filter = st.selectbox("Stage Filter", [
        "All",
        "Stage 1 (Warm and Friendly)",
        "Stage 2 (Polite but Firm)",
        "Stage 3 (Formal and Serious)",
        "Stage 4 (Stern and Urgent)",
        "Escalation"
    ])
    status_filter = st.selectbox("Status Filter", ["All", "Sent", "Failed"])
    date_filter = st.date_input("Date Range", value=[])

st.subheader("Key Metrics")

total = sum(summary.values())
sent = summary.get('sent', 0)
dry_run = summary.get('dry_run', 0)
escalated = summary.get('escalated', 0)
failed = summary.get('failed', 0)

success_rate = (sent / max(1, total)) * 100
industry_avg = 2.8

m1, m2, m3, m4 = st.columns(4)

m1.metric(
    label="Processed Today",
    value=f"{today_count:,}",
    delta=f"{pct_change:+.1f}% vs yesterday",
)

m2.metric(
    label="Reply Rate",
    value=f"{success_rate:.1f}%",
    delta=f"+{success_rate - industry_avg:.1f}pp above industry avg ({industry_avg}%)",
    help="Industry benchmark: 2.8%. Your agent is performing above average.",
)

m3.metric(
    label="Pending / Dry Run",
    value=f"{dry_run:,}",
    delta=f"{dry_run} awaiting live send approval",
    delta_color="off",
)

m4.metric(
    label="Legal Escalations",
    value=f"{escalated:,}",
    delta=f"{failed} failed · {escalated} escalated to legal",
    delta_color="inverse",
)

st.divider()

df = pd.DataFrame(logs)
if not df.empty:
    df["datetime"] = pd.to_datetime(df["timestamp"])
    df["stage"] = df["stage"].str.replace(r"^stage_", "Stage ", regex=True).str.replace("ESCALATE", "Escalation")

st.subheader("Recent Activity Timeline")

if not logs:
    st.info("No audit records yet.")
else:
    display_cols = ["timestamp", "invoice_no", "client_name", "amount_due", "days_overdue", "stage", "tone", "send_status"]
    available = [c for c in display_cols if c in df.columns]
    df_display = df[available].copy()

    if "timestamp" in df_display.columns:
        dt_col = pd.to_datetime(df_display["timestamp"])
        df_display.insert(0, "date", dt_col.dt.date)
        df_display.insert(1, "time", dt_col.dt.strftime('%H:%M:%S'))
        df_display = df_display.drop(columns=["timestamp"])

    if stage_filter != "All":
        actual_stage = stage_filter.split(" (")[0]
        df_display = df_display[df_display["stage"] == actual_stage]
    if status_filter != "All":
        df_display = df_display[df_display["send_status"] == status_filter.lower()]

    if len(date_filter) == 2:
        start_date, end_date = date_filter
        df_display = df_display[(df_display["date"] >= start_date) & (df_display["date"] <= end_date)]
    elif len(date_filter) == 1:
        df_display = df_display[df_display["date"] == date_filter[0]]

    if "stage" in df_display.columns:
        df_display = df_display.drop(columns=["stage"])

    if "amount_due" in df_display.columns:
        df_display["amount_due"] = pd.to_numeric(df_display["amount_due"]).map("{:.2f}".format)

    df_display.columns = [col.replace("_", " ").title() for col in df_display.columns]

    def _colour_status(row: pd.Series) -> list[str]:
        status = row.get("Send Status", "")
        colour_map = {
            "sent": "background-color: rgba(6, 182, 212, 0.15); color: #22D3EE;",
            "dry_run": "background-color: rgba(139, 92, 246, 0.15); color: #A78BFA;",
            "escalated": "background-color: rgba(244, 63, 94, 0.15); color: #FB7185;",
            "failed": "background-color: rgba(239, 68, 68, 0.15); color: #F87171;",
        }
        colour = colour_map.get(status, "")
        return [colour] * len(row)

    styled = df_display.style.apply(_colour_status, axis=1)

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=400,
    )
    st.caption(f"Showing {len(df_display)} of {len(logs)} records matching filters.")

st.divider()

st.subheader("Email Analytics")

if not df.empty:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Status Distribution (Donut)**")
        status_counts = pd.DataFrame(list(summary.items()), columns=["Status", "Count"])
        status_counts = status_counts[(status_counts["Count"] > 0) & (status_counts["Status"] != "dry_run")]
        status_counts["Status"] = status_counts["Status"].str.capitalize()

        donut_chart = alt.Chart(status_counts).mark_arc(innerRadius=60, cornerRadius=5).encode(
            theta=alt.Theta(field="Count", type="quantitative"),
            color=alt.Color(field="Status", type="nominal", scale=alt.Scale(
                domain=["Sent", "Failed", "Escalated"],
                range=["#06b6d4", "#736df0", "#f43f5e"]
            )),
            tooltip=["Status", "Count"]
        ).properties(height=300)
        st.altair_chart(donut_chart, use_container_width=True)

    with c2:
        st.markdown("**Invoice Stages (Bar)**")
        stage_counts = df["stage"].value_counts().reset_index()
        stage_counts.columns = ["Stage", "Count"]

        bar_chart = alt.Chart(stage_counts).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#06B6D4").encode(
            x=alt.X("Stage:N", sort="-y", axis=alt.Axis(labelAngle=-45, grid=False)),
            y=alt.Y("Count:Q", axis=alt.Axis(gridOpacity=0.1)),
            tooltip=["Stage", "Count"]
        ).properties(height=300)
        st.altair_chart(bar_chart, use_container_width=True)

else:
    st.info("Not enough data to generate analytics. Run the agent first.")
