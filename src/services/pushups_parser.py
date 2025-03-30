import re
from typing import Tuple, Optional

from services.openai_service import OpenAIClient
from models.bot_models import CommentContext
from utils.logger import get_named_logger

logger = get_named_logger()


class PushupsParser:
    def __init__(self, openai_client: Optional[OpenAIClient] = None):
        self.openai_client = openai_client
        self.api_calls_cache = {}

    def extract_pushups_count(self, text: str) -> Tuple[int, bool]:
        """
        Извлекает количество отжиманий из текста сообщения.

        Возвращает кортеж:
        - количество отжиманий
        - флаг, является ли число итогом за весь день
        """
        text_lower = text.lower()

        if text in self.api_calls_cache:
            return self.api_calls_cache[text]

        is_daily_total = bool(re.search(r'за день|за сегодня|всего|сегодня', text_lower))

        # Простые и очевидные форматы
        simple_match = re.search(r'=(\d+)', text)
        if simple_match:
            result = int(simple_match.group(1))
            self.api_calls_cache[text] = (result, is_daily_total)
            return result, is_daily_total

        # Использование OpenAI для сложных случаев
        if self.openai_client:
            try:
                prompt = f"Извлеки количество отжиманий из текста: '{text}'. Отвечай только числом. Если не уверен — 0."
                result_text = self.openai_client.generate_comment(
                    user_prompt=prompt,
                    context=CommentContext.REPORT,
                    fallback=False
                )

                match = re.search(r'\d+', result_text)
                if match:
                    result = int(match.group())
                    self.api_calls_cache[text] = (result, is_daily_total)
                    return result, is_daily_total
            except Exception as e:
                logger.error(f"Ошибка извлечения данных с OpenAI: {e}")

        # Резервный метод
        result = self.fallback_extract_pushups_count(text_lower)
        self.api_calls_cache[text] = (result, is_daily_total)
        return result, is_daily_total

    @staticmethod
    def fallback_extract_pushups_count(text: str) -> int:
        """Резервный метод, если OpenAI недоступен."""
        keywords = ["отжим", "отжал", "сделал", "подход", "выполнил", "осилил", "пуш", "push"]
        if not any(keyword in text for keyword in keywords) and "+" not in text:
            return 0

        # Формат X+Y+Z
        numbers = re.findall(r'\d+', text)
        if '+' in text and numbers:
            return sum(int(num) for num in numbers)

        # Формат с запятыми
        if ',' in text and numbers:
            return sum(int(num) for num in numbers)

        # Одно число с ключевым словом
        if numbers:
            return int(numbers[0])

        return 0
