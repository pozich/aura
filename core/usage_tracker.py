from datetime import datetime, timedelta, timezone

from data.db import get_connection


def log_call(
    model: str, tokens: int | None = None, api_key_id: int | None = None
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO usage_log (api_key_id, model, tokens) VALUES (?, ?, ?)",
        (api_key_id, model, tokens),
    )
    conn.commit()
    conn.close()


def _today_start_utc() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


def calls_today(model: str | None = None) -> int:
    conn = get_connection()
    query = "SELECT COUNT(*) FROM usage_log WHERE called_at >= ?"
    params: list = [_today_start_utc()]
    if model:
        query += " AND model = ?"
        params.append(model)
    count = conn.execute(query, params).fetchone()[0]
    conn.close()
    return count


def seconds_until_reset() -> int:
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return int((tomorrow - now).total_seconds())


def remaining_today(daily_limit: int, model: str | None = None) -> int:
    return max(0, daily_limit - calls_today(model))
