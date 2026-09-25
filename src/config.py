"""
config/settings.yaml と config/tickers.yaml を読み込むための共通モジュール。

このプロジェクトの他のコードは、設定値が欲しいときは
必ずここを経由して取得します（ファイルパスなどをあちこちに直接書かないため）。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# プロジェクトのルートディレクトリ（このファイルの2つ上）
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def load_settings() -> dict[str, Any]:
    """config/settings.yaml を辞書として読み込む。"""
    path = CONFIG_DIR / "settings.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_tickers() -> list[dict[str, Any]]:
    """
    config/tickers.yaml を読み込み、銘柄のリストを返す。

    戻り値の例:
        [{"symbol": "SPY", "category": "broad_market", "name": "S&P 500 ETF"}, ...]
    """
    path = CONFIG_DIR / "tickers.yaml"
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("tickers", [])


def get_ticker_symbols() -> list[str]:
    """ティッカーシンボルだけのリストを返す（例: ["SPY", "QQQ", ...]）。"""
    return [t["symbol"] for t in load_tickers()]


def get_db_path() -> Path:
    """SQLiteデータベースファイルへの絶対パスを返す。"""
    settings = load_settings()
    relative_path = settings["database"]["path"]
    return PROJECT_ROOT / relative_path


def get_news_sources() -> list[dict[str, Any]]:
    """config/settings.yaml の news.sources を返す（[{"name": ..., "url": ...}, ...]）。"""
    settings = load_settings()
    return settings.get("news", {}).get("sources", [])
