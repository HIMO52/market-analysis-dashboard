"""webdata/build.py のテスト。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.webdata.build import (
    build_correlation_data,
    build_market_overview,
    build_news_data,
    build_status_data,
    build_ticker_overview,
)


def _sample_price_df(n=260, start=100.0, end=150.0):
    dates = pd.date_range("2025-01-01", periods=n, freq="B", tz="UTC")
    prices = np.linspace(start, end, n)
    return pd.DataFrame(
        {
            "timestamp": dates,
            "close": prices,
            "adjusted_close": prices,
        }
    )


def test_build_ticker_overview_returns_expected_keys():
    entry = build_ticker_overview("SPY", _sample_price_df())
    assert entry["ticker"] == "SPY"
    assert entry["close"] is not None
    assert "change_1d" in entry
    assert "sma50_position" in entry
    assert "sma200_position" in entry


def test_build_ticker_overview_empty_returns_none():
    assert build_ticker_overview("SPY", pd.DataFrame()) is None


def test_build_ticker_overview_sma_position_above_when_rising():
    # 単調増加なので、直近の終値はSMAより上にあるはず
    entry = build_ticker_overview("SPY", _sample_price_df())
    assert entry["sma50_position"] == "above"
    assert entry["sma200_position"] == "above"


def test_build_market_overview_multiple_tickers():
    data = {
        "SPY": _sample_price_df(),
        "QQQ": _sample_price_df(start=200.0, end=250.0),
    }
    overview = build_market_overview(data)
    assert len(overview) == 2
    tickers = {e["ticker"] for e in overview}
    assert tickers == {"SPY", "QQQ"}


def test_build_market_overview_skips_empty_data():
    data = {"SPY": _sample_price_df(), "TLT": pd.DataFrame()}
    overview = build_market_overview(data)
    tickers = {e["ticker"] for e in overview}
    assert tickers == {"SPY"}


def test_build_correlation_data_structure():
    rng = np.random.default_rng(0)
    dates = pd.date_range("2025-01-01", periods=100, freq="B", tz="UTC")
    r = rng.normal(0.0003, 0.01, 99)
    a_prices = 100 * np.concatenate([[1.0], np.cumprod(1 + r)])
    c_prices = 100 * np.concatenate([[1.0], np.cumprod(1 - r)])

    price_series = {
        "A": pd.Series(a_prices, index=dates),
        "C": pd.Series(c_prices, index=dates),
    }
    data = build_correlation_data(price_series, {"1M": 21}, threshold=-0.5)

    assert data["windows"] == ["1M"]
    assert "A" in data["matrices"]["1M"]
    assert len(data["inverse_pairs"]) == 1


def test_build_news_data_converts_related_tickers_to_list():
    df = pd.DataFrame(
        [
            {
                "title": "記事1",
                "url": "https://example.com/1",
                "source": "テスト",
                "published_at": "2026-01-01T00:00:00+00:00",
                "related_tickers": "SPY,TLT",
                "importance": "HIGH",
            }
        ]
    )
    result = build_news_data(df)
    assert result[0]["related_tickers"] == ["SPY", "TLT"]
    assert result[0]["importance"] == "HIGH"


def test_build_news_data_empty_df_returns_empty_list():
    assert build_news_data(pd.DataFrame()) == []


def test_build_status_data_handles_none():
    result = build_status_data(None, None)
    assert result["market_data"]["tickers"] == {}
    assert result["news"]["sources"] == {}
