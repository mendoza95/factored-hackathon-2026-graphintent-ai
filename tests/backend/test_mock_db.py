import pytest

from decimal import Decimal
from app.backend.db.mock_db import MockDatabase
from app.backend.schemas.dispute import ComplaintSchema


@pytest.fixture(scope="module")
def db():
    # Loaded only ONCE for all tests in this file
    return MockDatabase()


def test_mock_db_initialization(db):
    """Verify database initializes and populates records."""

    # Check fallback customer or loaded customer exists
    assert db.get_customer("CUST_12345") is not None or len(db._customers) > 0


def test_mock_db_transaction_query(db):
    """Verify transaction querying returns correct model structure."""
    # Fetch any transaction ID present in database
    all_tx_ids = list(db._transactions.keys())
    assert len(all_tx_ids) > 0

    tx = db.get_transaction(all_tx_ids[0])
    assert tx is not None
    assert tx.transaction_id == all_tx_ids[0]


def test_mock_db_complaint_creation(db):
    """Verify saving new complaints works correctly."""
    new_complaint = ComplaintSchema(
        complaint_id="COMP_TEST_001",
        creation_date="2026-09-26T10:00:00",
        customer_id="CUST_12345",
        claimed_amount=Decimal("150.00"),
        currency="USD",
        status="Open",
    )

    saved = db.create_complaint(new_complaint)
    assert saved.complaint_id == "COMP_TEST_001"
    assert db.get_complaint("COMP_TEST_001") is not None
