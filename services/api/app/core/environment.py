"""Load only server configuration; paths may be overridden by the local launcher."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[4]


def load_environment():
    # Existing process settings win; root credentials fill empty API placeholders.
    load_dotenv(Path(os.getenv("APP_ROOT_ENV_FILE", ROOT / ".env")))
    load_dotenv(Path(os.getenv("APP_API_ENV_FILE", ROOT / "services/api/.env")))
    load_dotenv(Path(os.getenv("APP_GEMINI_ENV_FILE", ROOT / "services/api/.env.gemini.local")))
    if not os.getenv("SUPABASE_SERVICE_ROLE_KEY") and os.getenv("SUPABASE_SERVICE_KEY"):
        os.environ["SUPABASE_SERVICE_ROLE_KEY"] = os.environ["SUPABASE_SERVICE_KEY"]
