"""AIService: the only AI entry point application code should depend on.

Selects a primary provider (and an optional fallback) by name and exposes
a single generate() method. Provider failures never propagate as raw
exceptions to API consumers.

Only MockProvider is registered today. Real providers (Gemini, Groq,
OpenAI, Anthropic, Mistral, ...) get added to `_PROVIDERS` below once the
hackathon's actual AI requirement is known — do not add them speculatively.
"""

from app.ai.base import AIProvider
from app.ai.providers.mock import MockProvider
from app.ai.schemas import AIRequest, AIResponse
from app.core.config import Settings, get_settings
from app.core.exceptions import AIProviderError

_PROVIDERS: dict[str, AIProvider] = {
    "mock": MockProvider(),
}


class AIService:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._primary = _PROVIDERS.get(settings.ai_provider, _PROVIDERS["mock"])
        self._fallback = _PROVIDERS.get(settings.ai_fallback_provider or "")

    async def generate(self, request: AIRequest) -> AIResponse:
        try:
            return await self._primary.generate(request)
        except Exception:
            if self._fallback is not None:
                try:
                    return await self._fallback.generate(request)
                except Exception as exc:
                    raise AIProviderError("AI generation failed on primary and fallback providers") from exc
            raise AIProviderError("AI generation failed and no fallback provider is configured") from None
