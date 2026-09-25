"""
RSS（無料・APIキー不要）からニュース記事を取得する処理。

【方針】
- feedparserライブラリで解析した結果(entries)を、このプロジェクト共通の
  記事辞書の形に変換するロジック(parse_entries)は、ネットワーク通信を
  行わない純粋な関数として切り出してあり、テストしやすくしている。
- タイトルまたはURLが無い記事は「不完全なデータ」として除外する
  （存在しないデータを推測して埋めない）。
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any


def _parse_published_at(entry: dict[str, Any]) -> str | None:
    """
    エントリの公開日時を取得する。
    feedparserは "published_parsed"（time.struct_time）としてパース済みの
    日時を提供してくれることが多いので、それをUTCのISO8601文字列に変換する。
    取得できない場合はNone（「不明」として扱い、推測はしない）。
    """
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct_time:
        return None
    return datetime.fromtimestamp(time.mktime(struct_time), tz=timezone.utc).isoformat()


def entry_to_article(entry: dict[str, Any], source_name: str) -> dict[str, Any]:
    """1件のRSSエントリを、このプロジェクト共通の記事辞書に変換する。"""
    return {
        "title": (entry.get("title") or "").strip(),
        "url": (entry.get("link") or "").strip(),
        "published_at": _parse_published_at(entry),
        "source": source_name,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
    }


def parse_entries(entries: list[dict[str, Any]], source_name: str) -> list[dict[str, Any]]:
    """
    feedparserのentriesリストを、このプロジェクト共通の記事辞書のリストに変換する。
    タイトルまたはURLが空の記事は除外する。
    """
    articles = []
    for entry in entries:
        article = entry_to_article(entry, source_name)
        if article["title"] and article["url"]:
            articles.append(article)
    return articles


def fetch_rss_articles(url: str, source_name: str) -> list[dict[str, Any]]:
    """
    指定したRSSフィードURLから記事一覧を取得する（実際にネットワーク通信を行う）。
    パース結果の変換ロジックは parse_entries() に委譲している。
    """
    import feedparser  # 遅延import。ユニットテストではparse_entries()の方を直接使う

    parsed = feedparser.parse(url)
    return parse_entries(parsed.entries, source_name)
