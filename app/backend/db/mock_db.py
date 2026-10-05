from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

import pandas as pd

from app.backend.db.base import BaseDatabase
from app.backend.schemas.dispute import (
    ComplaintSchema,
    Transaction,
    TransactionSchema,
)


class MockDatabase(BaseDatabase):
    """In-memory database loader that populates from local sample CSVs."""

    def __init__(self, data_dir: str = "data/sample"):
        self.data_dir = Path(data_dir).parent.parent.resolve() / "app" / data_dir
        # print(f"DATA_DIR:{self.data_dir}")
        self._customers: dict[str, dict] = {}
        self._products: dict[str, dict] = {}
        self._transactions: dict[str, TransactionSchema] = {}
        self._complaints: dict[str, ComplaintSchema] = {}

        # Load real local data or fallback to mock fixtures
        # self._load_sample_data()
        # If no CSVs were found, seed standard fallback mock data
        self._seed_fallback_data()

    def _load_sample_data(self):
        """Read CSV files from data/sample if present, else seed mock defaults."""
        loaded_any = False

        # 1. Load Customers
        customers_file = self.data_dir / "customers.csv"
        print(f"Customers file: {customers_file}")
        if customers_file.exists():
            print("Reading customers")
            df_cust = pd.read_csv(customers_file)
            for _, row in df_cust.iterrows():
                c_id = str(row["customer_id"])
                self._customers[c_id] = row.to_dict()
            loaded_any = True

        # 2. Load Products
        products_file = self.data_dir / "products.csv"
        if products_file.exists():
            df_prod = pd.read_csv(products_file)
            for _, row in df_prod.iterrows():
                p_id = str(row["product_id"])
                self._products[p_id] = row.to_dict()
            loaded_any = True

        # 3. Load Transactions
        tx_file = self.data_dir / "transactions.csv"
        if tx_file.exists():
            df_tx = pd.read_csv(tx_file)
            for _, row in df_tx.iterrows():
                tx_id = str(row["transaction_id"])
                # Map pandas row to Pydantic TransactionSchema
                self._transactions[tx_id] = TransactionSchema(
                    transaction_id=tx_id,
                    transaction_date=pd.to_datetime(
                        row["transaction_date"]
                    ).to_pydatetime(),
                    product_id=str(row["product_id"]),
                    customer_id=str(row["customer_id"]),
                    transaction_type=str(row["transaction_type"]),
                    amount=Decimal(str(row["amount"])),
                    currency=str(row["currency"]),
                    amount_usd=(
                        Decimal(str(row["amount_usd"]))
                        if pd.notna(row.get("amount_usd"))
                        else None
                    ),
                    merchant_name=(
                        str(row["merchant_name"])
                        if pd.notna(row.get("merchant_name"))
                        else None
                    ),
                    merchant_category=(
                        str(row["merchant_category"])
                        if pd.notna(row.get("merchant_category"))
                        else None
                    ),
                    transaction_country=str(row["transaction_country"]),
                    transaction_status=str(row["transaction_status"]),
                    is_fraud=bool(row.get("is_fraud", False)),
                    fraud_score=(
                        Decimal(str(row["fraud_score"]))
                        if pd.notna(row.get("fraud_score"))
                        else None
                    ),
                )
            loaded_any = True

        # 4. Load Complaints
        complaints_file = self.data_dir / "complaints.csv"
        if complaints_file.exists():
            df_comp = pd.read_csv(complaints_file)
            for _, row in df_comp.iterrows():
                comp_id = str(row["complaint_id"])
                self._complaints[comp_id] = ComplaintSchema(
                    complaint_id=comp_id,
                    creation_date=pd.to_datetime(row["creation_date"]).to_pydatetime(),
                    customer_id=str(row["customer_id"]),
                    case_type=str(row.get("case_type", "Claim")),
                    category=str(row.get("category", "Transaction Dispute")),
                    affected_product_id=(
                        str(row["affected_product_id"])
                        if pd.notna(row.get("affected_product_id"))
                        else None
                    ),
                    claimed_amount=(
                        Decimal(str(row["claimed_amount"]))
                        if pd.notna(row.get("claimed_amount"))
                        else None
                    ),
                    currency=(
                        str(row["currency"]) if pd.notna(row.get("currency")) else None
                    ),
                    priority=str(row.get("priority", "Medium")),
                    status=str(row.get("status", "Open")),
                    assigned_agent_id=(
                        str(row["assigned_agent_id"])
                        if pd.notna(row.get("assigned_agent_id"))
                        else None
                    ),
                    resolution=(
                        str(row["resolution"])
                        if pd.notna(row.get("resolution"))
                        else None
                    ),
                    sla_breached=bool(row.get("sla_breached", False)),
                )
            loaded_any = True
        return loaded_any

    def _seed_fallback_data(self):
        """Seed default mock records if CSVs are missing."""
        cust_id = "CUST_12345"
        prod_id = "PROD_CARD_01"

        # 1. Datos de cliente
        self._customers[cust_id] = {
            "customer_id": cust_id,
            "first_name": "Carlos",
            "last_name": "Mendoza",
            "document_type": "CC",
            "document_number": "1098765432",
            "country": "Mexico",
            "detected_accent": "mexican",
            "segment": "Premium",
            "customer_status": "Active",
        }

        # 2. Productos financieros del cliente
        self._products[prod_id] = {
            "product_id": prod_id,
            "customer_id": cust_id,
            "product_type": "Credit Card",
            "currency": "MXN",
            "current_balance": Decimal("45000.00"),
            "credit_limit": Decimal("100000.00"),
            "product_status": "Active",
        }

        prod_savings_id = "PROD_SAV_02"
        self._products[prod_savings_id] = {
            "product_id": prod_savings_id,
            "customer_id": cust_id,
            "product_type": "Savings Account",
            "currency": "MXN",
            "current_balance": Decimal("125000.50"),
            "product_status": "Active",
        }

        # 3. Transacciones de prueba
        mock_txs = [
            TransactionSchema(
                transaction_id="TX_1001",
                transaction_date=datetime(2026, 10, 1),
                product_id=prod_id,
                customer_id=cust_id,
                transaction_type="Purchase",
                amount=Decimal("45.50"),
                currency="USD",
                amount_usd=Decimal("45.50"),
                merchant_name="Uber Trip",
                merchant_category="Transportation",
                transaction_country="Mexico",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("2.1"),
            ),
            TransactionSchema(
                transaction_id="TX_1002",
                transaction_date=datetime(2026, 9, 28),
                product_id=prod_id,
                customer_id=cust_id,
                transaction_type="Purchase",
                amount=Decimal("150.00"),
                currency="USD",
                amount_usd=Decimal("150.00"),
                merchant_name="Unknown Electronics Store",
                merchant_category="Digital Goods",
                transaction_country="Mexico",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("12.5"),
            ),
            TransactionSchema(
                transaction_id="TX_1003",
                transaction_date=datetime(2026, 9, 25),
                product_id=prod_id,
                customer_id=cust_id,
                transaction_type="Purchase",
                amount=Decimal("4.75"),
                currency="USD",
                amount_usd=Decimal("4.75"),
                merchant_name="Coffee Shop",
                merchant_category="Food & Beverage",
                transaction_country="Mexico",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("0.5"),
            ),
            TransactionSchema(
                transaction_id="TX_1004",
                transaction_date=datetime(2026, 9, 28, 10, 5),
                product_id=prod_id,
                customer_id=cust_id,
                transaction_type="Purchase",
                amount=Decimal("150.00"),
                currency="USD",
                amount_usd=Decimal("150.00"),
                merchant_name="Unknown Electronics Store",
                merchant_category="Digital Goods",
                transaction_country="Mexico",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("12.5"),
            ),
        ]

        for tx in mock_txs:
            self._transactions[tx.transaction_id] = tx

        # 4. Reclamos activos
        comp_id = "COMP_8812"
        self._complaints[comp_id] = ComplaintSchema(
            complaint_id=comp_id,
            creation_date=datetime(2026, 9, 29, 14, 30),
            customer_id=cust_id,
            case_type="Claim",
            category="Transaction Dispute",
            affected_product_id=prod_id,
            claimed_amount=Decimal("150.00"),
            currency="USD",
            priority="Medium",
            status="In Process",
            sla_breached=False,
        )

    # --- Public Methods ---

    def get_customer_by_document(
        self, document_type: str, document_number: str
    ) -> dict | None:
        """Query in-memory customers dictionary by document type and number."""
        for customer in self._customers.values():
            doc_type_match = (
                str(customer.get("document_type", "")).upper() == document_type.upper()
            )
            doc_num_match = str(customer.get("document_number", "")) == str(
                document_number
            )

            if doc_type_match and doc_num_match:
                return {
                    "customer_id": customer["customer_id"],
                    "first_name": customer.get("first_name", ""),
                    "last_name": customer.get("last_name", ""),
                    "document_type": customer.get("document_type", ""),
                    "document_number": customer.get("document_number", ""),
                }

        return None

    def get_customer(self, customer_id: str) -> Optional[dict]:
        return self._customers.get(customer_id)

    def get_product(self, product_id: str) -> Optional[dict]:
        return self._products.get(product_id)

    def get_transaction(self, transaction_id: str) -> Optional[TransactionSchema]:
        return self._transactions.get(transaction_id)

    def get_customer_transactions(self, customer_id: str) -> list[TransactionSchema]:
        return [
            tx for tx in self._transactions.values() if tx.customer_id == customer_id
        ]

    def get_frontend_transactions(self) -> list[Transaction]:
        """Convert stored transactions into lightweight frontend Transaction objects."""
        frontend_list = []
        for tx in self._transactions.values():
            status = "disputed" if tx.transaction_status == "Reversed" else "posted"
            frontend_list.append(
                Transaction(
                    id=tx.transaction_id,
                    merchant=tx.merchant_name or "Unknown Merchant",
                    amount=float(tx.amount),
                    currency=tx.currency,
                    date=tx.transaction_date.strftime("%b %d, %Y"),
                    status=status,
                )
            )
        return frontend_list

    def update_transaction_status(self, transaction_id: str, new_status: str) -> bool:
        """Update transaction status in mock store."""
        tx = self.get_transaction(transaction_id)
        if tx:
            tx.transaction_status = new_status
            return True
        return False

    def create_complaint(self, complaint: ComplaintSchema) -> ComplaintSchema:
        self._complaints[complaint.complaint_id] = complaint
        return complaint

    def get_complaint(self, complaint_id: str) -> Optional[ComplaintSchema]:
        return self._complaints.get(complaint_id)

    def get_customer_products(self, customer_id: str) -> list[dict]:
        """Retorna todos los productos asociados a un cliente."""
        return [
            prod
            for prod in self._products.values()
            if prod.get("customer_id") == customer_id
        ]

    def get_active_complaints(self, customer_id: str) -> list[ComplaintSchema]:
        """Retorna los reclamos no resueltos de un cliente."""
        return [
            comp
            for comp in self._complaints.values()
            if comp.customer_id == customer_id and comp.status in ["Open", "In Process"]
        ]

    def get_exchange_rate(
        self, source_currency: str, target_currency: str = "USD"
    ) -> float:
        """Obtiene la tasa de cambio simulada."""
        rates = {
            ("COP", "USD"): 0.00025,
            ("MXN", "USD"): 0.058,
            ("ARS", "USD"): 0.0011,
            ("USD", "USD"): 1.0,
        }
        return rates.get((source_currency, target_currency), 1.0)


# Instantiate singleton instance
db = MockDatabase()
