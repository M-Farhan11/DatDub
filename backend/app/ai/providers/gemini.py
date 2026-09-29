"""Gemini provider (google-genai) with native structured output."""

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.ai.schemas import AIPrompt


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def generate_json(self, prompt: AIPrompt, response_model: type[BaseModel]) -> str:
        response = await self._client.aio.models.generate_content(
            model=self._model,
            contents=prompt.user,
            config=types.GenerateContentConfig(
                system_instruction=prompt.system,
                response_mime_type="application/json",
                response_json_schema=response_model.model_json_schema(),
                temperature=0.2,
            ),
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response")
        return response.text
