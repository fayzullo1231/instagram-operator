from datetime import datetime, timezone

SERVER_START_TIME: datetime | None = None


def get_server_start_time() -> datetime:
    global SERVER_START_TIME
    if SERVER_START_TIME is None:
        SERVER_START_TIME = datetime.now(timezone.utc)
    return SERVER_START_TIME


def reset_server_start_time() -> datetime:
    global SERVER_START_TIME
    SERVER_START_TIME = datetime.now(timezone.utc)
    return SERVER_START_TIME
