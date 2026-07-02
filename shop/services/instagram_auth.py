import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

AUTH_COOLDOWN_MINUTES = 60


class InstagramAuthState:
    """Instagram login holati — bloklanganda qayta urinishni to'xtatadi."""

    def __init__(self) -> None:
        self.blocked = False
        self.blocked_until: datetime | None = None
        self.last_error: str = ""

    def block(self, reason: str, minutes: int = AUTH_COOLDOWN_MINUTES) -> None:
        self.blocked = True
        self.last_error = reason
        self.blocked_until = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        logger.error(
            "Instagram polling to'xtatildi (%d daqiqa). Sabab: %s",
            minutes,
            reason,
        )

    def is_blocked(self) -> bool:
        if not self.blocked:
            return False
        if self.blocked_until and datetime.now(timezone.utc) >= self.blocked_until:
            self.blocked = False
            self.blocked_until = None
            self.last_error = ""
            logger.info("Instagram auth cooldown tugadi, qayta urinish mumkin")
            return False
        return True

    def status(self) -> dict:
        return {
            "blocked": self.is_blocked(),
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None,
            "last_error": self.last_error,
        }


auth_state = InstagramAuthState()
