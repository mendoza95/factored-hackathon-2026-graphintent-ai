# app/backend/db/mock_db.py
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

from app.backend.db.base import BaseDatabase
from app.backend.schemas.dispute import (
    ComplaintSchema,
    Transaction,
    TransactionSchema,
)


class MockDatabase(BaseDatabase):
    """In-memory database loader that populates from local sample CSVs or seed data."""

    def __init__(self, data_dir: str = "data/sample"):
        self.data_dir = Path(data_dir).parent.parent.resolve() / "app" / data_dir
        self._customers: dict[str, dict] = {}
        self._products: dict[str, dict] = {}
        self._transactions: dict[str, TransactionSchema] = {}
        self._complaints: dict[str, ComplaintSchema] = {}

        # Seed standard fallback mock data
        self._seed_fallback_data()

    def _seed_fallback_data(self):
        """Seed default mock records if CSVs are missing or for fallback tests."""
        cust_id = "CUST_12345"
        cust_id_2 = "CUST_67890"

        # 1. Datos de clientes
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

        self._customers[cust_id_2] = {
            "customer_id": cust_id_2,
            "first_name": "Ana",
            "last_name": "Gomez",
            "document_type": "CE",
            "document_number": "987654321",
            "country": "Colombia",
            "detected_accent": "colombian",
            "segment": "Standard",
            "customer_status": "Active",
        }

        # 2. Productos financieros del cliente
        prod_id = "PROD_CARD_01"
        prod_savings_id = "PROD_SAV_02"
        prod_loan_id = "PROD_LOAN_03"
        prod_card_2 = "PROD_CARD_02"

        self._products[prod_id] = {
            "product_id": prod_id,
            "customer_id": cust_id,
            "product_type": "Credit Card",
            "currency": "MXN",
            "current_balance": Decimal("45000.00"),
            "credit_limit": Decimal("100000.00"),
            "product_status": "Active",
        }

        self._products[prod_savings_id] = {
            "product_id": prod_savings_id,
            "customer_id": cust_id,
            "product_type": "Savings Account",
            "currency": "MXN",
            "current_balance": Decimal("125000.50"),
            "product_status": "Active",
        }

        self._products[prod_loan_id] = {
            "product_id": prod_loan_id,
            "customer_id": cust_id,
            "product_type": "Personal Loan",
            "currency": "USD",
            "current_balance": Decimal("15000.00"),
            "product_status": "Active",
        }

        self._products[prod_card_2] = {
            "product_id": prod_card_2,
            "customer_id": cust_id_2,
            "product_type": "Credit Card",
            "currency": "COP",
            "current_balance": Decimal("1200000.00"),
            "credit_limit": Decimal("5000000.00"),
            "product_status": "Active",
        }

        # 3. Transacciones de prueba
        mock_txs = [
            TransactionSchema(
                transaction_id="TX_1001",
                transaction_date=datetime(2026, 10, 1, 12, 0, 0),
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
                transaction_date=datetime(2026, 9, 28, 15, 30, 0),
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
                transaction_date=datetime(2026, 9, 25, 9, 15, 0),
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
                transaction_date=datetime(2026, 9, 28, 10, 5, 0),
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
                transaction_id="TX_1005",
                transaction_date=datetime(2026, 9, 20, 18, 45, 0),
                product_id=prod_savings_id,
                customer_id=cust_id,
                transaction_type="Transfer",
                amount=Decimal("500.00"),
                currency="MXN",
                amount_usd=Decimal("29.00"),
                merchant_name="ATM Withdrawal",
                merchant_category="Banking",
                transaction_country="Mexico",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("1.0"),
            ),
            TransactionSchema(
                transaction_id="TX_1006",
                transaction_date=datetime(2026, 9, 15, 11, 20, 0),
                product_id=prod_id,
                customer_id=cust_id,
                transaction_type="Purchase",
                amount=Decimal("1200.00"),
                currency="MXN",
                amount_usd=Decimal("69.60"),
                merchant_name="Supermarket Central",
                merchant_category="Groceries",
                transaction_country="Mexico",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("3.2"),
            ),
            TransactionSchema(
                transaction_id="TX_2001",
                transaction_date=datetime(2026, 9, 30, 8, 10, 0),
                product_id=prod_card_2,
                customer_id=cust_id_2,
                transaction_type="Purchase",
                amount=Decimal("250000.00"),
                currency="COP",
                amount_usd=Decimal("62.50"),
                merchant_name="Exito Superstore",
                merchant_category="Retail",
                transaction_country="Colombia",
                transaction_status="Approved",
                is_fraud=False,
                fraud_score=Decimal("1.5"),
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

    # --- Public Methods (Firmas alineadas con duckdb_client) ---

    def get_customer(self, customer_id: str) -> Optional[dict]:
        return self._customers.get(customer_id)

    def get_customer_by_document(
        self, document_type: str, document_number: str
    ) -> Optional[dict]:
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

    def get_product(self, product_id: str) -> Optional[dict]:
        return self._products.get(product_id)

    def get_transaction(
        self,
        transaction_id: str,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> Optional[TransactionSchema]:
        return self._transactions.get(transaction_id)

    def get_customer_transactions(
        self,
        customer_id: str,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[TransactionSchema]:
        return [
            tx for tx in self._transactions.values() if tx.customer_id == customer_id
        ]

    def get_frontend_transactions(
        self,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[Transaction]:
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
        tx = self.get_transaction(transaction_id)
        if tx:
            tx.transaction_status = new_status
            return True
        return False

    def create_complaint(self, complaint: ComplaintSchema) -> ComplaintSchema:
        self._complaints[complaint.complaint_id] = complaint
        return complaint

    def get_complaint(
        self,
        complaint_id: str,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> Optional[ComplaintSchema]:
        return self._complaints.get(complaint_id)

    def get_customer_products(self, customer_id: str) -> list[dict]:
        return [
            prod
            for prod in self._products.values()
            if prod.get("customer_id") == customer_id
        ]

    def get_active_complaints(
        self,
        customer_id: str,
        days_back: Optional[int] = 7,
        year: Optional[str] = None,
        month: Optional[str] = None,
        day: Optional[str] = None,
    ) -> list[ComplaintSchema]:
        return [
            comp
            for comp in self._complaints.values()
            if comp.customer_id == customer_id and comp.status in ["Open", "In Process"]
        ]

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


# Instantiate singleton instance
db = MockDatabase()
