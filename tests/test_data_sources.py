"""
データ取得まわりのテスト。

【方針】yfinanceへの実際のネットワーク通信は行わない。
列名変換ロジック（normalize_yfinance_dataframe）と、
複数銘柄処理でエラーが起きても止まらないこと（fetch_all）を、
ダミーのデータ・ダミーのデータ取得元で検証する。
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.data_sources.base import DataSourceError, PriceDataSource
from src.data_sources.fetcher import fetch_all, fetch_and_tag
from src.data_sources.yfinance_source import normalize_yfinance_dataframe


# ---- normalize_yfinance_dataframe のテスト ----

def _fake_yfinance_raw_dataframe() -> pd.DataFrame:
    """yfinanceのTicker.history()が返す形を模したダミーDataFrame。"""
    index = pd.to_datetime(["2026-01-05", "2026-01-06"])
    index.name = "Date"
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0],
            "High": [102.0, 103.0],
            "Low": [99.0, 100.0],
            "Close": [101.5, 102.5],
            "Volume": [1000, 1200],
            "Adj Close": [101.0, 102.0],
        },
        index=index,
    )


def test_normalize_yfinance_dataframe_renames_columns():
    raw = _fake_yfinance_raw_dataframe()
    df = normalize_yfinance_dataframe(raw, "SPY")

    assert list(df.columns) == [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "adjusted_close",
    ]
    assert len(df) == 2
    assert df["adjusted_close"].iloc[0] == 101.0


def test_normalize_yfinance_dataframe_empty_raises():
    empty = pd.DataFrame()
    with pytest.raises(DataSourceError):
        normalize_yfinance_dataframe(empty, "SPY")


def test_normalize_yfinance_dataframe_missing_adjusted_close_falls_back():
    raw = _fake_yfinance_raw_dataframe().drop(columns=["Adj Close"])
    df = normalize_yfinance_dataframe(raw, "SPY")
    # Adj Closeが無い場合はcloseの値で代用する（推測はしない、closeをそのまま使う）
    assert (df["adjusted_close"] == df["close"]).all()


# ---- fetch_all / fetch_and_tag のテスト（ダミーのデータ取得元を使用） ----

class DummySource(PriceDataSource):
    """テスト専用のダミーデータ取得元。特定銘柄だけ失敗させられる。"""

    name = "dummy"

    def __init__(self, fail_symbols: set[str] | None = None):
        self.fail_symbols = fail_symbols or set()

    def fetch_ohlcv(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        if symbol in self.fail_symbols:
            raise DataSourceError(f"{symbol}: テスト用の意図的な失敗")
        return pd.DataFrame(
            {
                "timestamp": pd.to_datetime(["2026-01-05"]),
                "open": [1.0],
                "high": [2.0],
                "low": [0.5],
                "close": [1.5],
                "volume": [100],
                "adjusted_close": [1.5],
            }
        )


def test_fetch_and_tag_adds_source_and_ticker_columns():
    source = DummySource()
    df = fetch_and_tag(source, "SPY")
    assert df["ticker"].iloc[0] == "SPY"
    assert df["source"].iloc[0] == "dummy"
    assert "retrieved_at" in df.columns


def test_fetch_all_continues_after_one_symbol_fails():
    source = DummySource(fail_symbols={"TLT"})
    results, errors = fetch_all(source, ["SPY", "QQQ", "TLT"])

    assert set(results.keys()) == {"SPY", "QQQ"}
    assert set(errors.keys()) == {"TLT"}
    assert "TLT" in errors["TLT"]


def test_fetch_all_all_succeed_when_no_failures():
    source = DummySource()
    results, errors = fetch_all(source, ["SPY", "QQQ"])
    assert len(results) == 2
    assert len(errors) == 0
