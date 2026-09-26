"""
保存済みニュース記事に、関連銘柄（Phase 8）と重要度（Phase 9）を
タグ付けするスクリプト。ルールベースのみで動作し、AI APIは使わない。

実行方法:
    python scripts/tag_news.py

すべてのニュースに対して毎回再計算する（ルールが決定的なので、
何度実行しても同じ結果になる＝再実行しても安全）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_tickers  # noqa: E402
from src.config import get_db_path  # noqa: E402
from src.news.importance import classify_importance  # noqa: E402
from src.news.ticker_matching import find_related_tickers  # noqa: E402
from src.storage.db import get_connection, init_db, load_all_news, update_news_tags  # noqa: E402


def main() -> int:
    conn = get_connection(get_db_path())
    init_db(conn)

    tickers = load_tickers()
    news_df = load_all_news(conn)

    if news_df.empty:
        print("タグ付けするニュースがありません。先に fetch_news.py を実行してください。")
        return 1

    updates = []
    importance_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}

    for _, row in news_df.iterrows():
        title = row["title"]

        related = find_related_tickers(title, tickers)
        related_tickers_str = ",".join(r["ticker"] for r in related)

        importance = classify_importance(title)
        importance_counts[importance["level"]] += 1

        updates.append(
            {
                "url": row["url"],
                "related_tickers": related_tickers_str,
                "importance": importance["level"],
                "importance_keywords": ",".join(importance["matched_keywords"]),
            }
        )

    updated = update_news_tags(conn, updates)
    conn.close()

    print(f"[tag_news] {updated}件のニュースにタグ付けしました。")
    print(
        f"重要度の内訳: HIGH {importance_counts['HIGH']}件 / "
        f"MEDIUM {importance_counts['MEDIUM']}件 / LOW {importance_counts['LOW']}件"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
