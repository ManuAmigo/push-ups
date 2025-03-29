from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import logging
import datetime
from aiogram import Bot
from bot import BotService
from models.bot_models import ActivityStatus
from utils.logger import get_named_logger

logger = get_named_logger()

scheduler = AsyncIOScheduler()

def schedule_reminders(bot: Bot, service: BotService):
    """
    Планирует ежедневное напоминание и проверку неактивности.
    """
    reminder_time = service.config.reminder_time  # формат HH:MM
    hour, minute = map(int, reminder_time.split(":"))

    scheduler.add_job(
        send_daily_reminder,
        CronTrigger(hour=hour, minute=minute),
        args=[bot, service],
        name="daily_reminder",
        replace_existing=True,
    )

    scheduler.add_job(
        check_inactive_users,
        CronTrigger(hour=23, minute=59),
        args=[bot, service],
        name="kick_inactive_users",
        replace_existing=True,
    )

    scheduler.add_job(
        check_inactivity_warnings,
        CronTrigger(hour=20, minute=0),
        args=[bot, service],
        name="warn_inactive_users",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(f"Планировщик активирован: напоминание в {reminder_time}, предупреждение в 20:00, удаление в 23:59")


async def send_daily_reminder(bot: Bot, service: BotService):
    chat_id = service.config.chat_id
    if not chat_id:
        logger.warning("chat_id не задан — напоминание не отправлено")
        return

    today = service.users.total_pushups_today()
    current_day, days_remaining = service.period.get_day_info()

    message = (
        f"⏰ Напоминание!\n"
        f"Сегодня день #{current_day} челленджа. Осталось {days_remaining} дн.\n"
        f"Не забудьте отчитаться о своих отжиманиях сегодня.\n"
        f"Пример: 25+25+25+25=100"
    )

    try:
        await bot.send_message(chat_id=chat_id, text=message)
        logger.info(f"Напоминание отправлено в чат {chat_id}. Сегодня уже сделано: {today} отжиманий")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}")


async def check_inactive_users(bot: Bot, service: BotService):
    chat_id = service.config.chat_id
    if not chat_id:
        logger.warning("chat_id не задан — пропуск удаления неактивных")
        return

    now = datetime.datetime.now()
    to_remove = []
    for user_id, user in service.users.all().items():
        status = user.activity_status(
            current_date=now,
            inactivity_days=service.config.inactivity_days,
            warning_days=service.config.warning_days
        )
        if status == ActivityStatus.INACTIVE:
            to_remove.append((user_id, user.username))

    for user_id, username in to_remove:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id)
            await bot.send_message(
                chat_id,
                text=f"⛔ @{username} исключён из группы за неактивность."
            )
            service.users.remove(user_id)
            logger.info(f"Удалён @{username} ({user_id}) за неактивность")
        except Exception as e:
            logger.error(f"Ошибка удаления @{username}: {e}")

    if to_remove:
        service.storage.save(service.config, service.users.all())

        logger.info(f"Сохранено после удаления {len(to_remove)} пользователей")


async def check_inactivity_warnings(bot: Bot, service: BotService):
    chat_id = service.config.chat_id
    if not chat_id:
        logger.warning("chat_id не задан — пропуск предупреждений о неактивности")
        return

    now = datetime.datetime.now()
    warning_list = []
    for user_id, user in service.users.all().items():
        status = user.activity_status(
            current_date=now,
            inactivity_days=service.config.inactivity_days,
            warning_days=service.config.warning_days
        )
        if status == ActivityStatus.WARNING:
            warning_list.append((user_id, user.username))

    for user_id, username in warning_list:
        try:
            days_left = service.config.inactivity_days - service.config.warning_days
            await bot.send_message(
                chat_id,
                text=(
                    f"⚠️ @{username}, вы не отчитывались уже {service.config.warning_days} дня.\n"
                    f"Если не будет активности ещё {days_left} дн., вы будете исключены."
                )
            )
            logger.info(f"Предупреждение о неактивности отправлено для @{username}")
        except Exception as e:
            logger.error(f"Ошибка при отправке предупреждения @{username}: {e}")
