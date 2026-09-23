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


def init_db(conn: sqlite3.Connection) -> None:
    """テーブル・インデックスが無ければ作成する（既にあれば何もしない）。"""
    conn.executescript(SCHEMA)
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
