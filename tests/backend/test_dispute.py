import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_transactions_unauthorized(client: AsyncClient):
    """Verify requesting transactions without a token returns 401."""
    response = await client.get("/api/v1/transactions")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_transactions_success(client: AsyncClient, auth_headers):
    """Verify fetching posted transactions with valid auth headers."""
    response = await client.get("/api/v1/transactions", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "id" in data[0]
    assert "merchant" in data[0]


@pytest.mark.asyncio
async def test_submit_dispute_success(client: AsyncClient, auth_headers):
    """Verify submitting a dispute with valid auth headers."""
    payload = {
        "transaction_id": "TX_1001",
        "reason": "Cargo no reconocido",
        "details": "No reconozco este consumo en Uber.",
    }
    response = await client.post("/api/v1/disputes", json=payload, headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["transaction_id"] == "TX_1001"
    assert data["status"] == "under_review"
    assert data["reference_id"].startswith("DISP-")


@pytest.mark.asyncio
async def test_submit_dispute_not_found(client: AsyncClient, auth_headers):
    """Verify handling when attempting to dispute a non-existent transaction."""
    payload = {
        "transaction_id": "TX_INVALID_999",
        "reason": "Test dispute",
    }
    response = await client.post("/api/v1/disputes", json=payload, headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Transaction not found"
