import json
import os
from typing import Dict

from models.bot_models import BotConfig, UserInfo
from utils.logger import get_named_logger
from config import settings

logger = get_named_logger()


class Storage:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> Dict:
        """Загружает данные из JSON-файла"""
        if not os.path.exists(self.path):
            logger.warning(f"Файл {self.path} не найден. Используется конфигурация по умолчанию.")
            return {
                "config": self.default_config(),
                "user_data": {}
            }

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            config = BotConfig.model_validate(data.get("config", {}))

            user_data_raw = data.get("user_data", {})
            user_data = {
                int(uid): UserInfo.model_validate(info)
                for uid, info in user_data_raw.items()
            }

            return {
                "config": config,
                "user_data": user_data
            }

        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            return {
                "config": self.default_config(),
                "user_data": {}
            }

    def save(self, config: BotConfig, user_data: Dict[int, UserInfo]) -> None:
        """Сохраняет данные в JSON-файл"""
        try:
            serializable_data = {
                "config": config.model_dump(mode="json"),
                "user_data": {
                    str(uid): user.model_dump(mode="json")
                    for uid, user in user_data.items()
                }
            }

            with open(self.path, 'w', encoding='utf-8') as f:
                json.dump(serializable_data, f, indent=4) # qo

            logger.info("Данные успешно сохранены")

        except Exception as e:
            logger.error(f"Ошибка при сохранении данных: {e}")

    @staticmethod
    def default_config() -> BotConfig:
        return settings.to_bot_config()  # ✅ Используем единый источник правды
