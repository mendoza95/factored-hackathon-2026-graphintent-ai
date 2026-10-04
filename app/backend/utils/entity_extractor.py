import re
from typing import Any, Dict


def extract_entities_regex(text: str) -> Dict[str, Any]:
    """
    Extrae el monto reclamado y la moneda usando expresiones regulares.
    Soporta formatos como: "$150", "150$", "150 USD", "2500.50 dólares", "1000.00"
    """
    if not text:
        return {"claimed_amount": None, "currency": None}

    # Busca patrones numéricos en el texto
    amount_match = re.search(r"\b\d+(?:[\.,]\d{1,2})?\b", text)
    extracted_amount = None

    if amount_match:
        try:
            extracted_amount = float(amount_match.group(0).replace(",", "."))
        except ValueError:
            extracted_amount = None

    # Detectar moneda por palabras clave o símbolos
    text_lower = text.lower()
    currency = None

    if (
        "usd" in text_lower
        or "$" in text
        or "dólar" in text_lower
        or "dolar" in text_lower
    ):
        currency = "USD"
    elif "cop" in text_lower or "pesos" in text_lower or "peso" in text_lower:
        currency = "COP"
    elif "mxn" in text_lower:
        currency = "MXN"

    return {"claimed_amount": extracted_amount, "currency": currency}
