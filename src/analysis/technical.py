"""
テクニカル分析の計算ロジック。

【方針】
- すべて調整後終値(adjusted_close)を基準に計算する（配当・分割の影響を除いた
  価格変動を見るため）。
- どの関数も「価格の時系列(pandas Series, 日付昇順)」を受け取り、
  同じ長さの時系列を返す（＝ある日の値を計算するのに、未来のデータを
  使わない = look-ahead biasを避ける）。
- 計算式はすべてこのファイル内にコメントで明記する。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 1年 ≒ 252営業日（米国株式市場の一般的な近似値）
TRADING_DAYS_PER_YEAR = 252


def sma(prices: pd.Series, window: int) -> pd.Series:
    """
    単純移動平均 (Simple Moving Average)。
    計算式: 直近window日分の価格の単純平均。
    """
    return prices.rolling(window=window, min_periods=window).mean()


def ema(prices: pd.Series, window: int) -> pd.Series:
    """
    指数移動平均 (Exponential Moving Average)。
    直近の価格ほど大きい重みを持つ移動平均。pandasの標準的なEMA定義(span方式)を使う。
    """
    return prices.ewm(span=window, adjust=False, min_periods=window).mean()


def period_return(prices: pd.Series, window_days: int) -> pd.Series:
    """
    期間リターン。
    計算式: (当日の価格 / window_days営業日前の価格) - 1
    """
    return prices.pct_change(periods=window_days)


def rolling_volatility(prices: pd.Series, window_days: int, annualize: bool = True) -> pd.Series:
    """
    ボラティリティ（価格変動の大きさ）。
    計算式:
        1. 日次リターン = 当日価格 / 前日価格 - 1
        2. 直近window_days日分の日次リターンの標準偏差を計算
        3. annualize=True の場合、sqrt(252) を掛けて年率換算する
    """
    daily_returns = prices.pct_change()
    vol = daily_returns.rolling(window=window_days, min_periods=window_days).std()
    if annualize:
        vol = vol * np.sqrt(TRADING_DAYS_PER_YEAR)
    return vol


def rolling_52week_high_low(prices: pd.Series) -> tuple[pd.Series, pd.Series]:
    """
    52週（≒252営業日）の高値・安値。
    その日までの直近252営業日（データが252日に満たない期間はそれまでの全期間）
    の最大値・最小値を返す。
    """
    window = TRADING_DAYS_PER_YEAR
    high = prices.rolling(window=window, min_periods=1).max()
    low = prices.rolling(window=window, min_periods=1).min()
    return high, low


def pct_from_52week_high(prices: pd.Series, high_52w: pd.Series) -> pd.Series:
    """
    52週高値からの下落率。
    計算式: (当日価格 / 52週高値) - 1　※通常0以下の値（高値なら0%）
    """
    return prices / high_52w - 1


def pct_from_52week_low(prices: pd.Series, low_52w: pd.Series) -> pd.Series:
    """
    52週安値からの上昇率。
    計算式: (当日価格 / 52週安値) - 1　※通常0以上の値（安値なら0%）
    """
    return prices / low_52w - 1


def max_drawdown(prices: pd.Series) -> float:
    """
    最大ドローダウン（データ全期間における、過去最高値からの最大下落率）。
    計算式:
        1. その日までの累積最高値(cummax)を求める
        2. 各日の下落率 = 価格 / 累積最高値 - 1 （0以下の値）
        3. その中で最も小さい（＝最も大きく下落した）値を返す
    戻り値は負の値（例: -0.25 は最大35%ではなく25%の下落）。データが無ければNaN。
    """
    if prices.empty:
        return float("nan")
    cumulative_max = prices.cummax()
    drawdown = prices / cumulative_max - 1
    return float(drawdown.min())


def rolling_max_drawdown(prices: pd.Series) -> pd.Series:
    """各時点までの最大ドローダウンの時系列版（チャート表示用）。"""
    cumulative_max = prices.cummax()
    drawdown = prices / cumulative_max - 1
    return drawdown.cummin()


def add_technical_indicators(
    df: pd.DataFrame,
    price_col: str = "adjusted_close",
    return_windows: dict[str, int] | None = None,
    volatility_windows: dict[str, int] | None = None,
) -> pd.DataFrame:
    """
    1銘柄分の価格DataFrame（timestamp昇順）に、テクニカル指標の列をまとめて追加する。

    Args:
        df: "timestamp"と price_col の列を持つDataFrame（timestamp昇順であること）
        price_col: 計算に使う価格列名（デフォルトは調整後終値）
        return_windows: {"1D": 1, "5D": 5, ...} のような、リターン計算する期間の辞書
        volatility_windows: {"20D": 20, "60D": 60} のような、ボラティリティ計算する期間の辞書

    Returns:
        元のDataFrameに以下の列を追加したコピー:
            sma_20, sma_50, sma_200, ema_20, ema_50,
            return_<label>（return_windowsのラベルごと）,
            volatility_<label>（volatility_windowsのラベルごと）,
            high_52w, low_52w, pct_from_52w_high, pct_from_52w_low,
            drawdown（各時点までの最大ドローダウン）
    """
    return_windows = return_windows or {"1D": 1, "5D": 5, "20D": 20, "60D": 60, "1Y": 252}
    volatility_windows = volatility_windows or {"20D": 20, "60D": 60}

    out = df.sort_values("timestamp").reset_index(drop=True).copy()
    prices = out[price_col]

    out["sma_20"] = sma(prices, 20)
    out["sma_50"] = sma(prices, 50)
    out["sma_200"] = sma(prices, 200)
    out["ema_20"] = ema(prices, 20)
    out["ema_50"] = ema(prices, 50)

    for label, window_days in return_windows.items():
        out[f"return_{label}"] = period_return(prices, window_days)

    for label, window_days in volatility_windows.items():
        out[f"volatility_{label}"] = rolling_volatility(prices, window_days)

    high_52w, low_52w = rolling_52week_high_low(prices)
    out["high_52w"] = high_52w
    out["low_52w"] = low_52w
    out["pct_from_52w_high"] = pct_from_52week_high(prices, high_52w)
    out["pct_from_52w_low"] = pct_from_52week_low(prices, low_52w)

    out["drawdown"] = rolling_max_drawdown(prices)

    return out
