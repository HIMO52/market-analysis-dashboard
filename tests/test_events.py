"""events/calendar.py のテスト。"""

from __future__ import annotations

from datetime import date

from src.config import load_market_events
from src.events.calendar import split_past_and_upcoming


def test_load_market_events_returns_fomc_events():
    events = load_market_events()
    assert len(events) >= 1
    assert all(e["type"] == "FOMC" for e in events)


def test_split_past_and_upcoming_basic():
    events = [
        {"name": "過去イベント", "start_date": "2026-01-01", "end_date": "2026-01-02"},
        {"name": "未来イベント", "start_date": "2026-12-01", "end_date": "2026-12-02"},
    ]
    past, upcoming = split_past_and_upcoming(events, today=date(2026, 6, 1))

    assert [e["name"] for e in past] == ["過去イベント"]
    assert [e["name"] for e in upcoming] == ["未来イベント"]


def test_split_past_and_upcoming_today_counts_as_upcoming():
    events = [{"name": "今日開催", "start_date": "2026-06-01", "end_date": "2026-06-01"}]
    past, upcoming = split_past_and_upcoming(events, today=date(2026, 6, 1))
    assert past == []
    assert len(upcoming) == 1


def test_split_past_and_upcoming_sorted_by_date():
    events = [
        {"name": "12月", "start_date": "2026-12-08", "end_date": "2026-12-09"},
        {"name": "10月", "start_date": "2026-10-27", "end_date": "2026-10-28"},
    ]
    _, upcoming = split_past_and_upcoming(events, today=date(2026, 1, 1))
    assert [e["name"] for e in upcoming] == ["10月", "12月"]
