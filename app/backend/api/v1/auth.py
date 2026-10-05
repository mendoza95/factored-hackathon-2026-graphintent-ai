from fastapi import APIRouter, Depends, HTTPException, status

from app.backend.core.security import create_access_token
from app.backend.db.base import BaseDatabase
from app.backend.db.deps import get_db
from app.backend.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(credentials: LoginRequest, db: BaseDatabase = Depends(get_db)):

    print(credentials.document_type.value)
    print(credentials.document_number)
    # Query DuckDB to retrieve customer_id matching document_type and document_number
    customer = db.get_customer_by_document(
        credentials.document_type.value, credentials.document_number
    )
    print(customer)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid document type or document number",
        )

    # Encode internal customer_id into JWT token payload
    access_token = create_access_token(
        data={
            "sub": customer["customer_id"],
            "document_type": credentials.document_type.value,
        }
    )
    return TokenResponse(access_token=access_token)


@router.get("/token")
def get_test_token():
    # Creates a valid token using your actual secret key and encoding rules
    token = create_access_token(data={"sub": "CUST_12345"})
    return {"access_token": token}
