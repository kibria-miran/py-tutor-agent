import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
MODEL_ID = os.getenv("MODEL_ID", "")
API_BASE = os.getenv("API_BASE", "https://integrate.api.nvidia.com/v1")
MAX_STEPS = int(os.getenv("MAX_STEPS", "6"))
RUN_TIMEOUT = int(os.getenv("RUN_TIMEOUT", "10"))
API_TIMEOUT = int(os.getenv("API_TIMEOUT", "60"))
SANDBOX_DIR = Path(os.getenv("SANDBOX_DIR", BASE_DIR / "sandbox"))
PASS_RATIO = float(os.getenv("PASS_RATIO", "0.6"))
WEB_SEARCH_ENABLED = os.getenv("WEB_SEARCH_ENABLED", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
HISTORY_MESSAGES = int(os.getenv("HISTORY_MESSAGES", "10"))
PROGRESS_PATH = Path(os.getenv("PROGRESS_PATH", BASE_DIR / "progress.json"))
LOG_PATH = Path(os.getenv("LOG_PATH", BASE_DIR / "logs" / "tutor.log"))
