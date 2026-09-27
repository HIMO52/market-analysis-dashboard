"""
config/settings.yaml に設定したRSSフィードからニュースを取得し、
SQLiteに保存するスクリプト。

実行方法:
    python scripts/fetch_news.py

一部のフィード取得に失敗しても、他のフィードの取得は続行する。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PROJECT_ROOT, get_db_path, get_news_sources  # noqa: E402
from src.news.rss_source import fetch_rss_articles  # noqa: E402
from src.storage.db import get_connection, init_db, save_news  # noqa: E402


def _write_status(source_statuses: dict) -> None:
    status = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "sources": source_statuses,
    }
    status_dir = PROJECT_ROOT / "data" / "status"
    status_dir.mkdir(parents=True, exist_ok=True)
    with open(status_dir / "news_status.json", "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def main() -> int:
    sources = get_news_sources()
    if not sources:
        print("config/settings.yaml の news.sources が空です。取得するフィードがありません。")
        return 1

    conn = get_connection(get_db_path())
    init_db(conn)

    total_inserted = 0
    error_count = 0
    source_statuses = {}

    for src in sources:
        name = src["name"]
        url = src["url"]
        try:
            articles = fetch_rss_articles(url, name)
            inserted = save_news(conn, articles)
            total_inserted += inserted
            skipped = len(articles) - inserted
            print(f"{name} OK  取得{len(articles)}件 / 新規{inserted}件 / 重複スキップ{skipped}件")
            source_statuses[name] = "OK"
        except Exception as e:  # フィードごとの失敗で全体を止めない
            error_count += 1
            print(f"{name} ERROR  {e}")
            source_statuses[name] = f"ERROR: {e}"

    conn.close()
    _write_status(source_statuses)
    print(f"[fetch_news] 完了: 新規保存 {total_inserted}件 / 失敗 {error_count}フィード")

    return 1 if (error_count and error_count == len(sources)) else 0


if __name__ == "__main__":
    raise SystemExit(main())
