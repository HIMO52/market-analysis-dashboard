"""テクニカル分析関数のテスト。既知の入力に対して、既知の答えになるかを検算する。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.technical import (
    add_technical_indicators,
    ema,
    max_drawdown,
    pct_from_52week_high,
    pct_from_52week_low,
    period_return,
    rolling_52week_high_low,
    rolling_volatility,
    sma,
)


def test_sma_of_constant_series_equals_constant():
    prices = pd.Series([100.0] * 30)
    result = sma(prices, 10)
    # 最初の9個(window未満)はNaN、10個目以降は100になるはず
    assert result.iloc[:9].isna().all()
    assert result.iloc[9:].round(6).eq(100.0).all()


def test_sma_known_values():
    prices = pd.Series([1, 2, 3, 4, 5], dtype=float)
    result = sma(prices, 3)
    # (1+2+3)/3=2, (2+3+4)/3=3, (3+4+5)/3=4
    assert result.iloc[2] == 2.0
    assert result.iloc[3] == 3.0
    assert result.iloc[4] == 4.0


def test_ema_of_constant_series_equals_constant():
    prices = pd.Series([50.0] * 20)
    result = ema(prices, 10)
    assert result.iloc[9:].round(6).eq(50.0).all()


def test_period_return_known_value():
    prices = pd.Series([100.0, 110.0, 121.0])
    result = period_return(prices, 1)
    # (110/100) - 1 = 0.10
    assert round(result.iloc[1], 6) == 0.10
    # (121/110) - 1 = 0.10
    assert round(result.iloc[2], 6) == 0.10


def test_rolling_volatility_zero_for_constant_prices():
    prices = pd.Series([100.0] * 30)
    result = rolling_volatility(prices, 10, annualize=False)
    assert result.iloc[10:].round(10).eq(0.0).all()


def test_rolling_52week_high_low_simple_increasing_series():
    prices = pd.Series(range(1, 11), dtype=float)  # 1,2,...,10
    high, low = rolling_52week_high_low(prices)
    # データが252日未満でも、その時点までの最大・最小を返す
    assert high.iloc[-1] == 10.0
    assert low.iloc[-1] == 1.0
    assert high.iloc[0] == 1.0  # 初日は自分自身が高値でもある


def test_pct_from_52week_high_is_zero_at_the_high():
    prices = pd.Series([90.0, 100.0, 95.0])
    high, _ = rolling_52week_high_low(prices)
    pct = pct_from_52week_high(prices, high)
    assert round(pct.iloc[1], 6) == 0.0  # 高値そのものの日は0%
    assert round(pct.iloc[2], 6) == round(95.0 / 100.0 - 1, 6)


def test_pct_from_52week_low_is_zero_at_the_low():
    prices = pd.Series([100.0, 90.0, 95.0])
    _, low = rolling_52week_high_low(prices)
    pct = pct_from_52week_low(prices, low)
    assert round(pct.iloc[1], 6) == 0.0


def test_max_drawdown_known_scenario():
    # 100 -> 120（最高値） -> 90 という値動き
    prices = pd.Series([100.0, 120.0, 90.0])
    dd = max_drawdown(prices)
    # 90 / 120 - 1 = -0.25
    assert round(dd, 6) == -0.25


def test_max_drawdown_no_drawdown_when_always_rising():
    prices = pd.Series([100.0, 110.0, 120.0])
    assert max_drawdown(prices) == 0.0


def test_max_drawdown_empty_series_returns_nan():
    assert np.isnan(max_drawdown(pd.Series([], dtype=float)))


def test_add_technical_indicators_adds_expected_columns():
    n = 260  # 200日SMAや52週の計算が意味を持つ程度の長さ
    df = pd.DataFrame(
        {
            "timestamp": pd.date_range("2025-01-01", periods=n, freq="D"),
            "adjusted_close": np.linspace(100, 200, n),
        }
    )
    result = add_technical_indicators(df)

    expected_columns = {
        "sma_20", "sma_50", "sma_200", "ema_20", "ema_50",
        "return_1D", "return_5D", "return_20D", "return_60D", "return_1Y",
        "volatility_20D", "volatility_60D",
        "high_52w", "low_52w", "pct_from_52w_high", "pct_from_52w_low",
        "drawdown",
    }
    assert expected_columns.issubset(set(result.columns))
    assert len(result) == n

    # 価格が単調増加なので、最終日は52週高値と一致し、ドローダウンは0のはず
    assert round(result["pct_from_52w_high"].iloc[-1], 6) == 0.0
    assert result["drawdown"].iloc[-1] == 0.0
