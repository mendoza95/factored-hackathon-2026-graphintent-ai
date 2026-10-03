import os

from huggingface_hub import AsyncInferenceClient

HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = "meta-llama/Llama-3.2-3B-Instruct"


class LLM_client:
    def __init__(self):
        self.client = AsyncInferenceClient(api_key=HF_TOKEN) if HF_TOKEN else None

    async def query_llm_fallback(self, user_message: str, language: str = "es") -> str:
        """
        Generate a conversational fallback response
        when ML intent confidence is low.
        """
        if not self.client:
            return (
                "No se pudo conectar al servicio LLM. Por favor, especifica si "
                "deseas iniciar un reclamo o consultar tu saldo."
            )

        system_prompt = (
            "Eres un asistente virtual bancario servicial y profesional. "
            "El usuario ha enviado una solicitud que no pudimos clasificar"
            " automáticamente. "
            "Responde de forma concisa y amable en español, ayudándole "
            "a aclarar si desea "
            "disputar una transacción o consultar información de su cuenta."
        )

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            response = await self.client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=200,
                temperature=0.3,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Hugging Face API Error: {e}")
            return (
                "Lo siento, tuve un problema procesando tu consulta. "
                "¿Deseas iniciar la disputa de una transacción?"
            )
