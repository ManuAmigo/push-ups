# config/settings.py
from datetime import date
from pathlib import Path
from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings
from models.bot_models import BotConfig


class Settings(BaseSettings):
    TELEGRAM_TOKEN: str = Field(..., alias="TELEGRAM_BOT_TOKEN")
    OPENAI_API_KEY: str = Field(default="", alias="OPENAI_API_KEY")

    DATA_PATH: str = "data.json"

    DEFAULT_REMINDER_TIME: str = Field(default="22:00", alias="DEFAULT_REMINDER_TIME")
    DEFAULT_INACTIVITY_DAYS: int = Field(default=4, alias="DEFAULT_INACTIVITY_DAYS")
    DEFAULT_WARNING_DAYS: int = Field(default=2, alias="DEFAULT_WARNING_DAYS")

    CHALLENGE_START: date = Field(default_factory=lambda: date(2025, 3, 15), alias="CHALLENGE_START")
    CHALLENGE_END: date = Field(default_factory=lambda: date(2025, 2, 13), alias="CHALLENGE_END")

    def to_bot_config(self) -> BotConfig:
        """
        Преобразует Settings → BotConfig, с валидацией логики.
        Выбрасывает RuntimeError, если значения из .env противоречивы.
        """
        try:
            return BotConfig(
                reminder_time=self.DEFAULT_REMINDER_TIME,
                inactivity_days=self.DEFAULT_INACTIVITY_DAYS,
                warning_days=self.DEFAULT_WARNING_DAYS,
                challenge_start_date=self.CHALLENGE_START,
                challenge_end_date=self.CHALLENGE_END,
            )
        except ValidationError as e:
            raise RuntimeError(
                f"\n❌ Некорректная конфигурация в .env:\n{e}"
            )

    model_config = {

        "env_file": str(Path(__file__).resolve().parents[0] / ".env"),

        "env_file_encoding": "utf-8",
        "populate_by_name": True,
    }


# Сразу валидируем настройки
try:
    settings = Settings()
except ValidationError as e:
    raise RuntimeError(f"\n❌ Ошибка в .env или переменных окружения:\n{e}")
