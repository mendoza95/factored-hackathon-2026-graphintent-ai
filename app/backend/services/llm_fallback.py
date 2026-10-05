import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import AsyncInferenceClient

# Obtiene la ruta raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

HF_TOKEN = os.getenv("HF_TOKEN")
# Modelo de chat compatible con Serverless Router
MODEL_NAME = "Qwen/Qwen2.5-72B-Instruct"


class LLM_client:
    def __init__(self, timeout_seconds: float = 12.0):  # Aumentado de 5 a 12 segundos
        self.timeout_seconds = timeout_seconds
        self.client = (
            AsyncInferenceClient(model=MODEL_NAME, token=HF_TOKEN) if HF_TOKEN else None
        )

    async def query_llm_fallback(self, user_message: str) -> str:
        if not self.client:
            return (
                "Entiendo tu consulta. Para darte un mejor soporte, "
                "¿podrías darme más detalles o el monto de la transacción?"
            )

        try:
            # Envolvemos la llamada en asyncio.wait_for para forzar el timeout
            response = await asyncio.wait_for(
                self.client.chat_completion(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Eres un asistente conversacional de soporte bancario. "
                                "Responde brevemente y orienta al usuario sin "
                                "prometer reembolsos."
                            ),
                        },
                        {"role": "user", "content": user_message},
                    ],
                    max_tokens=150,
                ),
                timeout=self.timeout_seconds,
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            # Fallback amigable ante latencia alta del proveedor
            return (
                "En este momento estoy experimentando una breve demora. "
                "¿Podrías decirme el monto o concepto del movimiento "
                "que deseas consultar?"
            )
        except Exception:
            # Fallback seguro ante cualquier otro error de red/API
            return (
                "Para ayudarte con tu solicitud, "
                "¿podrías indicarme más detalles sobre el cargo o "
                "la consulta que deseas realizar?"
            )
