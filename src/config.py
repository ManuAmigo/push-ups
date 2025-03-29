import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATA_PATH: str = "data.json"
    DEFAULT_REMINDER_TIME: str = "22:00"
    DEFAULT_INACTIVITY_DAYS: int = 4
    DEFAULT_WARNING_DAYS: int = 2
    CHALLENGE_START = "2025-03-15"
    CHALLENGE_END = "2025-06-13"


settings = Settings()
