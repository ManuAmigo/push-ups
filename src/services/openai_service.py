from typing import Optional
from openai import OpenAI

from models.bot_models import CommentContext
from utils.logger import get_named_logger

logger = get_named_logger()


class OpenAIClient:
    def __init__(self, api_key: Optional[str] = None):
        if not api_key:
            raise ValueError("OpenAI API ключ не задан.")

        try:
            self.client = OpenAI(api_key=api_key)
            logger.info("OpenAI API клиент успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации OpenAI API: {e}")
            raise

    def generate_comment(
        self,
        user_prompt: str,
        context: CommentContext = CommentContext.REPORT,
        fallback: bool = True,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Генерация короткого комментария или анализа на основе промпта пользователя.

        :param user_prompt: текст от пользователя
        :param context: контекст генерации (персональный, групповой, отчётный)
        :param fallback: возвращать ли заглушку в случае ошибки
        :param system_prompt: override — если указан, будет использоваться вместо шаблона по context
        :return: строка с ответом
        """

        system_prompt = system_prompt or self._get_system_prompt(context)

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

    @staticmethod
    def _get_system_prompt(context: CommentContext) -> str:
        """
        Возвращает системный prompt в зависимости от типа контекста.
        """
        match context:
            case CommentContext.REPORT:
                return "Ты строгий и немногословный тренер. Говори лаконично и мотивирующе."
            case CommentContext.DAILY_STATS:
                return "Ты старший тренер. Подводишь итоги дня: строго, с уважением и юмором."
            case CommentContext.PERSONAL:
                return "Ты опытный наставник. Мотивируешь человека продолжать путь. Будь философски краток."
        return "Ты строгий тренер."
