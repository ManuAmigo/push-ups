#file: /Users/andreynaumov/PycharmProjects/push-ups/push-ups_bot/models/bot_models.py
from dataclasses import dataclass, asdict
from typing import Optional, Tuple
from enum import Enum
import datetime

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
@dataclass
class BotConfig:
    chat_id: Optional[int] = None
    inactivity_days: int = 4
    reminder_time: str = "22:00"
    warning_days: int = 2
    challenge_start_date: datetime.date = datetime.date(2025, 3, 15)
    challenge_end_date: datetime.date = datetime.date(2025, 6, 13)

    def __post_init__(self):
        hours, minutes = map(int, self.reminder_time.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError("Некорректный формат reminder_time (HH:MM)")
        if self.warning_days >= self.inactivity_days:
            raise ValueError("warning_days должен быть меньше inactivity_days")
        if self.challenge_start_date >= self.challenge_end_date:
            raise ValueError("Дата начала челленджа должна быть раньше даты окончания")

    @staticmethod
    def from_dict(data: dict) -> 'BotConfig':
        data['challenge_start_date'] = datetime.date.fromisoformat(data['challenge_start_date'])
        data['challenge_end_date'] = datetime.date.fromisoformat(data['challenge_end_date'])
        return BotConfig(**data)

    def to_dict(self) -> dict:
        data = asdict(self) # type: ignore[arg-type]
        data['challenge_start_date'] = self.challenge_start_date.isoformat()
        data['challenge_end_date'] = self.challenge_end_date.isoformat()
        return data

# Информация о пользователе
@dataclass
class UserInfo:
    username: str
    last_activity: Optional[datetime.datetime] = None
    pushups_today: int = 0
    reported_today: bool = False
    last_report_date: Optional[datetime.date] = None
    total_pushups: int = 0

    def activity_status(self, current_date: Optional[datetime.datetime] = None, inactivity_days: int = 4, warning_days: int = 2) -> ActivityStatus:
        current_date = current_date or datetime.datetime.now()
        if not self.last_activity:
            return ActivityStatus.INACTIVE
        inactive_days_count = (current_date - self.last_activity).days
        if inactive_days_count >= inactivity_days:
            return ActivityStatus.INACTIVE
        elif inactive_days_count >= warning_days:
            return ActivityStatus.WARNING
        return ActivityStatus.ACTIVE

    @staticmethod
    def from_dict(data: dict) -> 'UserInfo':
        return UserInfo(
            username=data['username'],
            last_activity=datetime.datetime.fromisoformat(data['last_activity']) if data.get('last_activity') else None,
            pushups_today=data.get('pushups_today', 0),
            reported_today=data.get('reported_today', False),
            last_report_date=datetime.date.fromisoformat(data['last_report_date']) if data.get('last_report_date') else None,
            total_pushups=data.get('total_pushups', 0)
        )

    def to_dict(self) -> dict:
        return {
            'username': self.username,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'pushups_today': self.pushups_today,
            'reported_today': self.reported_today,
            'last_report_date': self.last_report_date.isoformat() if self.last_report_date else None,
            'total_pushups': self.total_pushups
        }

# Период челленджа
@dataclass
class ChallengePeriod:
    start_date: datetime.date
    end_date: datetime.date

    def get_day_info(self, today: Optional[datetime.date] = None) -> Tuple[int, int]:
        today = today or datetime.date.today()
        if today < self.start_date:
            return 0, (self.end_date - self.start_date).days
        if today > self.end_date:
            total_days = (self.end_date - self.start_date).days
            return total_days, 0
        current_day = (today - self.start_date).days + 1
        days_remaining = (self.end_date - today).days
        return current_day, days_remaining