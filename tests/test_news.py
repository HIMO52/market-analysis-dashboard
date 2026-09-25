"""
news/rss_source.py のテスト。

feedparser自体はネットワーク通信を伴うため、ここではparse_entries()に
「feedparserのentriesを模したただのdict」を渡してテストする。
"""

from __future__ import annotations

import time

from src.news.rss_source import entry_to_article, parse_entries


def _fake_entry(title="サンプルニュース", link="https://example.com/news/1", published=True):
    entry = {"title": title, "link": link}
    if published:
        # 2026-01-15 09:00:00 UTC を模したstruct_time
        entry["published_parsed"] = time.struct_time((2026, 1, 15, 9, 0, 0, 0, 0, 0))
    return entry


def test_entry_to_article_extracts_title_and_url():
    article = entry_to_article(_fake_entry(), "テスト情報源")
    assert article["title"] == "サンプルニュース"
    assert article["url"] == "https://example.com/news/1"
    assert article["source"] == "テスト情報源"
    assert article["published_at"] is not None
    assert "retrieved_at" in article


def test_entry_to_article_no_published_date_returns_none():
    article = entry_to_article(_fake_entry(published=False), "テスト情報源")
    assert article["published_at"] is None


def test_parse_entries_filters_out_missing_title_or_url():
    entries = [
        _fake_entry(title="正常な記事", link="https://example.com/1"),
        _fake_entry(title="", link="https://example.com/2"),  # タイトル無し→除外
        _fake_entry(title="URLが無い記事", link=""),  # URL無し→除外
    ]
    articles = parse_entries(entries, "テスト情報源")

    assert len(articles) == 1
    assert articles[0]["title"] == "正常な記事"


def test_parse_entries_strips_whitespace():
    entries = [_fake_entry(title="  空白付きタイトル  ", link="  https://example.com/x  ")]
    articles = parse_entries(entries, "テスト情報源")
    assert articles[0]["title"] == "空白付きタイトル"
    assert articles[0]["url"] == "https://example.com/x"
