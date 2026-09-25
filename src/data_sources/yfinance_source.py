"""
yfinance（無料・APIキー不要）を使った株価データ取得の実装。

列名の正規化ロジック(normalize_yfinance_dataframe)は、
実際のネットワーク通信を伴わない純粋な関数として切り出してあり、
テストしやすくしている。
"""

from __future__ import annotations

import pandas as pd

from .base import REQUIRED_COLUMNS, DataSourceError, PriceDataSource

# yfinanceの列名 → このプロジェクト共通の列名
_COLUMN_RENAME_MAP = {
    "Date": "timestamp",
    "Datetime": "timestamp",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
    "Adj Close": "adjusted_close",
}


def normalize_yfinance_dataframe(raw: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    yfinance の Ticker.history() が返す生のDataFrameを、
    このプロジェクト共通の列名・列順に変換する。

    ネットワーク通信を行わないため、テストではこの関数だけを
    ダミーのDataFrameで検証すればよい。
    """
    if raw is None or raw.empty:
        raise DataSourceError(f"{symbol}: yfinanceからデータが返りませんでした")

    df = raw.reset_index()
    df = df.rename(columns=_COLUMN_RENAME_MAP)

    if "adjusted_close" not in df.columns:
        # auto_adjust=False で取得していれば通常 "Adj Close" が存在するが、
        # 念のためのフォールバック（調整後価格がない銘柄・期間向け）
        df["adjusted_close"] = df["close"]

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise DataSourceError(
            f"{symbol}: yfinanceの応答に想定した列がありません: {missing}"
        )

    df = df[REQUIRED_COLUMNS].copy()

    # closeが無い行（その日の取引がまだ確定していない「未確定行」）は、
    # 存在しないデータとして扱い保存しない。推測で埋めることはしない。
    df = df.dropna(subset=["close"]).reset_index(drop=True)
    if df.empty:
        raise DataSourceError(f"{symbol}: 有効な終値データが1件も取得できませんでした")

    return df


class YFinanceSource(PriceDataSource):
    """yfinanceライブラリを使った株価データ取得。"""

    name = "yfinance"

    def fetch_ohlcv(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        # importをここに置くことで、yfinance未インストールの環境でも
        # このモジュールの他のテスト（normalize_yfinance_dataframeなど）は動く
        import yfinance as yf

        try:
            raw = yf.Ticker(symbol).history(period=period, auto_adjust=False)
        except Exception as e:  # yfinance側の例外はまとめてDataSourceErrorに変換
            raise DataSourceError(f"{symbol}: yfinanceからの取得に失敗しました: {e}") from e

        return normalize_yfinance_dataframe(raw, symbol)
