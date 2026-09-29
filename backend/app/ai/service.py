"""AIService: the only AI entry point application code should depend on.

generate_structured(prompt, response_model):
  primary provider → validate with Pydantic → on invalid output retry once
  (with the validation error fed back) → fallback provider (same) →
  AIProviderError.

A provider exception (network, auth, timeout) skips the retry and goes
straight to the fallback.
"""

import asyncio
import logging
from functools import lru_cache
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.ai.base import AIProvider
from app.ai.providers.gemini import GeminiProvider
from app.ai.providers.groq import GroqProvider
from app.ai.providers.mock import MockProvider
from app.ai.schemas import AIPrompt
from app.core.config import Settings, get_settings
from app.core.exceptions import AIProviderError

logger = logging.getLogger("app.ai")

T = TypeVar("T", bound=BaseModel)

ATTEMPTS_PER_PROVIDER = 2  # first try + one retry on invalid output


def build_provider(name: str, settings: Settings) -> AIProvider | None:
    name = name.strip().lower()
    if name == "gemini":
        if settings.gemini_api_key and settings.gemini_model:
            return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        logger.warning("AI provider 'gemini' needs GEMINI_API_KEY and GEMINI_MODEL; skipping it")
        return None
    if name == "groq":
        if settings.groq_api_key and settings.groq_model:
            return GroqProvider(settings.groq_api_key, settings.groq_model)
        logger.warning("AI provider 'groq' needs GROQ_API_KEY and GROQ_MODEL; skipping it")
        return None
    if name == "mock":
        return MockProvider()
    if name:
        logger.warning("Unknown AI provider %r; skipping it", name)
    return None


class AIService:
    def __init__(self, settings: Settings | None = None) -> None:
        settings = settings or get_settings()
        self._timeout = settings.ai_timeout_seconds
        # an unusable primary falls back to mock so the offline demo always works
        self._primary: AIProvider = build_provider(settings.ai_provider, settings) or MockProvider()
        self._fallback: AIProvider | None = build_provider(settings.ai_fallback_provider, settings)

    @property
    def provider_name(self) -> str:
        return self._primary.name

    async def generate_structured(self, prompt: AIPrompt, response_model: type[T]) -> T:
        providers = [p for p in (self._primary, self._fallback) if p is not None]
        for provider in providers:
            result = await self._try_provider(provider, prompt, response_model)
            if result is not None:
                return result
        raise AIProviderError("The AI service is unavailable right now. Try again or start from a template.")

    async def _try_provider(self, provider: AIProvider, prompt: AIPrompt, response_model: type[T]) -> T | None:
        current = prompt
        for attempt in range(1, ATTEMPTS_PER_PROVIDER + 1):
            try:
                raw = await asyncio.wait_for(provider.generate_json(current, response_model), timeout=self._timeout)
            except Exception as exc:  # provider down / auth / timeout: no point retrying the same one
                logger.warning("AI %s failed on %s: %s", provider.name, prompt.task, type(exc).__name__)
                return None
            try:
                return response_model.model_validate_json(_strip_fences(raw))
            except ValidationError as exc:
                logger.warning(
                    "AI %s returned invalid %s (attempt %d): %d errors",
                    provider.name,
                    response_model.__name__,
                    attempt,
                    exc.error_count(),
                )
                current = _with_feedback(prompt, exc)
        return None


def _strip_fences(raw: str) -> str:
    """Some models wrap JSON in ```json fences even in JSON mode."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


def _with_feedback(prompt: AIPrompt, exc: ValidationError) -> AIPrompt:
    errors = "; ".join(
        f"{'.'.join(str(p) for p in e['loc']) or '<root>'}: {e['msg']}" for e in exc.errors(include_input=False)[:8]
    )
    return prompt.model_copy(
        update={
            "user": f"{prompt.user}\n\nYour previous answer was invalid ({errors}). "
            "Return only JSON that matches the schema exactly."
        }
    )


@lru_cache
def get_ai_service() -> AIService:
    return AIService()
