"""
GitHub Pagesで表示するWebダッシュボード用に、SQLiteのデータを
JSONとして書き出すためのデータ整形ロジック。

このファイル自体はファイルの読み書きを行わない（読み書きは
scripts/generate_web_data.py が行う）。ここには純粋なデータ整形の
関数だけを置き、テストしやすくしている。
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.analysis.correlation import (
    compute_daily_returns,
    correlation_matrix_multi_window,
    find_inverse_correlation_candidates,
    pairwise_correlation_table,
)
from src.analysis.technical import add_technical_indicators

# トップページ(MARKET OVERVIEW)で優先的に表示する主要銘柄
OVERVIEW_TICKERS = ["SPY", "QQQ", "IWM", "DIA", "TLT", "GLD"]


def _sma_position(close: float, sma: float | None) -> str | None:
    """終値が移動平均線の上か下かを文字列で返す（"above"/"below"）。データが無ければNone。"""
    if sma is None or pd.isna(sma):
        return None
    return "above" if close >= sma else "below"


def build_ticker_overview(ticker: str, price_history: pd.DataFrame) -> dict | None:
    """
    1銘柄分の価格履歴（timestamp昇順、adjusted_close等を含む）から、
    MARKET OVERVIEW表示用の1件分のデータを作る。
    データが無ければNoneを返す。
    """
    if price_history.empty:
        return None

    result = add_technical_indicators(price_history)
    latest = result.iloc[-1]

    return {
        "ticker": ticker,
        "close": round(float(latest["close"]), 4) if pd.notna(latest["close"]) else None,
        "change_1d": _safe_round(latest.get("return_1D")),
        "change_5d": _safe_round(latest.get("return_5D")),
        "change_20d": _safe_round(latest.get("return_20D")),
        "pct_from_52w_high": _safe_round(latest.get("pct_from_52w_high")),
        "sma50_position": _sma_position(latest["close"], latest.get("sma_50")),
        "sma200_position": _sma_position(latest["close"], latest.get("sma_200")),
        "as_of": str(latest["timestamp"]),
    }


def _safe_round(value, digits: int = 6):
    if value is None or pd.isna(value):
        return None
    return round(float(value), digits)


def build_market_overview(price_by_ticker: dict[str, pd.DataFrame]) -> list[dict]:
    """複数銘柄分のMARKET OVERVIEWデータをまとめて作る。"""
    overview = []
    for ticker, df in price_by_ticker.items():
        entry = build_ticker_overview(ticker, df)
        if entry:
            overview.append(entry)
    return overview


def build_correlation_data(
    price_by_ticker: dict[str, pd.Series],
    windows: dict[str, int],
    threshold: float,
) -> dict:
    """
    相関ヒートマップ・逆相関ペア一覧のためのデータを作る。

    Returns:
        {
          "windows": ["1M", "3M", ...],
          "tickers": ["SPY", "QQQ", ...],
          "matrices": {"1M": {"SPY": {"QQQ": 0.9, ...}, ...}, ...},
          "inverse_pairs": [{"ticker_a":..., "ticker_b":..., "1M":..., ..., "安定性":...}, ...]
        }
    """
    daily_returns = compute_daily_returns(price_by_ticker)
    matrices = correlation_matrix_multi_window(daily_returns, windows)
    table = pairwise_correlation_table(matrices)

    reference = "1Y" if "1Y" in table.columns else list(windows.keys())[-1]
    inverse_pairs = find_inverse_correlation_candidates(table, threshold=threshold, reference_column=reference)

    matrices_json = {
        label: json.loads(matrix.round(4).to_json(orient="columns")) for label, matrix in matrices.items()
    }

    return {
        "windows": list(windows.keys()),
        "tickers": sorted(price_by_ticker.keys()),
        "threshold": threshold,
        "matrices": matrices_json,
        "inverse_pairs": inverse_pairs.round(4).to_dict(orient="records"),
    }


def build_news_data(news_df: pd.DataFrame, limit: int = 30) -> list[dict]:
    """保存済みニュースのDataFrameを、Web表示用のリストに変換する。"""
    if news_df.empty:
        return []

    trimmed = news_df.head(limit).copy()
    records = []
    for _, row in trimmed.iterrows():
        records.append(
            {
                "title": row["title"],
                "url": row["url"],
                "source": row["source"],
                "published_at": row.get("published_at"),
                "related_tickers": (row.get("related_tickers") or "").split(",")
                if row.get("related_tickers")
                else [],
                "importance": row.get("importance") or "LOW",
            }
        )
    return records


def build_status_data(
    market_status: dict | None,
    news_status: dict | None,
) -> dict:
    """更新履歴・エラー表示用のステータスデータを作る。"""
    return {
        "market_data": market_status or {"run_at": None, "tickers": {}},
        "news": news_status or {"run_at": None, "sources": {}},
    }


def write_json(data, path: Path) -> None:
    """データをJSONファイルとして書き出す（ディレクトリが無ければ作成する）。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
