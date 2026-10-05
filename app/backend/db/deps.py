# app/backend/db/deps.py
import os
from pathlib import Path

from app.backend.db.base import BaseDatabase
from app.backend.db.duckdb_client import DuckDBDatabase
from app.backend.db.mock_db import MockDatabase

BASE_DIR = Path(__file__).parent.parent.parent.parent.resolve()
env_path = BASE_DIR / ".env"

USE_DUCKDB = os.getenv("USE_DUCKDB", "false").lower() == "true"
if USE_DUCKDB:
    S3_BUCKET = os.getenv("AWS_S3_BUCKET_URL")  # ej: s3://mi-bucket/datos
    LOCAL_DATA_DIR = BASE_DIR / "app" / "data" / "sample"

    # Si existe variable S3 usamos la nube, de lo contrario usamos la ruta local
    data_source = S3_BUCKET if S3_BUCKET else LOCAL_DATA_DIR
    _db_instance: BaseDatabase = DuckDBDatabase(data_path=data_source)
else:
    _db_instance: BaseDatabase = MockDatabase()


def get_db() -> BaseDatabase:
    return _db_instance
