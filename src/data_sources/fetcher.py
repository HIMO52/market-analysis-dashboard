"""
複数銘柄の株価データ取得をまとめて行う処理。

【重要】一部の銘柄の取得に失敗しても、他の銘柄の取得は続ける
（例: SPY OK / QQQ OK / TLT ERROR のように、成功と失敗を両方記録する）。
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd

from .base import DataSourceError, PriceDataSource


def fetch_and_tag(source: PriceDataSource, symbol: str, period: str = "2y") -> pd.DataFrame:
    """
    1銘柄分のデータを取得し、"source"（取得元）と
    "retrieved_at"（取得日時、UTC）の列を追加して返す。
    """
    df = source.fetch_ohlcv(symbol, period=period)
    df = df.copy()
    df["source"] = source.name
    df["retrieved_at"] = datetime.now(timezone.utc).isoformat()
    df.insert(0, "ticker", symbol)
    return df


def fetch_all(
    source: PriceDataSource,
    symbols: list[str],
    period: str = "2y",
) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    """
    複数銘柄を順番に取得する。

    Returns:
        (成功した銘柄のDataFrame辞書, 失敗した銘柄とエラー理由の辞書)
        例: results, errors = fetch_all(...)
            results = {"SPY": <DataFrame>, "QQQ": <DataFrame>}
            errors  = {"TLT": "TLT: yfinanceからの取得に失敗しました: ..."}
    """
    results: dict[str, pd.DataFrame] = {}
    errors: dict[str, str] = {}

    for symbol in symbols:
        try:
            results[symbol] = fetch_and_tag(source, symbol, period=period)
        except DataSourceError as e:
            errors[symbol] = str(e)
        except Exception as e:  # 想定外のエラーも、他の銘柄を止めないよう捕捉する
            errors[symbol] = f"{symbol}: 想定外のエラー: {e}"

    return results, errors
