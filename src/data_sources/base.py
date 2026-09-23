"""
株価データ取得元の共通インターフェース。

新しいデータ取得元（yfinance以外）を追加したくなった場合は、
このPriceDataSourceを継承して fetch_ohlcv() を実装するだけで
他のコードを変更せずに差し替えられるようにする（交換可能な構造）。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

# どのデータ取得元を使っても、最終的にこの列名・順序に揃える
REQUIRED_COLUMNS = [
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "adjusted_close",
]


class DataSourceError(Exception):
    """データ取得元で問題が起きたときに送出する例外。

    取得できなかったデータを推測や補完で埋めることはせず、
    必ずこの例外を送出して「取得できなかった」ことを明示する。
    """


class PriceDataSource(ABC):
    """株価データを取得するための共通インターフェース。"""

    name: str = "unknown"

    @abstractmethod
    def fetch_ohlcv(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        """
        指定した銘柄のOHLCVデータを取得する。

        Args:
            symbol: ティッカーシンボル（例: "SPY"）
            period: 取得期間（yfinance形式。例: "2y", "1y", "6mo"）

        Returns:
            REQUIRED_COLUMNS の列を持つDataFrame。

        Raises:
            DataSourceError: 取得に失敗した場合。データを推測して埋めない。
        """
        raise NotImplementedError
