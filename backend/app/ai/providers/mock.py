"""Mock AI provider.

Makes no external calls and consumes no API credits. Returns deterministic,
schema-valid output so the provider abstraction can be developed and tested
without any real AI credentials. This is the default provider
(AI_PROVIDER=mock) for local development.
"""

from app.ai.schemas import AIRequest, AIResponse


class MockProvider:
    name = "mock"

    async def generate(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            output=f"[mock response to]: {request.input}",
            provider=self.name,
            success=True,
        )
