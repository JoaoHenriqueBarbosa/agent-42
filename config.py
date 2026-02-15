"""Configuração via variáveis de ambiente."""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

PROVIDERS = {
    "anthropic": {
        "api_key": os.environ["ANTHROPIC_API_KEY"],
        "base_url": os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/"),
        "model": os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
    },
    "zai": {
        "api_key": os.environ["ZAI_API_KEY"],
        "base_url": os.environ.get("ZAI_BASE_URL", "https://api.z.ai/api/coding/paas/v4"),
        "model": os.environ.get("ZAI_MODEL", "GLM-4.5-air"),
    },
    "openai": {
        "api_key": os.environ["OPENAI_API_KEY"],
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
    },
}
