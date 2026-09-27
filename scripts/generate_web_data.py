"""
docs/data/ 以下にWebダッシュボード用のJSONファイルを生成するスクリプト。

実行方法:
    python scripts/generate_web_data.py

生成されるファイル:
    docs/data/overview.json      … MARKET OVERVIEW（主要銘柄の現在値・変化率など）
    docs/data/correlation.json   … 相関ヒートマップ・逆相関ペア一覧
    docs/data/news.json          … 最新ニュース一覧
    docs/data/status.json        … 更新履歴・エラー状況
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.config import PROJECT_ROOT, get_db_path, get_ticker_symbols, load_settings  # noqa: E402
from src.storage.db import get_connection, load_all_news, load_prices  # noqa: E402
from src.webdata.build import (  # noqa: E402
    build_correlation_data,
    build_market_overview,
    build_news_data,
    build_status_data,
    write_json,
)

DOCS_DATA_DIR = PROJECT_ROOT / "docs" / "data"


def _load_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    settings = load_settings()
    conn = get_connection(get_db_path())
    symbols = get_ticker_symbols()

    price_frames = {}
    price_series = {}
    for symbol in symbols:
        df = load_prices(conn, symbol)
        if df.empty:
            continue
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.dropna(subset=["close"])
        if df.empty:
            continue
        price_frames[symbol] = df
        price_series[symbol] = df.set_index("timestamp")["adjusted_close"]

    # 1. MARKET OVERVIEW（主要銘柄のみ）
    overview = build_market_overview({t: price_frames[t] for t in price_frames})
    write_json(overview, DOCS_DATA_DIR / "overview.json")
    print(f"overview.json を書き出しました（{len(overview)}銘柄）")

    # 2. 相関・逆相関
    if len(price_series) >= 2:
        windows = settings["analysis"]["correlation_windows_days"]
        threshold = settings["analysis"]["inverse_correlation_threshold"]
        correlation_data = build_correlation_data(price_series, windows, threshold)
        write_json(correlation_data, DOCS_DATA_DIR / "correlation.json")
        print(f"correlation.json を書き出しました（逆相関候補 {len(correlation_data['inverse_pairs'])}件）")
    else:
        print("相関計算に必要な銘柄数が足りないため、correlation.json はスキップしました。")

    # 3. ニュース
    news_df = load_all_news(conn)
    news_data = build_news_data(news_df)
    write_json(news_data, DOCS_DATA_DIR / "news.json")
    print(f"news.json を書き出しました（{len(news_data)}件）")

    conn.close()

    # 4. ステータス（更新履歴・エラー）
    status_dir = PROJECT_ROOT / "data" / "status"
    market_status = _load_json_if_exists(status_dir / "market_data_status.json")
    news_status = _load_json_if_exists(status_dir / "news_status.json")
    status_data = build_status_data(market_status, news_status)
    write_json(status_data, DOCS_DATA_DIR / "status.json")
    print("status.json を書き出しました")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
