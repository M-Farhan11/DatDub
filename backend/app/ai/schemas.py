"""Generic AI request/response models.

Intentionally minimal and domain-agnostic. These exist to prove the
provider abstraction works, not to model any specific product's AI
workflow. Expect these to be replaced once the hackathon product is known.
"""

from typing import Any

from pydantic import BaseModel


class AIRequest(BaseModel):
    input: str
    metadata: dict[str, Any] | None = None


class AIResponse(BaseModel):
    output: str
    provider: str
    success: bool
