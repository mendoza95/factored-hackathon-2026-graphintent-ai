import pytest

from app.backend.services.llm_fallback import LLM_client


@pytest.fixture
def llm_client():
    """Fixture providing an instance of LLM_client."""
    return LLM_client()


@pytest.mark.asyncio
async def test_query_llm_fallback_success(llm_client):
    """Verifica que el servicio de Hugging Face responda correctamente."""
    prompt = "Hola, tengo una duda sobre un cobro doble que me hicieron."
    response = await llm_client.query_llm_fallback(prompt)

    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_query_llm_fallback_empty_prompt(llm_client):
    """Verifica el comportamiento con un mensaje básico."""
    response = await llm_client.query_llm_fallback("¿Qué puedes hacer?")
    assert response is not None
    assert isinstance(response, str)
    assert len(response) > 0


@pytest.mark.asyncio
async def test_query_llm_fallback_success2(llm_client):
    prompt = "Hola, tengo una duda sobre un cobro doble que me hicieron."
    response = await llm_client.query_llm_fallback(prompt)

    assert response is not None
    assert len(response) > 0
    # Asegurar que no devolvió el mensaje de fallback por timeout
    assert "experimentando una breve demora" not in response
