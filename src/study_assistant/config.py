from pathlib import Path
import os
from dotenv import load_dotenv

# Load .env file if it exists (dev convenience)
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

def get_required_env(key: str) -> str:
    """Retrieve env var or raise clear error."""
    value = os.getenv(key)
    if not value:
        raise ValueError(
            f"Missing required environment variable: {key}\n"
            f"Set it in .env file or system environment variables."
        )
    return value

# Public accessors (use these everywhere instead of os.getenv directly)
XAI_API_KEY = get_required_env("XAI_API_KEY")
XAI_API_MODEL = get_required_env("XAI_API_MODEL")
XAI_TIMEOUT = get_required_env("XAI_TIMEOUT")
ZOTERO_LIBRARY_ID = get_required_env("ZOTERO_LIBRARY_ID")
ZOTERO_API_KEY = get_required_env("ZOTERO_API_KEY")
DB_PATH = get_required_env("DB_PATH")

# Non-secret config (can stay here or move to separate constants)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
RESEARCH_LIBRARY = DATA_DIR / "research_library"
INCOMING_FOLDER = DATA_DIR / "incoming"
MAX_SECTION_TOKENS = 950