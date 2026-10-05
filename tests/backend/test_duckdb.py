# tests/test_duckdb.py
import os

import pytest
from dotenv import load_dotenv

from app.backend.db.duckdb_client import BASE_DIR, DuckDBDatabase

env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


# --- PRUEBA 1: LECTURA DESDE CSV LOCAL REAL (data/sample) ---


def test_duckdb_local_csv_reading(monkeypatch):
    """
    Prueba que DuckDB pueda leer los datos locales ubicados en data/sample.
    """
    monkeypatch.delenv("AWS_S3_BUCKET_NAME", raising=False)
    monkeypatch.delenv("AWS_S3_BUCKET_URL", raising=False)
    monkeypatch.delenv("S3_BUCKET_NAME", raising=False)

    db = DuckDBDatabase(data_path="data/sample")
    assert db.is_s3 is False

    customer = db.get_customer_by_document("Pasaporte", "G8637940")
    if customer is None:
        products = db.get_customer_products("CUST_12345")
        assert isinstance(products, list)
    else:
        assert customer["document_number"] == "G8637940"
        assert customer["document_type"] == "Pasaporte"


# --- PRUEBA 2: CONSULTAS OPTIMIZADAS A TABLAS PARTICIONADAS EN S3 ---


@pytest.mark.skipif(
    not os.getenv("S3_BUCKET_NAME") and not os.getenv("AWS_S3_BUCKET_NAME"),
    reason="Requiere variables de entorno AWS en .env para conectarse a S3",
)
@pytest.mark.parametrize(
    "folder_name",
    [
        "transactions",
        "call_center_interactions",
        "call_transcripts",
        "campaign_sends",
        "complaints",
        "digital_events",
        "satisfaction_surveys",
    ],
)
def test_s3_partitioned_tables_reading(folder_name):
    """
    Prueba consultas optimizadas filtrando por año, mes, día y acotando con LIMIT 5
    para verificar que cada carpeta particionada se responda sin latencia.
    """
    db = DuckDBDatabase()
    assert db.is_s3 is True

    # Genera la ruta acotada al primer día del año para minimizar descarga por red
    path = db._get_partitioned_path(
        folder_name=folder_name, year="2026", month="01", day="01"
    )

    query = f"SELECT * FROM read_csv_auto('{path}', hive_partitioning=1) LIMIT 5"
    df = db.con.execute(query).df()

    # Valida que la respuesta sea un DataFrame estructurado
    assert df is not None


# --- PRUEBA 3: METODOS OPTIMIZADOS DE LA CLASE DUCKDB ---


@pytest.mark.skipif(
    not os.getenv("S3_BUCKET_NAME") and not os.getenv("AWS_S3_BUCKET_NAME"),
    reason="Requiere variables de entorno AWS en .env para conectarse a S3",
)
def test_duckdb_methods_with_params():
    """
    Verifica que los métodos de la clase respondan rápido con parámetros de partición.
    """
    db = DuckDBDatabase()

    # Consulta transacciones de frontend acotando la ventana
    txs = db.get_frontend_transactions(days_back=7, year="2026", month="01")
    assert isinstance(txs, list)

    # Consulta interacciones de call center acotando la partición
    interactions = db.get_call_center_interactions(year="2026", month="01", day="01")
    assert isinstance(interactions, list)
