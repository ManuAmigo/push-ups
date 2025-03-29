import datetime
from typing import Dict, Optional

from models.bot_models import UserInfo


class UserRepository:
    def __init__(self, user_data: Optional[Dict[int, UserInfo]] = None):
        self.users: Dict[int, UserInfo] = user_data or {}

    def get(self, user_id: int) -> Optional[UserInfo]:
        return self.users.get(user_id)

    def add_or_update(self, user_id: int, user: UserInfo):
        self.users[user_id] = user

    def remove(self, user_id: int):
        if user_id in self.users:
            del self.users[user_id]

    def all(self) -> Dict[int, UserInfo]:
        return self.users

    def get_active_today(self, today: Optional[datetime.date] = None):
        today = today or datetime.date.today()
        return {
            uid: u for uid, u in self.users.items()
            if u.last_report_date == today
        }

    def get_inactive_for_days(self, days: int, now: Optional[datetime.datetime] = None):
        now = now or datetime.datetime.now()
        return {
            uid: u for uid, u in self.users.items()
            if (now - u.last_activity).days >= days
        }

    def total_pushups_today(self, today: Optional[datetime.date] = None) -> int:
        return sum(u.pushups_today for u in self.get_active_today(today).values())

    def total_pushups_all_time(self) -> int:
        return sum(u.total_pushups for u in self.users.values())

    def sorted_by_pushups_today(self, today: Optional[datetime.date] = None):
        return sorted(
            self.get_active_today(today).items(),
            key=lambda x: x[1].pushups_today,
            reverse=True
        )

    def sorted_by_total_pushups(self):
        return sorted(
            self.users.items(),
            key=lambda x: x[1].total_pushups,
            reverse=True
        )
