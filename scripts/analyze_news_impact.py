"""
保存済みニュースのうち、関連銘柄が分かっているものについて、
値動き分析（Phase 11）を表示する確認用スクリプト。

実行方法:
    python scripts/analyze_news_impact.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.analysis.news_impact import analyze_price_impact  # noqa: E402
from src.config import get_db_path  # noqa: E402
from src.storage.db import get_connection, load_all_news, load_prices  # noqa: E402


def main() -> int:
    conn = get_connection(get_db_path())
    news_df = load_all_news(conn)

    tagged = news_df[
        news_df["related_tickers"].notna() & (news_df["related_tickers"] != "")
    ].head(5)

    if tagged.empty:
        print("関連銘柄が判明しているニュースがありません。先に tag_news.py を実行してください。")
        return 1

    for _, row in tagged.iterrows():
        ticker = row["related_tickers"].split(",")[0]
        prices = load_prices(conn, ticker)
        if prices.empty:
            print(f"{ticker}: 価格データがありません（スキップ）")
            continue

        prices["timestamp"] = pd.to_datetime(prices["timestamp"], utc=True)
        published_at = pd.to_datetime(row["published_at"], utc=True)

        print(f"\n--- {row['title']} ({ticker}) ---")
        for r in analyze_price_impact(published_at, prices):
            if r["change_pct"] is None:
                print(f"  {r['horizon']}: {r['note']}")
            else:
                print(f"  {r['horizon']}: {r['change_pct'] * 100:+.2f}%")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
