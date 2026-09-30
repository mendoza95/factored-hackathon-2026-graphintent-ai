from enum import Enum

from pydantic import BaseModel, Field


class DocumentTypeEnum(str, Enum):
    CC = "CC"  # Cédula de Ciudadanía
    CE = "CE"  # Cédula de Extranjería
    PASSPORT = "PASSPORT"
    NIT = "NIT"


class LoginRequest(BaseModel):
    document_type: DocumentTypeEnum = Field(
        ..., description="Type of identification document"
    )
    document_number: str = Field(
        ...,
        json_schema_extra={"example": "1098765432"},
        description="Identification document number",
    )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
