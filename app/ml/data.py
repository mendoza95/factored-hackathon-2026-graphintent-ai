from datetime import datetime
from pathlib import Path
from typing import Optional, Union

import pandas as pd

from app.backend.db.duckdb import DuckDBDatabase

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
]

INQUIRY_KEYWORDS = [
    "saldo",
    "consulta",
    "estado de cuenta",
    "disponible",
    "saldo disponible",
    "consulta_saldo",
    "balance",
    "movimientos",
]

COMPLAINT_KEYWORDS = [
    "reclamo",
    "queja",
    "disputa",
    "cobro duplicado",
    "unauthorized",
    "falsificación",
    "fraud",
    "impugnación",
    "cargo no reconocido",
]


def assign_target_label(row: pd.Series) -> str:
    # Concatenar todos los campos de texto
    text = (
        f"{row.get('full_text', '')} {row.get('detected_keywords', '')} "
        f"{row.get('detected_intents', '')} {row.get('main_topics', '')}"
    ).lower()

    # Evaluar primero coincidencia con consulta de saldo/cuenta
    if any(kw in text for kw in INQUIRY_KEYWORDS):
        return "account_inquiry"

    # Evaluar si contiene términos de disputa o reclamo
    if any(kw in text for kw in COMPLAINT_KEYWORDS):
        return "dispute_initiate"

    # Si viene del dataframe de reclamos/complaints explícito
    if row.get("source") == "complaints":
        return "dispute_initiate"

    # Si es ambiguo o neutro, asignamos por defecto la
    # consulta para no inflar la clase disputa
    return "account_inquiry"


def load_and_prepare_data(
    data_dir: Union[Path, str],
    start_date: Optional[datetime] = None,
    days_back: int = 30,
) -> pd.DataFrame:
    """
    Extract raw data using DuckDB (Local or S3), build engineered features,
    and return clean DataFrame.
    """
    # Usamos la abstracción de DuckDBDatabase para
    # gestionar credenciales y conexión S3
    db = DuckDBDatabase(data_path=str(data_dir))
    con = db.con

    if start_date is None:
        start_date = datetime.now()

    year_str = start_date.strftime("%Y")
    month_str = start_date.strftime("%m")

    # Construcción de paths optimizados para S3 usando Hive Partitioning
    if db.is_s3:
        transcripts_path = db._get_partitioned_path(
            "call_transcripts", year=year_str, month=month_str
        )
        interactions_path = db._get_partitioned_path(
            "call_center_interactions", year=year_str, month=month_str
        )
        complaints_path = db._get_partitioned_path("complaints")

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
            FROM read_csv_auto('{transcripts_path}', 
                hive_partitioning=1) t
            INNER JOIN read_csv_auto('{interactions_path}', 
                hive_partitioning=1) i
                ON t.interaction_id = i.interaction_id
            WHERE t.full_text IS NOT NULL AND LENGTH(TRIM(t.full_text)) > 0
        """

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
            FROM read_csv_auto('{complaints_path}', hive_partitioning=1) c
            WHERE c.description IS NOT NULL AND LENGTH(TRIM(c.description)) > 0
        """

        # complaints_dist_query = f"""
        #    SELECT DISTINCT customer_id
        #    FROM read_csv_auto('{complaints_path}', hive_partitioning=1)
        #    WHERE customer_id IS NOT NULL
        # """
    else:
        # Lógica Fallback para disco local (data/sample)
        query_interactions = f"""
            SELECT 
                t.full_text, t.detected_keywords, 
                t.detected_intents, t.main_topics,
                i.channel, i.detected_sentiment,
                i.duration_seconds, i.wait_time_seconds,
                i.sentiment_score, i.contact_reason, 
                i.was_escalated, i.customer_id
            FROM '{data_dir}/call_transcripts/*.csv' t
            INNER JOIN '{data_dir}/call_center_interactions/*.csv' i 
                ON t.interaction_id = i.interaction_id
            WHERE t.full_text IS NOT NULL AND LENGTH(TRIM(t.full_text)) > 0
        """
        query_complaints = f"""
            SELECT 
                c.description AS full_text, c.category AS detected_keywords,
                c.subcategory AS detected_intents, c.case_type AS main_topics,
                'chat' AS channel, 'negative' AS detected_sentiment,
                0.0 AS duration_seconds, 0.0 AS wait_time_seconds,
                -0.8 AS sentiment_score, 'complaint' AS contact_reason,
                FALSE AS was_escalated, c.customer_id
            FROM '{data_dir}/complaints/*.csv' c
            WHERE c.description IS NOT NULL AND LENGTH(TRIM(c.description)) > 0
        """
        # complaints_dist_query = f"""
        #    SELECT DISTINCT customer_id
        #    FROM '{data_dir}/complaints/*.csv'
        #    WHERE customer_id IS NOT NULL
        # """

    # Ejecución de queries
    try:
        df_interactions = con.execute(query_interactions).df()
    except Exception:
        df_interactions = pd.DataFrame()

    try:
        df_complaints = con.execute(query_complaints).df()
    except Exception:
        df_complaints = pd.DataFrame()

    df = pd.concat([df_interactions, df_complaints], ignore_index=True)

    for col in TEXT_COLS:
        if col in df.columns:
            df[col] = df[col].fillna("")

    if not df.empty:
        df["rich_text"] = (
            df["full_text"]
            + " "
            + df["detected_keywords"]
            + " "
            + df["detected_intents"]
            + " "
            + df["main_topics"]
        )

        # try:
        #    complaint_customers = set(
        #        con.execute(complaints_dist_query).df()["customer_id"].astype(str)
        #    )
        # except Exception:
        #    complaint_customers = set()

        df["label"] = df.apply(assign_target_label, axis=1)

    return df


def save_training_data(df: pd.DataFrame, output_path: Path) -> None:
    """Persist the prepared training dataset locally in Parquet format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Dataset de entrenamiento guardado exitosamente en: {output_path}")


def get_or_create_dataset(
    data_dir: Union[Path, str],
    processed_parquet_path: Path,
    start_date: Optional[datetime] = None,
    days_back: int = 30,
    force_rebuild: bool = False,
) -> pd.DataFrame:
    """
    Obtiene el dataset guardado en Parquet. Si no existe o se fuerza el rebuild,
    ejecuta la extracción DuckDB y lo guarda en disco.
    """
    if processed_parquet_path.exists() and not force_rebuild:
        print(f"Cargando dataset preprocesado desde: {processed_parquet_path}")
        return pd.read_parquet(processed_parquet_path)

    print("Generando nuevo dataset de entrenamiento con DuckDB...")
    df = load_and_prepare_data(
        data_dir=data_dir,
        start_date=start_date,
        days_back=days_back,
    )
    save_training_data(df, processed_parquet_path)
    return df
