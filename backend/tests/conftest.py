"""Unit tests never call a real AI provider, whatever backend/.env says.

Env vars override .env in pydantic-settings. tests/test_ai_live.py builds its
own settings with the real keys, so it is unaffected.
"""

import os

os.environ["AI_PROVIDER"] = "mock"
os.environ["AI_FALLBACK_PROVIDER"] = ""
