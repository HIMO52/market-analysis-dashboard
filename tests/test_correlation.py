"""相関分析関数のテスト。完全相関・完全逆相関など、答えが分かっているデータで検証する。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.correlation import (
    classify_inverse_correlation_stability,
    compute_daily_returns,
    correlation_for_window,
    correlation_matrix_multi_window,
    find_inverse_correlation_candidates,
    pairwise_correlation_table,
)


def _make_price_dict(n=100):
    """
    A: ランダムな日次リターンで動く価格
    B: Aと全く同じ日次リターン（スケールだけ異なる）→ 完全に正の相関
    C: Aと正反対の日次リターン → 完全に負の相関

    （価格を先に作ってから逆算すると、offsetの影響でリターンの相関が
    ちょうど+1/-1にならないため、リターンの方を先に作ってから価格を積み上げる）
    """
    rng = np.random.default_rng(42)
    dates = pd.date_range("2025-01-01", periods=n, freq="B")
    daily_returns = rng.normal(loc=0.0005, scale=0.01, size=n - 1)

    a_prices = 100 * np.concatenate([[1.0], np.cumprod(1 + daily_returns)])
    b_prices = 50 * np.concatenate([[1.0], np.cumprod(1 + daily_returns)])  # 同じリターン、スケール違い
    c_prices = 100 * np.concatenate([[1.0], np.cumprod(1 - daily_returns)])  # 正反対のリターン

    return {
        "A": pd.Series(a_prices, index=dates),
        "B": pd.Series(b_prices, index=dates),
        "C": pd.Series(c_prices, index=dates),
    }


def test_compute_daily_returns_shape():
    prices = _make_price_dict(n=50)
    returns = compute_daily_returns(prices)
    assert set(returns.columns) == {"A", "B", "C"}
    assert len(returns) == 49  # pct_changeで1行減る


def test_correlation_for_window_perfect_positive():
    prices = _make_price_dict(n=50)
    returns = compute_daily_returns(prices)
    corr = correlation_for_window(returns, window_days=30)
    assert round(corr.loc["A", "B"], 4) == 1.0


def test_correlation_for_window_perfect_negative():
    prices = _make_price_dict(n=50)
    returns = compute_daily_returns(prices)
    corr = correlation_for_window(returns, window_days=30)
    assert round(corr.loc["A", "C"], 4) == -1.0


def test_correlation_matrix_multi_window_returns_all_labels():
    prices = _make_price_dict(n=100)
    returns = compute_daily_returns(prices)
    matrices = correlation_matrix_multi_window(returns, {"1M": 21, "3M": 63})
    assert set(matrices.keys()) == {"1M", "3M"}


def test_pairwise_correlation_table_has_all_pairs():
    prices = _make_price_dict(n=100)
    returns = compute_daily_returns(prices)
    matrices = correlation_matrix_multi_window(returns, {"1M": 21})
    table = pairwise_correlation_table(matrices)

    pairs = set(zip(table["ticker_a"], table["ticker_b"]))
    assert pairs == {("A", "B"), ("A", "C"), ("B", "C")}


def test_find_inverse_correlation_candidates_finds_ac_pair():
    prices = _make_price_dict(n=100)
    returns = compute_daily_returns(prices)
    matrices = correlation_matrix_multi_window(returns, {"1Y": 90})
    table = pairwise_correlation_table(matrices)

    candidates = find_inverse_correlation_candidates(table, threshold=-0.5, reference_column="1Y")
    pairs = set(zip(candidates["ticker_a"], candidates["ticker_b"]))
    assert ("A", "C") in pairs
    assert ("A", "B") not in pairs  # 正の相関なので候補に入らない


def test_classify_inverse_correlation_stability_all_periods():
    row = pd.Series({"1M": -0.9, "3M": -0.8, "1Y": -0.7})
    result = classify_inverse_correlation_stability(row, ["1M", "3M", "1Y"], threshold=-0.5)
    assert result == "全期間で安定した逆相関"


def test_classify_inverse_correlation_stability_recent_only():
    row = pd.Series({"1M": -0.9, "3M": -0.1, "1Y": 0.2})
    result = classify_inverse_correlation_stability(row, ["1M", "3M", "1Y"], threshold=-0.5)
    assert result == "直近のみの逆相関"


def test_classify_inverse_correlation_stability_long_term_only():
    row = pd.Series({"1M": 0.1, "3M": 0.0, "1Y": -0.9})
    result = classify_inverse_correlation_stability(row, ["1M", "3M", "1Y"], threshold=-0.5)
    assert result == "長期のみの逆相関（直近は弱まっている）"
