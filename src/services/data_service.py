import json
import os
import logging
from typing import Dict

from models.bot_models import BotConfig, UserInfo
from utils.logger import get_named_logger

logger = get_named_logger()


class Storage:
    def __init__(self, path: str):
        self.path = path

    def load(self) -> Dict:
        """Загружает данные из JSON-файла"""
        if not os.path.exists(self.path):
            logger.warning(f"Файл {self.path} не найден. Используется конфигурация по умолчанию.")
            return {
                "config": BotConfig().to_dict(),
                "user_data": {}
            }

        try:
            with open(self.path, 'r') as f:
                data = json.load(f)

            config = BotConfig.from_dict(data.get("config", {}))
            user_data_raw = data.get("user_data", {})
            user_data = {
                int(uid): UserInfo.from_dict(info)
                for uid, info in user_data_raw.items()
            }

            return {
                "config": config,
                "user_data": user_data
            }

        except Exception as e:
            logger.error(f"Ошибка при загрузке данных: {e}")
            return {
                "config": BotConfig(),
                "user_data": {}
            }

    def save(self, config: BotConfig, user_data: Dict[int, UserInfo]) -> None:
        """Сохраняет данные в JSON-файл"""
        try:
            serializable_data = {
                "config": config.to_dict(),
                "user_data": {
                    str(uid): user.to_dict()
                    for uid, user in user_data.items()
                }
            }

            with open(self.path, 'w') as f:
                json.dump(serializable_data, f, indent=4)  # type: ignore[arg-type]

            logger.info("Данные успешно сохранены")

        except Exception as e:
            logger.error(f"Ошибка при сохранении данных: {e}")
