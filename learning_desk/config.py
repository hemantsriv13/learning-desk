"""Settings read from environment variables (optionally from a local .env file).

Nothing here is secret except the API key, and the key is never stored by this app:
the provider SDK reads ANTHROPIC_API_KEY from the environment itself.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_DIR = Path(__file__).resolve().parent.parent

# Values already set in the real environment win over .env.
load_dotenv(PROJECT_DIR / ".env", override=False)

DEFAULT_DB_PATH = PROJECT_DIR / "data" / "learning_desk.db"

# Default model; change it with LEARNING_DESK_MODEL without editing code.
DEFAULT_MODEL = "claude-opus-5-5"
DEFAULT_EFFORT = "medium"
DEFAULT_MAX_TOKENS = 8000
DEFAULT_TIMEOUT_SECONDS = 180


def db_path() -> Path:
    return Path(os.environ.get("LEARNING_DESK_DB", DEFAULT_DB_PATH))


def model() -> str:
    return os.environ.get("LEARNING_DESK_MODEL", "").strip() or DEFAULT_MODEL


def effort() -> str:
    """Anthropic's effort setting: low, medium, high, xhigh or max. Empty means 'do not send'."""
    return os.environ.get("LEARNING_DESK_EFFORT", DEFAULT_EFFORT).strip()


def max_tokens() -> int:
    return int(os.environ.get("LEARNING_DESK_MAX_TOKENS", DEFAULT_MAX_TOKENS))


def timeout_seconds() -> float:
    return float(os.environ.get("LEARNING_DESK_TIMEOUT", DEFAULT_TIMEOUT_SECONDS))


def api_key_present() -> bool:
    """Only reports whether a key exists. Never returns or logs the key."""
    return bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
