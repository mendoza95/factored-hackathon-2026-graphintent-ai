from pathlib import Path

import duckdb
import pandas as pd

TEXT_COLS = [
    "full_text",
    "detected_keywords",
    "detected_intents",
    "main_topics",
]

FEATURE_COLS = [
    "rich_text",
    "channel",
    "detected_sentiment",
    "duration_seconds",
    "wait_time_seconds",
    "sentiment_score",
    "has_past_complaint",
]


def assign_target_label(row: pd.Series) -> str:
    """Derive ground truth intent label from interaction metadata."""
    contact_reason = str(row.get("contact_reason", "")).lower()
    was_escalated = row.get("was_escalated", False)

    if contact_reason in ["queja", "transaccional", "complaint"]:
        return "dispute_initiate"
    elif was_escalated is True:
        return "human_handoff"
    else:
        return "account_inquiry"


def load_and_prepare_data(data_dir: Path) -> pd.DataFrame:
    """
    Extract raw data using DuckDB, build engineered features,
    and return clean DataFrame.
    """
    con = duckdb.connect()

    # 1. Query Call Center Interactions
    query_interactions = f"""
        SELECT 
            t.full_text,
            t.detected_keywords,
            t.detected_intents,
            t.main_topics,
            i.channel,
            i.detected_sentiment,
            i.duration_seconds,
            i.wait_time_seconds,
            i.sentiment_score,
            i.contact_reason,
            i.was_escalated,
            i.customer_id
        FROM '{data_dir}/call_transcripts/*.csv' t
        INNER JOIN '{data_dir}/call_center_interactions/*.csv' i
            ON t.interaction_id = i.interaction_id
        WHERE t.full_text IS NOT NULL AND LENGTH(TRIM(t.full_text)) > 0
    """
    df_interactions = con.sql(query_interactions).df()

    # 2. Query Complaints Data (Treated as In-Domain Dispute Training Rows)
    query_complaints = f"""
        SELECT 
            c.description AS full_text,
            c.category AS detected_keywords,
            c.subcategory AS detected_intents,
            c.case_type AS main_topics,
            'chat' AS channel,
            'negative' AS detected_sentiment,
            0.0 AS duration_seconds,
            0.0 AS wait_time_seconds,
            -0.8 AS sentiment_score,
            'complaint' AS contact_reason,
            FALSE AS was_escalated,
            c.customer_id
        FROM '{data_dir}/complaints/*.csv' c
        WHERE c.description IS NOT NULL AND LENGTH(TRIM(c.description)) > 0
    """
    try:
        df_complaints = con.sql(query_complaints).df()
    except Exception:
        df_complaints = pd.DataFrame()

    # 3. Concatenate both DataFrames vertically
    df = pd.concat([df_interactions, df_complaints], ignore_index=True)

    # Fill missing text columns
    for col in TEXT_COLS:
        df[col] = df[col].fillna("")

    # Combine text fields into rich_text
    df["rich_text"] = (
        df["full_text"]
        + " "
        + df["detected_keywords"]
        + " "
        + df["detected_intents"]
        + " "
        + df["main_topics"]
    )

    # Flag historical complaint customers
    complaints_query = f"""
        SELECT DISTINCT customer_id 
        FROM '{data_dir}/complaints/*.csv' 
        WHERE customer_id IS NOT NULL
    """
    try:
        complaint_customers = set(
            con.sql(complaints_query).df()["customer_id"].astype(str)
        )
    except Exception:
        complaint_customers = set()

    df["has_past_complaint"] = df["customer_id"].astype(str).isin(complaint_customers)

    # Generate target labels
    df["label"] = df.apply(assign_target_label, axis=1)

    return df
