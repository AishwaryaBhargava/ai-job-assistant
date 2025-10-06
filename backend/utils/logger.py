import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Ensure the logs directory exists
LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "ai_job_assistant.log"

# Create a named logger
logger = logging.getLogger("ai_job_assistant")
logger.setLevel(logging.INFO)

# --- Formatter ---
formatter = logging.Formatter(
    "[%(asctime)s] [%(levelname)s] [%(name)s:%(module)s]: %(message)s",
    "%Y-%m-%d %H:%M:%S",
)

# --- File Handler (for daily rotation) ---
file_handler = TimedRotatingFileHandler(
    LOG_FILE,
    when="midnight",       # rotate every midnight
    interval=1,
    backupCount=7,         # keep last 7 days
    encoding="utf-8",
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# --- Attach handlers if not already ---
if not logger.hasHandlers():
    logger.addHandler(file_handler)  # ✅ Only file handler, no console handler

# Critical line: disable propagation so Uvicorn doesn't override it
logger.propagate = False