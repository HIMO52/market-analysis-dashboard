"""storage/db.py のテスト。インメモリSQLite（:memory:）を使い、ネットワーク不要。"""

from __future__ import annotations

import pandas as pd

from src.storage.db import (
    get_connection,
    get_latest_timestamp,
    init_db,
    load_all_news,
    load_news,
    load_prices,
    save_news,
    save_prices,
    update_news_tags,
)


def _sample_df(ticker="SPY", n=2, source="dummy"):
    return pd.DataFrame(
        {
            "ticker": [ticker] * n,
            "timestamp": [f"2026-01-0{i+1}" for i in range(n)],
            "open": [100.0 + i for i in range(n)],
            "high": [101.0 + i for i in range(n)],
            "low": [99.0 + i for i in range(n)],
            "close": [100.5 + i for i in range(n)],
            "volume": [1000 + i for i in range(n)],
            "adjusted_close": [100.5 + i for i in range(n)],
            "source": [source] * n,
            "retrieved_at": ["2026-01-10T00:00:00+00:00"] * n,
        }
    )


def _fresh_conn():
    conn = get_connection(":memory:")
    init_db(conn)
    return conn


def test_init_db_creates_table():
    conn = _fresh_conn()
    # エラーが出なければテーブルが存在する
    conn.execute("SELECT COUNT(*) FROM prices").fetchone()


def test_save_prices_inserts_rows():
    conn = _fresh_conn()
    inserted = save_prices(conn, _sample_df())
    assert inserted == 2

    df = load_prices(conn, "SPY")
    assert len(df) == 2


def test_save_prices_does_not_duplicate():
    conn = _fresh_conn()
    df = _sample_df()

    first = save_prices(conn, df)
    second = save_prices(conn, df)  # 同じデータをもう一度保存

    assert first == 2
    assert second == 0  # 重複は挿入されない

    total = load_prices(conn, "SPY")
    assert len(total) == 2  # 4件にはならない


def test_save_prices_different_source_is_not_duplicate():
    conn = _fresh_conn()
    save_prices(conn, _sample_df(source="yfinance"))
    inserted = save_prices(conn, _sample_df(source="other_source"))

    # 取得元が違えば別データとして保存される（UNIQUE制約はsource込みのため）
    assert inserted == 2


def test_get_latest_timestamp_returns_max():
    conn = _fresh_conn()
    save_prices(conn, _sample_df(n=3))
    latest = get_latest_timestamp(conn, "SPY", "dummy")
    assert latest == "2026-01-03"


def test_get_latest_timestamp_none_when_no_data():
    conn = _fresh_conn()
    assert get_latest_timestamp(conn, "SPY", "dummy") is None


def test_save_prices_multiple_tickers_are_independent():
    conn = _fresh_conn()
    save_prices(conn, _sample_df(ticker="SPY"))
    save_prices(conn, _sample_df(ticker="QQQ"))

    assert len(load_prices(conn, "SPY")) == 2
    assert len(load_prices(conn, "QQQ")) == 2


def _sample_articles():
    return [
        {
            "title": "記事A",
            "url": "https://example.com/a",
            "published_at": "2026-01-15T09:00:00+00:00",
            "retrieved_at": "2026-01-15T10:00:00+00:00",
            "source": "テスト情報源",
        },
        {
            "title": "記事B",
            "url": "https://example.com/b",
            "published_at": "2026-01-16T09:00:00+00:00",
            "retrieved_at": "2026-01-16T10:00:00+00:00",
            "source": "テスト情報源",
        },
    ]


def test_save_news_inserts_articles():
    conn = _fresh_conn()
    inserted = save_news(conn, _sample_articles())
    assert inserted == 2
    assert len(load_news(conn)) == 2


def test_save_news_does_not_duplicate_by_url():
    conn = _fresh_conn()
    articles = _sample_articles()
    first = save_news(conn, articles)
    second = save_news(conn, articles)  # 同じ記事をもう一度保存

    assert first == 2
    assert second == 0
    assert len(load_news(conn)) == 2


def test_load_news_orders_by_published_at_desc():
    conn = _fresh_conn()
    save_news(conn, _sample_articles())
    news_df = load_news(conn)
    assert news_df.iloc[0]["title"] == "記事B"  # 新しい記事が先頭


def test_update_news_tags_sets_related_tickers_and_importance():
    conn = _fresh_conn()
    save_news(conn, _sample_articles())

    updates = [
        {
            "url": "https://example.com/a",
            "related_tickers": "XLE,USO",
            "importance": "HIGH",
            "importance_keywords": "oil,opec",
        },
        {
            "url": "https://example.com/b",
            "related_tickers": "",
            "importance": "LOW",
            "importance_keywords": "",
        },
    ]
    updated = update_news_tags(conn, updates)
    assert updated == 2

    all_news = load_all_news(conn)
    row_a = all_news[all_news["url"] == "https://example.com/a"].iloc[0]
    assert row_a["related_tickers"] == "XLE,USO"
    assert row_a["importance"] == "HIGH"
