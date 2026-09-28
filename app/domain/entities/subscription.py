from dataclasses import dataclass, field
from datetime import datetime, timedelta

@dataclass
class SearchSubscription:
    telegram_chat_id: int
    role: str
    duration_days: int
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(init=False)
    id: int | None = None

    def __post_init__(self):
        self.expires_at = self.created_at + timedelta(days=self.duration_days)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at