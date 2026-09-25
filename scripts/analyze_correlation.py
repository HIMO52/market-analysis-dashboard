"""
保存済みデータから全銘柄の相関分析を行い、逆相関候補を一覧表示するスクリプト。

実行方法:
    python scripts/analyze_correlation.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.analysis.correlation import (  # noqa: E402
    classify_inverse_correlation_stability,
    compute_daily_returns,
    correlation_matrix_multi_window,
    find_inverse_correlation_candidates,
    pairwise_correlation_table,
)
from src.config import get_db_path, get_ticker_symbols, load_settings  # noqa: E402
from src.storage.db import get_connection, load_prices  # noqa: E402


def main() -> int:
    settings = load_settings()
    windows = settings["analysis"]["correlation_windows_days"]
    threshold = settings["analysis"]["inverse_correlation_threshold"]

    conn = get_connection(get_db_path())
    symbols = get_ticker_symbols()

    price_by_ticker = {}
    for symbol in symbols:
        df = load_prices(conn, symbol)
        if df.empty:
            print(f"{symbol}: データ不足のためスキップします")
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        price_by_ticker[symbol] = df.set_index("timestamp")["adjusted_close"]
    conn.close()

    if len(price_by_ticker) < 2:
        print("相関を計算するには最低2銘柄分のデータが必要です。")
        return 1

    daily_returns = compute_daily_returns(price_by_ticker)
    matrices = correlation_matrix_multi_window(daily_returns, windows)
    table = pairwise_correlation_table(matrices)

    print(f"=== 逆相関候補（相関係数 <= {threshold}、基準期間: 1Y） ===")
    reference = "1Y" if "1Y" in table.columns else list(windows.keys())[-1]
    candidates = find_inverse_correlation_candidates(table, threshold=threshold, reference_column=reference)

    if candidates.empty:
        print("該当するペアはありませんでした。")
    else:
        window_labels = list(windows.keys())
        candidates["安定性"] = candidates.apply(
            lambda row: classify_inverse_correlation_stability(row, window_labels, threshold),
            axis=1,
        )
        print(candidates.round(3).to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
