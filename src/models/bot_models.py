from typing import Optional, Tuple
from pydantic import BaseModel, field_validator
from datetime import datetime, date
from enum import Enum


# Тип генерации комментария
class CommentContext(str, Enum):
    REPORT = "report"
    DAILY_STATS = "daily_stats"
    PERSONAL = "personal"


# Статус активности пользователя
class ActivityStatus(str, Enum):
    ACTIVE = "active"
    WARNING = "warning"
    INACTIVE = "inactive"


# Конфигурация бота
class BotConfig(BaseModel):
    chat_id: Optional[int] = None
    inactivity_days: int = 4
    reminder_time: str = "22:00"
    warning_days: int = 2
    challenge_start_date: date
    challenge_end_date: date

    @field_validator("reminder_time")
    def check_time_format(self, v: str) -> str:
        hours, minutes = map(int, v.split(":"))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Неверный формат времени")
        return v

    @field_validator("warning_days")
    def check_warning_vs_inactive(self, v, info):
        inactivity_days = info.data.get("inactivity_days")
        if inactivity_days is not None and v >= inactivity_days:
            raise ValueError("warning_days должен быть меньше inactivity_days")
        return v

    @field_validator("challenge_end_date")
    def check_dates(self, v, info):
        start_date = info.data.get("challenge_start_date")
        if start_date and v <= start_date:
            raise ValueError("Дата окончания должна быть позже даты начала")
        return v


# Информация о пользователе
class UserInfo(BaseModel):
    username: str
    last_activity: Optional[datetime] = None
    pushups_today: int = 0
    reported_today: bool = False
    last_report_date: Optional[date] = None
    total_pushups: int = 0

    def activity_status(
        self,
        current_date: Optional[datetime] = None,
        inactivity_days: int = 4,
        warning_days: int = 2
    ) -> ActivityStatus:
        current_date = current_date or datetime.now()
        if not self.last_activity:
            return ActivityStatus.INACTIVE
        inactive_days_count = (current_date - self.last_activity).days
        if inactive_days_count >= inactivity_days:
            return ActivityStatus.INACTIVE
        elif inactive_days_count >= warning_days:
            return ActivityStatus.WARNING
        return ActivityStatus.ACTIVE


# Период челленджа
class ChallengePeriod(BaseModel):
    start_date: date
    end_date: date

    def get_day_info(self, today: Optional[date] = None) -> Tuple[int, int]:
        today = today or date.today()
        if today < self.start_date:
            return 0, (self.end_date - self.start_date).days
        if today > self.end_date:
            total_days = (self.end_date - self.start_date).days
            return total_days, 0
        current_day = (today - self.start_date).days + 1
        days_remaining = (self.end_date - today).days
        return current_day, days_remaining
