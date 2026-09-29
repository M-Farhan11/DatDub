"""AI provider interface.

Any provider (mock or real) implements this Protocol. Application code
depends on `AIService`, never on a provider or its SDK.

A provider returns the raw JSON text of its answer. `AIService` owns
parsing, Pydantic validation, retry and fallback.
"""

from typing import Protocol

from pydantic import BaseModel

from app.ai.schemas import AIPrompt


class AIProvider(Protocol):
    name: str

    async def generate_json(self, prompt: AIPrompt, response_model: type[BaseModel]) -> str: ...
