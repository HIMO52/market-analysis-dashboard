"""
市場イベントカレンダーの処理。

現時点では config/market_events.yaml に手動登録されたFOMC会合日程のみを扱う。
「取得元が無い場合は無理に作らない」方針のため、CPI・雇用統計などは含まない。
"""

from __future__ import annotations

from datetime import date, datetime


def _parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def split_past_and_upcoming(
    events: list[dict],
    today: date | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    イベント一覧を「過去」と「今後」に分ける。

    判定基準: end_date（無ければstart_date）が today より前なら過去、
    それ以外は今後（当日含む）。

    Returns:
        (past_events, upcoming_events) いずれも日付の早い順にソート済み
    """
    today = today or date.today()

    past = []
    upcoming = []

    for event in events:
        end = _parse_date(event.get("end_date") or event["start_date"])
        if end < today:
            past.append(event)
        else:
            upcoming.append(event)

    past.sort(key=lambda e: e["start_date"])
    upcoming.sort(key=lambda e: e["start_date"])

    return past, upcoming
