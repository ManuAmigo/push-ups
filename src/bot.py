import datetime
from typing import Optional

from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import Message

from models.bot_models import BotConfig, UserInfo, ChallengePeriod, CommentContext
from services.data_service import Storage
from services.openai_service import OpenAIClient
from services.user_repository import UserRepository
from services.pushups_parser import PushupsParser
from utils.logger import get_named_logger

logger = get_named_logger()


class BotService:
    def __init__(
        self,
        config: BotConfig,
        users: UserRepository,
        storage: Storage,
        openai_client: Optional[OpenAIClient] = None,
    ):
        self.config = config
        self.users = users
        self.storage = storage
        self.openai = openai_client
        self.parser = PushupsParser(openai_client)
        self.period = ChallengePeriod(
            start_date=config.challenge_start_date,
            end_date=config.challenge_end_date
        )

    async def handle_message(self, message: Message) -> None:
        if not message.text:
            logger.debug("Получено пустое сообщение — игнорируем.")
            return

        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name
        text = message.text.strip()
        now = datetime.datetime.now()
        today = now.date()

        logger.debug(f"Сообщение от @{username} ({user_id}): '{text}'")

        user = self.users.get(user_id) or UserInfo(username=username, last_activity=now)
        if user.last_activity:
            logger.debug(f"Пользователь найден: @{username} | Последняя активность: {user.last_activity}")
        else:
            logger.debug(f"Новый пользователь: @{username}")

        user.username = username
        user.last_activity = now

        pushups, is_total = self.parser.extract_pushups_count(text)
        logger.debug(f"Распознано: {pushups} отжиманий | {'итог за день' if is_total else 'добавление'}")

        if pushups <= 0:
            logger.debug("Отжиманий не найдено — сообщение проигнорировано.")
            return

        if user.last_report_date != today:
            logger.debug("Первый отчёт за сегодня — сохраняем как новый.")
            user.pushups_today = pushups
            user.total_pushups += pushups
            user.reported_today = True
            user.last_report_date = today
        else:
            if is_total:
                delta = pushups - user.pushups_today
                user.total_pushups += delta
                user.pushups_today = pushups
                logger.debug(f"Обновлён отчёт: новое значение {pushups} (изменение на {delta})")
            else:
                user.pushups_today += pushups
                user.total_pushups += pushups
                logger.debug(f"Добавлены отжимания: +{pushups} → итого за сегодня: {user.pushups_today}")

        self.users.add_or_update(user_id, user)
        self.storage.save(self.config, self.users.all())
        logger.debug("Статистика пользователя сохранена.")

        comment = "Продолжай в том же духе!"
        if self.openai:
            try:
                comment = self.openai.generate_comment(
                    user_prompt=(
                        f"Дай краткий мотивирующий комментарий для @{user.username}, "
                        f"который отжался {user.pushups_today} раз сегодня."
                    ),
                    context=CommentContext.REPORT
                )
                logger.debug(f"Комментарий от OpenAI: {comment}")
            except Exception as e:
                logger.warning(f"OpenAI fallback: {e}")


        total_today = self.users.total_pushups_today(today)
        logger.debug(
            f"Ответ пользователю @{user.username}: {user.pushups_today} сегодня, всего по группе: {total_today}"
        )

        await message.answer(
            f"✅ @{user.username}: {user.pushups_today} отжиманий за сегодня.\n"
            f"💪 Группа: {total_today} сегодня.\n\n{comment}"
        )

    async def handle_mystats(self, message: Message) -> None:
        user_id = message.from_user.id
        user = self.users.get(user_id)

        if not user:
            logger.debug(f"@{message.from_user.username}: запрос /mystats — пользователь не найден.")
            await message.answer("У вас пока нет статистики. Отправьте отчёт, чтобы начать!")
            return

        today = datetime.date.today()
        current_day, days_remaining = self.period.get_day_info(today)

        logger.debug(f"@{user.username}: /mystats — {user.pushups_today} сегодня, {user.total_pushups} всего")

        await message.answer(
            f"📊 @{user.username}\n"
            f"Сегодня: {user.pushups_today} отжиманий\n"
            f"Всего: {user.total_pushups} отжиманий\n"
            f"День челленджа: #{current_day} (осталось {days_remaining})"
        )

    async def handle_stats(self, message: Message) -> None:
        today = datetime.date.today()
        total_today = self.users.total_pushups_today(today)
        total_all = self.users.total_pushups_all_time()
        current_day, _ = self.period.get_day_info(today)

        logger.debug(f"/stats: сегодня {total_today}, всего {total_all}")

        top_today = self.users.sorted_by_pushups_today(today)
        top_list = ""
        if top_today:
            top_list += "🔥 Топ за сегодня:\n"
            for i, (uid, u) in enumerate(top_today, 1):
                top_list += f"{i}. @{u.username}: {u.pushups_today}\n"

        await message.answer(
            f"📈 Сегодня группа сделала: {total_today} отжиманий\n"
            f"🏆 Всего: {total_all} отжиманий\n"
            f"📅 День челленджа: #{current_day}\n\n"
            f"{top_list}"
        )

    async def handle_change_stat(self, message: Message) -> None:
        user_id = message.from_user.id
        args = message.text.strip().split()

        if len(args) < 2 or not args[1].isdigit():
            logger.debug("Некорректный формат /changemydailystats")
            await message.answer("Укажите новое количество отжиманий. Пример: /changemydailystats 100")
            return

        new_value = int(args[1])
        user = self.users.get(user_id)

        if not user:
            logger.debug("Пользователь не найден при /changemydailystats")
            await message.answer("У вас пока нет статистики. Отправьте отчёт, чтобы начать!")
            return

        today = datetime.date.today()
        old_value = user.pushups_today
        delta = new_value - old_value

        user.pushups_today = new_value
        user.total_pushups += delta
        user.last_report_date = today
        user.last_activity = datetime.datetime.now()

        self.users.add_or_update(user_id, user)
        self.storage.save(self.config, self.users.all())

        logger.debug(f"/changemydailystats: @{user.username} {old_value} ➡️ {new_value} (+{delta})")
        await message.answer(f"Изменено: {old_value} ➡️ {new_value} отжиманий.")

    async def handle_setgroup(self, message: Message) -> None:
        if message.chat.type not in ("group", "supergroup"):
            logger.debug("/setgroup вызван не из группы")
            await message.answer("Эта команда работает только в группах.")
            return

        self.config.chat_id = message.chat.id
        self.storage.save(self.config, self.users.all())

        logger.info(f"Группа настроена как основная: chat_id={self.config.chat_id}")
        await message.answer(f"Группа настроена! chat_id: <code>{self.config.chat_id}</code>")

    async def handle_config(self, message: Message) -> None:
        cfg = self.config
        logger.debug(f"/config: {cfg}")
        await message.answer(
            f"🛠 <b>Текущая конфигурация:</b>\n"
            f"Chat ID: <code>{cfg.chat_id}</code>\n"
            f"Напоминание: <b>{cfg.reminder_time}</b>\n"
            f"Предупреждение: {cfg.warning_days} дн\n"
            f"Удаление: {cfg.inactivity_days} дн\n"
            f"Челлендж: {cfg.challenge_start_date} → {cfg.challenge_end_date}"
        )

    async def handle_welcome_new(self, message: Message) -> None:
        for member in message.new_chat_members:
            if member.is_bot:
                continue
            username = member.username or member.full_name
            logger.info(f"Новый участник: @{username}")
            await message.answer(
                f"👋 Добро пожаловать, @{username}!\n"
                f"Не забудь отчитаться сегодня! Пример: 25+25+25=75\n"
                f"Команды: /mystats, /stats"
            )

    async def handle_adminstats(self, message: Message, bot: Bot) -> None:
        try:
            member = await bot.get_chat_member(message.chat.id, message.from_user.id)
            if member.status not in ("creator", "administrator"):
                await message.answer("⛔ Эта команда доступна только администраторам.")
                return
        except TelegramForbiddenError:
            await message.answer("Не удалось проверить статус администратора.")
            return

        total_users = len(self.users.all())
        active_today = len(self.users.get_active_today())
        inactive_4d = len(self.users.get_inactive_for_days(self.config.inactivity_days))
        never_reported = [
            u.username for u in self.users.all().values()
            if not u.last_report_date
        ]

        top_total = self.users.sorted_by_total_pushups()[:5]

        logger.debug(f"/adminstats: {total_users} участников, {active_today} активны, {inactive_4d} неактивны")

        text = (
            "<b>📊 Админ-статистика:</b>\n"
            f"Всего участников: <b>{total_users}</b>\n"
            f"Активны сегодня: <b>{active_today}</b>\n"
            f"Неактивны {self.config.inactivity_days}+ дней: <b>{inactive_4d}</b>\n\n"
        )

        if never_reported:
            text += "❗ Никогда не отчитывались:\n"
            text += "\n".join(f"• @{name}" for name in never_reported[:10]) + "\n\n"

        if top_total:
            text += "🏆 Топ-5 по всем временам:\n"
            for i, (_, user) in enumerate(top_total, 1):
                text += f"{i}. @{user.username}: {user.total_pushups} отж.\n"

        await message.answer(text)