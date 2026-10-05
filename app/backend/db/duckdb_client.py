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

# Fecha de referencia por defecto para todas las consultas (30 de Junio de 2026)
REFERENCE_DATE = datetime(2026, 6, 30, 23, 59, 59)


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
        """Configure AWS S3 credentials and performance optimizations."""
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
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
        extension: str = "csv",
    ) -> str:
        """Genera la ruta para estructuras particionadas.
        Si no se pasan parametros de fecha, se usará el wildcard restringido.
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
        try:
            reader_fn = "read_parquet" if path.endswith(".parquet") else "read_csv_auto"

            if start_date:
                date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
                query = (
                    f"SELECT * FROM {reader_fn}('{path}', hive_partitioning=1)"
                    f" WHERE transaction_date >= '{date_str}'::TIMESTAMP"
                )
            else:
                query = f"SELECT * FROM {reader_fn}('{path}', hive_partitioning=1)"

            res = self.con.execute(query).df()
            if res is not None and not res.empty:
                res.columns = [str(c).lower() for c in res.columns]
                return res
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def _query_table(self, path: str, condition_sql: str, params: list) -> pd.DataFrame:
        """Ejecuta una consulta filtrada retornando un DataFrame en minúsculas."""
        try:
            reader_fn = "read_parquet" if path.endswith(".parquet") else "read_csv_auto"
            query = (
                f"SELECT * FROM {reader_fn}('{path}', hive_partitioning=1) "
                f"WHERE {condition_sql}"
            )
            res = self.con.execute(query, params).df()
            if res is not None and not res.empty:
                res.columns = [str(c).lower() for c in res.columns]
                return res
            return pd.DataFrame()
        except Exception:
            return pd.DataFrame()

    def _get_file_path(self, filename: str) -> str:
        return f"{self.data_path}/{filename}"

    # --- MÉTODOS PARA CARPETAS PARTICIONADAS EN S3 ---

    def get_call_center_interactions(
        self,
        customer_id: Optional[str] = None,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "call_center_interactions", year=year, month=month, day=day
        )
        cond = "customer_id = ?" if customer_id else "1=1"
        params = [customer_id] if customer_id else []
        res = self._query_table(path, cond, params)
        return (
            res.to_dict(orient="records") if (res is not None and not res.empty) else []
        )

    def get_call_transcripts(
        self,
        customer_id: Optional[str] = None,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "call_transcripts", year=year, month=month, day=day
        )
        cond = "customer_id = ?" if customer_id else "1=1"
        params = [customer_id] if customer_id else []
        res = self._query_table(path, cond, params)
        return (
            res.to_dict(orient="records") if (res is not None and not res.empty) else []
        )

    def get_campaign_sends(
        self,
        customer_id: Optional[str] = None,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "campaign_sends", year=year, month=month, day=day
        )
        cond = "customer_id = ?" if customer_id else "1=1"
        params = [customer_id] if customer_id else []
        res = self._query_table(path, cond, params)
        return (
            res.to_dict(orient="records") if (res is not None and not res.empty) else []
        )

    def get_digital_events(
        self,
        customer_id: Optional[str] = None,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "digital_events", year=year, month=month, day=day
        )
        cond = "customer_id = ?" if customer_id else "1=1"
        params = [customer_id] if customer_id else []
        res = self._query_table(path, cond, params)
        return (
            res.to_dict(orient="records") if (res is not None and not res.empty) else []
        )

    def get_satisfaction_surveys(
        self,
        customer_id: Optional[str] = None,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[dict]:
        path = self._get_partitioned_path(
            "satisfaction_surveys", year=year, month=month, day=day
        )
        cond = "customer_id = ?" if customer_id else "1=1"
        params = [customer_id] if customer_id else []
        res = self._query_table(path, cond, params)
        return (
            res.to_dict(orient="records") if (res is not None and not res.empty) else []
        )

    # --- IMPLEMENTACIÓN BASE DATABASE ---

    def get_customer(self, customer_id: str) -> Optional[dict]:
        path = self._get_file_path("customers.csv")
        res = self._query_table(path, "customer_id = ?", [customer_id])
        return res.iloc[0].to_dict() if (res is not None and not res.empty) else None

    def get_customer_by_document(
        self, document_type: str, document_number: str
    ) -> Optional[dict]:
        path = self._get_file_path("customers.csv")
        cond = (
            "UPPER(CAST(document_type AS VARCHAR)) = UPPER(?) "
            "AND CAST(document_number AS VARCHAR) = CAST(? AS VARCHAR)"
        )
        res = self._query_table(path, cond, [document_type, str(document_number)])
        return res.iloc[0].to_dict() if (res is not None and not res.empty) else None

    def get_product(self, product_id: str) -> Optional[dict]:
        path = self._get_file_path("products.csv")
        res = self._query_table(path, "product_id = ?", [product_id])
        return res.iloc[0].to_dict() if (res is not None and not res.empty) else None

    def get_transaction(
        self,
        transaction_id: str,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> Optional[TransactionSchema]:
        path = self._get_partitioned_path(
            "transactions", year=year, month=month, day=day
        )
        res = self._query_table(path, "transaction_id = ?", [transaction_id])
        if res is None or res.empty or "transaction_id" not in res.columns:
            return None
        row = res.iloc[0]
        return TransactionSchema(
            transaction_id=str(row.get("transaction_id", "")),
            transaction_date=pd.to_datetime(
                row.get("transaction_date", REFERENCE_DATE)
            ).to_pydatetime(),
            product_id=str(row.get("product_id", "")),
            customer_id=str(row.get("customer_id", "")),
            transaction_type=str(row.get("transaction_type", "Debit")),
            amount=Decimal(str(row.get("amount", "0"))),
            currency=str(row.get("currency", "USD")),
            merchant_name=str(row.get("merchant_name", "")),
            transaction_country=str(row.get("transaction_country", "")),
            transaction_status=str(row.get("transaction_status", "Approved")),
        )

    def get_customer_transactions(
        self,
        customer_id: str,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[TransactionSchema]:
        ref_date = REFERENCE_DATE
        if not year and days_back:
            year = str(ref_date.year)

        path = self._get_partitioned_path(
            "transactions", year=year, month=month, day=day
        )

        if days_back:
            start_date = ref_date - timedelta(days=days_back)
            date_str = start_date.strftime("%Y-%m-%d %H:%M:%S")
            end_date_str = ref_date.strftime("%Y-%m-%d %H:%M:%S")
            cond = (
                "customer_id = ? AND transaction_date "
                "BETWEEN ?::TIMESTAMP AND ?::TIMESTAMP"
            )
            params = [customer_id, date_str, end_date_str]
        else:
            cond = "customer_id = ?"
            params = [customer_id]

        res = self._query_table(path, cond, params)

        if res is None or res.empty or "transaction_id" not in res.columns:
            return []

        txs = []
        for _, row in res.iterrows():
            txs.append(
                TransactionSchema(
                    transaction_id=str(row.get("transaction_id", "")),
                    transaction_date=pd.to_datetime(
                        row.get("transaction_date", ref_date)
                    ).to_pydatetime(),
                    product_id=str(row.get("product_id", "")),
                    customer_id=str(row.get("customer_id", customer_id)),
                    transaction_type=str(row.get("transaction_type", "Debit")),
                    amount=Decimal(str(row.get("amount", "0"))),
                    currency=str(row.get("currency", "USD")),
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
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> Optional[ComplaintSchema]:
        path = self._get_partitioned_path("complaints", year=year, month=month, day=day)
        res = self._query_table(path, "complaint_id = ?", [complaint_id])
        if res is None or res.empty or "complaint_id" not in res.columns:
            return None
        row = res.iloc[0]
        return ComplaintSchema(
            complaint_id=str(row.get("complaint_id", "")),
            creation_date=pd.to_datetime(
                row.get("creation_date", REFERENCE_DATE)
            ).to_pydatetime(),
            customer_id=str(row.get("customer_id", "")),
            claimed_amount=Decimal(str(row.get("claimed_amount", 0))),
            currency=str(row.get("currency", "USD")),
            status=str(row.get("status", "Open")),
        )

    def get_frontend_transactions(
        self,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[Transaction]:
        ref_date = REFERENCE_DATE
        path = self._get_partitioned_path(
            "transactions", year=year, month=month, day=day
        )
        start_date = ref_date - timedelta(days=days_back) if days_back else None

        res = self._read_table(path, start_date=start_date)
        if res is None or res.empty or "transaction_id" not in res.columns:
            return []

        frontend_list = []
        for _, row in res.iterrows():
            status = (
                "disputed"
                if str(row.get("transaction_status", "")) == "Reversed"
                else "posted"
            )
            frontend_list.append(
                Transaction(
                    id=str(row.get("transaction_id", "")),
                    merchant=str(row.get("merchant_name", "Comercio")),
                    amount=float(row.get("amount", 0.0)),
                    currency=str(row.get("currency", "USD")),
                    date=str(row.get("transaction_date", "")),
                    status=status,
                )
            )
        return frontend_list

    def update_transaction_status(self, transaction_id: str, new_status: str) -> bool:
        return True

    def get_customer_products(self, customer_id: str) -> list[dict]:
        path = self._get_file_path("products.csv")
        res = self._query_table(path, "customer_id = ?", [customer_id])
        return (
            res.to_dict(orient="records") if (res is not None and not res.empty) else []
        )

    def get_active_complaints(
        self,
        customer_id: str,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[ComplaintSchema]:
        ref_date = REFERENCE_DATE
        if not year and days_back:
            year = str(ref_date.year)

        path = self._get_partitioned_path("complaints", year=year, month=month, day=day)

        if days_back:
            start_date = ref_date - timedelta(days=days_back)
            cond = (
                "customer_id = ? AND status IN ('Open', 'In Process') AND "
                "creation_date BETWEEN ?::TIMESTAMP AND ?::TIMESTAMP"
            )
            params = [
                customer_id,
                start_date.strftime("%Y-%m-%d %H:%M:%S"),
                ref_date.strftime("%Y-%m-%d %H:%M:%S"),
            ]
        else:
            cond = "customer_id = ? AND status IN ('Open', 'In Process')"
            params = [customer_id]

        res = self._query_table(path, cond, params)
        if res is None or res.empty or "complaint_id" not in res.columns:
            return []

        complaints = []
        for _, row in res.iterrows():
            complaints.append(
                ComplaintSchema(
                    complaint_id=str(row.get("complaint_id", "")),
                    creation_date=pd.to_datetime(
                        row.get("creation_date", ref_date)
                    ).to_pydatetime(),
                    customer_id=str(row.get("customer_id", customer_id)),
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
