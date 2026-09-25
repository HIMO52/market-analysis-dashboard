"""
SQLiteに保存済みの株価データにテクニカル指標を計算し、
各銘柄の最新値を一覧表示する確認用スクリプト。

実行方法:
    python scripts/analyze_technical.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.analysis.technical import add_technical_indicators  # noqa: E402
from src.config import get_db_path, get_ticker_symbols  # noqa: E402
from src.storage.db import get_connection, load_prices  # noqa: E402


def main() -> int:
    conn = get_connection(get_db_path())
    symbols = get_ticker_symbols()

    rows = []
    for symbol in symbols:
        df = load_prices(conn, symbol)
        if df.empty:
            print(f"{symbol}: データ不足（保存済みデータがありません）")
            continue

        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        result = add_technical_indicators(df)
        latest = result.iloc[-1]

        rows.append(
            {
                "ticker": symbol,
                "close": round(latest["close"], 2),
                "1D": _pct(latest.get("return_1D")),
                "5D": _pct(latest.get("return_5D")),
                "20D": _pct(latest.get("return_20D")),
                "SMA50差": _pct(latest["close"] / latest["sma_50"] - 1 if pd.notna(latest.get("sma_50")) else None),
                "SMA200差": _pct(latest["close"] / latest["sma_200"] - 1 if pd.notna(latest.get("sma_200")) else None),
                "52週高値差": _pct(latest.get("pct_from_52w_high")),
                "最大DD": _pct(latest.get("drawdown")),
            }
        )

    conn.close()

    if not rows:
        print("表示できるデータがありません。先に update_market_data.py を実行してください。")
        return 1

    table = pd.DataFrame(rows)
    print(table.to_string(index=False))
    return 0


def _pct(value) -> str:
    if value is None or pd.isna(value):
        return "データ不足"
    return f"{value * 100:+.2f}%"


if __name__ == "__main__":
    raise SystemExit(main())
