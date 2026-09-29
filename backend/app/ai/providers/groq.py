"""Groq provider over plain httpx (OpenAI-compatible chat completions).

Uses JSON mode (`json_object`), which every Groq chat model supports, and
puts the JSON schema in the system prompt. AIService validates the result.
"""

import json

import httpx
from pydantic import BaseModel

from app.ai.schemas import AIPrompt

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def generate_json(self, prompt: AIPrompt, response_model: type[BaseModel]) -> str:
        schema = json.dumps(response_model.model_json_schema(), separators=(",", ":"))
        system = f"{prompt.system}\n\nRespond with a single JSON object that matches this JSON schema:\n{schema}"
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt.user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(GROQ_URL, json=payload, headers={"Authorization": f"Bearer {self._api_key}"})
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
