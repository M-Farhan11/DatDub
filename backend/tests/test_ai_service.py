import pytest

from app.ai.schemas import AIRequest, AIResponse
from app.ai.service import AIService
from app.core.config import Settings
from app.core.exceptions import AIProviderError


@pytest.mark.asyncio
async def test_mock_provider_returns_valid_response():
    service = AIService(settings=Settings(ai_provider="mock"))
    response = await service.generate(AIRequest(input="hello"))

    assert isinstance(response, AIResponse)
    assert response.success is True
    assert response.provider == "mock"
    assert "hello" in response.output


@pytest.mark.asyncio
async def test_unknown_provider_falls_back_to_mock():
    # No provider named "does-not-exist" is registered, so AIService falls
    # back to mock rather than the app.
    service = AIService(settings=Settings(ai_provider="does-not-exist"))
    response = await service.generate(AIRequest(input="hi"))

    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_primary_failure_falls_back_to_secondary():
    class FailingProvider:
        name = "failing"

        async def generate(self, request: AIRequest) -> AIResponse:
            raise RuntimeError("simulated provider outage")

    service = AIService(settings=Settings(ai_provider="mock", ai_fallback_provider="mock"))
    service._primary = FailingProvider()  # simulate a broken primary
    response = await service.generate(AIRequest(input="hi"))

    assert response.provider == "mock"


@pytest.mark.asyncio
async def test_failure_without_fallback_raises_controlled_error():
    class FailingProvider:
        name = "failing"

        async def generate(self, request: AIRequest) -> AIResponse:
            raise RuntimeError("simulated provider outage")

    service = AIService(settings=Settings(ai_provider="mock"))
    service._primary = FailingProvider()
    service._fallback = None

    with pytest.raises(AIProviderError):
        await service.generate(AIRequest(input="hi"))
