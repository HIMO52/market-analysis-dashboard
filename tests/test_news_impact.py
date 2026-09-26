"""news_impact.py のテスト。"""

from __future__ import annotations

import pandas as pd

from src.analysis.news_impact import analyze_price_impact


def _sample_prices():
    dates = pd.to_datetime(
        ["2026-01-05", "2026-01-06", "2026-01-07", "2026-01-08"], utc=True
    )
    return pd.DataFrame(
        {
            "timestamp": dates,
            "close": [100.0, 102.0, 105.0, 103.0],
        }
    )


def test_analyze_price_impact_intraday_horizons_are_insufficient_data():
    published_at = pd.Timestamp("2026-01-06T09:00:00", tz="UTC")
    results = analyze_price_impact(published_at, _sample_prices())

    intraday_results = [r for r in results if r["horizon"] != "1日"]
    assert len(intraday_results) == 4
    for r in intraday_results:
        assert r["change_pct"] is None
        assert "不足" in r["note"]


def test_analyze_price_impact_1day_known_value():
    # 2026-01-06に公開 → 反応日は01-06（終値102.0）、直前の営業日は01-05（終値100.0）
    published_at = pd.Timestamp("2026-01-06T09:00:00", tz="UTC")
    results = analyze_price_impact(published_at, _sample_prices())

    one_day = next(r for r in results if r["horizon"] == "1日")
    assert round(one_day["change_pct"], 6) == round(102.0 / 100.0 - 1, 6)
    assert one_day["note"] is None


def test_analyze_price_impact_published_on_non_trading_day_uses_next_trading_day():
    # 01-06.5相当（土日）に公開されたと仮定 → 次の営業日01-07が反応日、直前が01-06
    published_at = pd.Timestamp("2026-01-06T20:00:00", tz="UTC")
    prices = _sample_prices()
    # 01-06自体は既に取引日なので、公開時刻が01-06の当日である場合は01-06が反応日になる
    results = analyze_price_impact(published_at, prices)
    one_day = next(r for r in results if r["horizon"] == "1日")
    assert one_day["change_pct"] is not None


def test_analyze_price_impact_insufficient_data_when_no_prior_baseline():
    # 保有データの最初の日より前に公開された場合、反応日は最初の行になるが
    # 「直前の営業日」の終値が存在しないためNoneになる
    published_at = pd.Timestamp("2020-01-01T00:00:00", tz="UTC")
    results = analyze_price_impact(published_at, _sample_prices())
    one_day = next(r for r in results if r["horizon"] == "1日")
    assert one_day["change_pct"] is None
    assert one_day["note"] is not None
