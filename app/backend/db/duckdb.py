# app/backend/db/duckdb_db.py
import os
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
from dotenv import load_dotenv

from app.backend.db.base import BaseDatabase
from app.backend.schemas.dispute import (
    ComplaintSchema,
    Transaction,
    TransactionSchema,
)

BASE_DIR = Path(__file__).parent.parent.parent.parent.resolve()
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)


class DuckDBDatabase(BaseDatabase):
    """DuckDB Database connector supporting local
    CSV/Parquet paths and AWS S3 buckets.
    """

    def __init__(self, data_path: Optional[str] = None):
        self.con = duckdb.connect(database=":memory:")

        bucket_name = os.getenv("S3_BUCKET_NAME") or os.getenv("AWS_S3_BUCKET_NAME")

        if bucket_name:
            if not bucket_name.startswith("s3://"):
                bucket_name = f"s3://{bucket_name}/data"

            self.data_path = bucket_name.rstrip("/")
            self.is_s3 = True
            self._init_s3_credentials()
        else:
            local_dir = data_path or "data/sample"
            self.data_path = str(BASE_DIR / "app" / local_dir.rstrip("/"))
            self.is_s3 = False

        print(f"--> DuckDB iniciado apuntando a: {self.data_path}")

    def _init_s3_credentials(self):
        """Configure AWS S3 credentials and thread/read performance
        optimizations in DuckDB."""
        aws_key = os.getenv("AWS_ACCESS_KEY_ID", "")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "")
        aws_region = os.getenv("AWS_REGION", "us-east-1")

        self.con.execute("INSTALL httpfs;")
        self.con.execute("LOAD httpfs;")
        self.con.execute(f"SET s3_region='{aws_region}';")
        self.con.execute(f"SET s3_access_key_id='{aws_key}';")
        self.con.execute(f"SET s3_secret_access_key='{aws_secret}';")

        self.con.execute("SET threads TO 8;")
        self.con.execute("SET preserve_insertion_order=false;")

    def _get_partitioned_path(
        self,
        folder_name: str,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
        extension: str = "csv",
    ) -> str:
        """
        Genera la ruta para estructuras particionadas.
        Por defecto filtra por el año actual ('2026').
        Se pueden pasar month y day opcionales.
        """
        y_str = f"year={year}" if year else "year=*"
        m_str = f"month={str(month).zfill(2)}" if month else "month=*"
        d_str = f"day={str(day).zfill(2)}" if day else "day=*"

        if self.is_s3:
            return (
                f"{self.data_path}/{folder_name}/{y_str}/{m_str}/{d_str}/*.{extension}"
            )

        local_single_file = Path(self.data_path) / f"{folder_name}.{extension}"
        if local_single_file.exists():
            return str(local_single_file)
        return f"{self.data_path}/{folder_name}/{y_str}/{m_str}/{d_str}/*.{extension}"

    def _read_table(
        self, path: str, start_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """Lee la tabla aplicando filtro de fecha cuando se proporcione."""
        reader_fn = "read_parquet" if path.endswith(".parquet") else "read_csv_auto"

        if start_date:
            date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
            query = (
                f"SELECT * FROM {reader_fn}('{path}', hive_partitioning=1)"
                f" WHERE transaction_date >= TIMESTAMP '{date_str}'"
            )
        else:
            query = f"SELECT * FROM {reader_fn}('{path}', hive_partitioning=1)"

        return self.con.execute(query).df()

    def _query_table(self, path: str, condition_sql: str, params: list) -> pd.DataFrame:
        """Ejecuta una consulta filtrada sobre un archivo
        o estructura particionada."""
        reader_fn = "read_parquet" if path.endswith(".parquet") else "read_csv_auto"
        query = (
            f"SELECT * FROM {reader_fn}('{path}', hive_partitioning=1) "
            f"WHERE {condition_sql}"
        )
        return self.con.execute(query, params).df()

    def _get_file_path(self, filename: str) -> str:
        return f"{self.data_path}/{filename}"

    # --- MÉTODOS PARA CARPETAS PARTICIONADAS EN S3 ---

    def get_call_center_interactions(
        self,
        customer_id: Optional[str] = None,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "call_center_interactions", year=year, month=month, day=day
        )
        if customer_id:
            res = self._query_table(path, "customer_id = ?", [customer_id])
        else:
            res = self._read_table(path)
        return res.to_dict(orient="records") if not res.empty else []

    def get_call_transcripts(
        self,
        customer_id: Optional[str] = None,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "call_transcripts", year=year, month=month, day=day
        )
        if customer_id:
            res = self._query_table(path, "customer_id = ?", [customer_id])
        else:
            res = self._read_table(path)
        return res.to_dict(orient="records") if not res.empty else []

    def get_campaign_sends(
        self,
        customer_id: Optional[str] = None,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "campaign_sends", year=year, month=month, day=day
        )
        if customer_id:
            res = self._query_table(path, "customer_id = ?", [customer_id])
        else:
            res = self._read_table(path)
        return res.to_dict(orient="records") if not res.empty else []

    def get_digital_events(
        self,
        customer_id: Optional[str] = None,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "digital_events", year=year, month=month, day=day
        )
        if customer_id:
            res = self._query_table(path, "customer_id = ?", [customer_id])
        else:
            res = self._read_table(path)
        return res.to_dict(orient="records") if not res.empty else []

    def get_satisfaction_surveys(
        self,
        customer_id: Optional[str] = None,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "satisfaction_surveys", year=year, month=month, day=day
        )
        if customer_id:
            res = self._query_table(path, "customer_id = ?", [customer_id])
        else:
            res = self._read_table(path)
        return res.to_dict(orient="records") if not res.empty else []

    # --- IMPLEMENTACIÓN BASE DATABASE ---

    def get_customer(self, customer_id: str) -> Optional[dict]:
        path = self._get_file_path("customers.csv")
        res = self._query_table(path, "customer_id = ?", [customer_id])
        return res.iloc[0].to_dict() if not res.empty else None

    def get_customer_by_document(
        self, document_type: str, document_number: str
    ) -> Optional[dict]:
        path = self._get_file_path("customers.csv")
        cond = (
            "UPPER(CAST(document_type AS VARCHAR)) = UPPER(?) "
            "AND CAST(document_number AS VARCHAR) = CAST(? AS VARCHAR)"
        )
        res = self._query_table(path, cond, [document_type, str(document_number)])
        return res.iloc[0].to_dict() if not res.empty else None

    def get_product(self, product_id: str) -> Optional[dict]:
        path = self._get_file_path("products.csv")
        res = self._query_table(path, "product_id = ?", [product_id])
        return res.iloc[0].to_dict() if not res.empty else None

    def get_transaction(
        self,
        transaction_id: str,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> Optional[TransactionSchema]:
        path = self._get_partitioned_path(
            "transactions", year=year, month=month, day=day
        )
        res = self._query_table(path, "transaction_id = ?", [transaction_id])
        if res.empty:
            return None
        row = res.iloc[0]
        return TransactionSchema(
            transaction_id=str(row["transaction_id"]),
            transaction_date=pd.to_datetime(row["transaction_date"]).to_pydatetime(),
            product_id=str(row["product_id"]),
            customer_id=str(row["customer_id"]),
            transaction_type=str(row["transaction_type"]),
            amount=Decimal(str(row["amount"])),
            currency=str(row["currency"]),
            merchant_name=str(row.get("merchant_name", "")),
            transaction_country=str(row.get("transaction_country", "")),
            transaction_status=str(row.get("transaction_status", "Approved")),
        )

    def get_customer_transactions(
        self,
        customer_id: str,
        days_back: int = 7,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[TransactionSchema]:
        path = self._get_partitioned_path(
            "transactions", year=year, month=month, day=day
        )

        # Filtro de ventana de tiempo (por defecto 7 días atrás)
        if days_back:
            start_date = datetime.now() - timedelta(days=days_back)
            date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
            cond = "customer_id = ? AND transaction_date >= TIMESTAMP ?"
            params = [customer_id, date_str]
        else:
            cond = "customer_id = ?"
            params = [customer_id]

        res = self._query_table(path, cond, params)
        txs = []
        for _, row in res.iterrows():
            txs.append(
                TransactionSchema(
                    transaction_id=str(row["transaction_id"]),
                    transaction_date=pd.to_datetime(
                        row["transaction_date"]
                    ).to_pydatetime(),
                    product_id=str(row["product_id"]),
                    customer_id=str(row["customer_id"]),
                    transaction_type=str(row["transaction_type"]),
                    amount=Decimal(str(row["amount"])),
                    currency=str(row["currency"]),
                    merchant_name=str(row.get("merchant_name", "")),
                    transaction_country=str(row.get("transaction_country", "")),
                    transaction_status=str(row.get("transaction_status", "Approved")),
                )
            )
        return txs

    def create_complaint(self, complaint: ComplaintSchema) -> ComplaintSchema:
        return complaint

    def get_complaint(
        self,
        complaint_id: str,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> Optional[ComplaintSchema]:
        path = self._get_partitioned_path("complaints", year=year, month=month, day=day)
        res = self._query_table(path, "complaint_id = ?", [complaint_id])
        if res.empty:
            return None
        row = res.iloc[0]
        return ComplaintSchema(
            complaint_id=str(row["complaint_id"]),
            creation_date=pd.to_datetime(row["creation_date"]).to_pydatetime(),
            customer_id=str(row["customer_id"]),
            claimed_amount=Decimal(str(row.get("claimed_amount", 0))),
            currency=str(row.get("currency", "USD")),
            status=str(row.get("status", "Open")),
        )

    def get_frontend_transactions(
        self,
        days_back: int = 7,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[Transaction]:
        path = self._get_partitioned_path(
            "transactions", year=year, month=month, day=day
        )
        start_date = datetime.now() - timedelta(days=days_back) if days_back else None

        res = self._read_table(path, start_date=start_date)
        frontend_list = []
        for _, row in res.iterrows():
            status = (
                "disputed"
                if str(row.get("transaction_status")) == "Reversed"
                else "posted"
            )
            frontend_list.append(
                Transaction(
                    id=str(row["transaction_id"]),
                    merchant=str(row.get("merchant_name", "Comercio")),
                    amount=float(row["amount"]),
                    currency=str(row["currency"]),
                    date=str(row["transaction_date"]),
                    status=status,
                )
            )
        return frontend_list

    def update_transaction_status(self, transaction_id: str, new_status: str) -> bool:
        return True

    def get_customer_products(self, customer_id: str) -> list[dict]:
        path = self._get_file_path("products.csv")
        res = self._query_table(path, "customer_id = ?", [customer_id])
        return res.to_dict(orient="records") if not res.empty else []

    def get_active_complaints(
        self,
        customer_id: str,
        year: Optional[str] = "2026",
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[ComplaintSchema]:
        path = self._get_partitioned_path("complaints", year=year, month=month, day=day)
        res = self._query_table(
            path, "customer_id = ? AND status IN ('Open', 'In Process')", [customer_id]
        )
        complaints = []
        for _, row in res.iterrows():
            complaints.append(
                ComplaintSchema(
                    complaint_id=str(row["complaint_id"]),
                    creation_date=pd.to_datetime(row["creation_date"]).to_pydatetime(),
                    customer_id=str(row["customer_id"]),
                    claimed_amount=Decimal(str(row.get("claimed_amount", 0))),
                    currency=str(row.get("currency", "USD")),
                    status=str(row.get("status", "Open")),
                )
            )
        return complaints

    def get_exchange_rate(
        self, source_currency: str, target_currency: str = "USD"
    ) -> float:
        rates = {
            ("COP", "USD"): 0.00025,
            ("MXN", "USD"): 0.058,
            ("ARS", "USD"): 0.0011,
            ("USD", "USD"): 1.0,
        }
        return rates.get((source_currency, target_currency), 1.0)


if __name__ == "__main__":
    con = DuckDBDatabase()
