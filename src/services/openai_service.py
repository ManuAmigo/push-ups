import logging
from openai import OpenAI
from typing import Optional
from utils.logger import get_named_logger

logger = get_named_logger()


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key
        if not api_key:
            raise ValueError("OpenAI API ключ не задан.")

        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI API клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI API: {e}")
            raise

    def generate_comment(self, user_prompt: str, system_prompt: Optional[str] = None, fallback: bool = True) -> str:
        """
        Генерация короткого комментария или анализа на основе промпта пользователя.

        :param user_prompt: текст от пользователя
        :param system_prompt: настройка роли (по умолчанию: строгий тренер)
        :param fallback: возвращать ли заглушку в случае ошибки
        :return: строка с ответом
        """
        system_prompt = system_prompt or (
            "Ты строгий и немногословный тренер. Говори лаконично и мотивирующе."
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Ошибка генерации с OpenAI: {e}")
            if fallback:
                return "Сила в постоянстве."
            raise
