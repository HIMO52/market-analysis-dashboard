"""
SQLiteデータベースへの株価データ保存処理。

重複データを保存しないよう、(ticker, timestamp, source) の組み合わせに
UNIQUE制約を付け、INSERT OR IGNORE で挿入する。
これにより、同じ取得元・同じ時刻のデータを何度取得し直しても
2重に保存されることはない。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    adjusted_close REAL,
    source TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    UNIQUE(ticker, timestamp, source)
);

CREATE INDEX IF NOT EXISTS idx_prices_ticker_timestamp
    ON prices (ticker, timestamp);

CREATE TABLE IF NOT EXISTS news (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published_at TEXT,
    retrieved_at TEXT NOT NULL,
    source TEXT NOT NULL,
    UNIQUE(url)
);

CREATE INDEX IF NOT EXISTS idx_news_published_at
    ON news (published_at);
"""


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """
    SQLiteデータベースへの接続を作る。
    保存先フォルダが無ければ自動的に作成する。
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    return conn


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    """指定したテーブルに列が無ければ追加する（既存DBへの後方互換マイグレーション）。"""
    existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")


def init_db(conn: sqlite3.Connection) -> None:
    """テーブル・インデックスが無ければ作成する（既にあれば何もしない）。"""
    conn.executescript(SCHEMA)
    # Phase 8/9で追加した列。既に稼働中のDBにも安全に列を追加できるようにする
    _ensure_column(conn, "news", "related_tickers", "TEXT")
    _ensure_column(conn, "news", "importance", "TEXT")
    _ensure_column(conn, "news", "importance_keywords", "TEXT")
    conn.commit()


def save_prices(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    """
    株価データのDataFrameをpricesテーブルに保存する。

    必須列: ticker, timestamp, open, high, low, close, volume,
            adjusted_close, source, retrieved_at

    Returns:
        実際に新しく挿入された行数（重複していてスキップされた行は含まない）
    """
    if df.empty:
        return 0

    required = [
        "ticker", "timestamp", "open", "high", "low", "close",
        "volume", "adjusted_close", "source", "retrieved_at",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"save_pricesに渡されたDataFrameに列がありません: {missing}")

    rows = df[required].copy()
    # timestampはSQLiteに保存する前に文字列化しておく
    rows["timestamp"] = rows["timestamp"].astype(str)
    rows["retrieved_at"] = rows["retrieved_at"].astype(str)

    before = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]

    conn.executemany(
        """
        INSERT OR IGNORE INTO prices
            (ticker, timestamp, open, high, low, close, volume, adjusted_close, source, retrieved_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows.itertuples(index=False, name=None),
    )
    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    return after - before


def get_latest_timestamp(conn: sqlite3.Connection, ticker: str, source: str) -> str | None:
    """
    指定した銘柄・取得元について、既に保存されている最新のtimestampを返す。
    データが無ければNoneを返す。

    将来、この値より新しいデータだけを取得する「差分取得」に使える。
    """
    row = conn.execute(
        "SELECT MAX(timestamp) FROM prices WHERE ticker = ? AND source = ?",
        (ticker, source),
    ).fetchone()
    return row[0] if row else None


def load_prices(conn: sqlite3.Connection, ticker: str) -> pd.DataFrame:
    """指定した銘柄の保存済みデータを、timestamp昇順で取得する。"""
    return pd.read_sql_query(
        "SELECT * FROM prices WHERE ticker = ? ORDER BY timestamp ASC",
        conn,
        params=(ticker,),
    )


def save_news(conn: sqlite3.Connection, articles: list[dict]) -> int:
    """
    ニュース記事のリストをnewsテーブルに保存する。

    URL(url列)にUNIQUE制約があるため、同じ記事を何度取得しても
    重複して保存されることはない。

    Args:
        articles: [{"title":..., "url":..., "published_at":..., "source":..., "retrieved_at":...}, ...]

    Returns:
        新しく挿入された行数（重複でスキップされた件数は含まない）
    """
    if not articles:
        return 0

    before = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]

    conn.executemany(
        """
        INSERT OR IGNORE INTO news (title, url, published_at, retrieved_at, source)
        VALUES (:title, :url, :published_at, :retrieved_at, :source)
        """,
        articles,
    )
    conn.commit()

    after = conn.execute("SELECT COUNT(*) FROM news").fetchone()[0]
    return after - before


def load_news(conn: sqlite3.Connection, limit: int = 50) -> pd.DataFrame:
    """最新のニュースを、公開日時が新しい順に取得する。"""
    return pd.read_sql_query(
        "SELECT * FROM news ORDER BY published_at DESC LIMIT ?",
        conn,
        params=(limit,),
    )


def load_all_news(conn: sqlite3.Connection) -> pd.DataFrame:
    """保存済みの全ニュースを取得する（Phase 8/9のタグ付け処理などで使用）。"""
    return pd.read_sql_query("SELECT * FROM news ORDER BY published_at DESC", conn)


def update_news_tags(conn: sqlite3.Connection, updates: list[dict]) -> int:
    """
    ニュース記事の関連銘柄・重要度をまとめて更新する。

    Args:
        updates: [{"url": ..., "related_tickers": "XLE,USO",
                    "importance": "HIGH", "importance_keywords": "oil,opec"}, ...]

    Returns:
        更新件数
    """
    if not updates:
        return 0

    conn.executemany(
        """
        UPDATE news
        SET related_tickers = :related_tickers,
            importance = :importance,
            importance_keywords = :importance_keywords
        WHERE url = :url
        """,
        updates,
    )
    conn.commit()
    return len(updates)
