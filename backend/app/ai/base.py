"""AI provider interface.

Any provider (mock or real) implements this Protocol. Application code
depends on this interface, never on a specific provider SDK.
"""

from typing import Protocol

from app.ai.schemas import AIRequest, AIResponse


class AIProvider(Protocol):
    name: str

    async def generate(self, request: AIRequest) -> AIResponse: ...
