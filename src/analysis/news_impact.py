"""
ニュース公開後の値動き分析。

【重要な方針】
- このプロジェクトが取得している株価データは「日足（1日単位）」のみ。
  5分・15分・30分・1時間といった分足レベルのデータは取得していない。
- そのため、分足・時間足の分析は「データ不足」として明示し、
  存在しないデータを補間・推測することはしない。
- 唯一計算できるのは「1日」の値動き（ニュース公開日以降、直近の営業日の
  終値が、その前の営業日の終値からどれだけ変化したか）。
"""

from __future__ import annotations

import pandas as pd

# 日足データしか無いため、分足・時間足は常に「データ不足」となるホライズン
INSUFFICIENT_DATA_HORIZONS = ["5分", "15分", "30分", "1時間"]
INSUFFICIENT_DATA_NOTE = "この期間の分析データが不足しています（日足データのみ取得しているため）"

ALL_HORIZONS = INSUFFICIENT_DATA_HORIZONS + ["1日"]


def _daily_change_after(published_at: pd.Timestamp, prices: pd.DataFrame) -> float | None:
    """
    ニュース公開日以降で最初に迎える営業日の終値が、
    その直前の営業日の終値からどれだけ変化したかを計算する。

    Args:
        published_at: ニュースの公開日時（tz-aware推奨）
        prices: "timestamp"（tz-aware）と"close"の列を持つDataFrame（昇順ソート済み）

    Returns:
        変化率（例: 0.02 は+2%）。前後どちらかのデータが無ければNone。
    """
    df = prices.sort_values("timestamp").reset_index(drop=True)
    published_date = pd.Timestamp(published_at).normalize()

    on_or_after = df[df["timestamp"].dt.normalize() >= published_date]
    if on_or_after.empty:
        return None

    reaction_pos = on_or_after.index[0]
    if reaction_pos == 0:
        return None  # 直前の営業日データが無い

    reaction_close = df.loc[reaction_pos, "close"]
    baseline_close = df.loc[reaction_pos - 1, "close"]

    if pd.isna(reaction_close) or pd.isna(baseline_close) or baseline_close == 0:
        return None

    return float(reaction_close / baseline_close - 1)


def analyze_price_impact(published_at: pd.Timestamp, prices: pd.DataFrame) -> list[dict]:
    """
    ニュース公開後の値動きを、複数の時間軸でまとめて分析する。

    Returns:
        [{"horizon": "5分", "change_pct": None, "note": "データ不足の説明"},
         ...,
         {"horizon": "1日", "change_pct": 0.015, "note": None}]
    """
    results = []

    for horizon in INSUFFICIENT_DATA_HORIZONS:
        results.append({"horizon": horizon, "change_pct": None, "note": INSUFFICIENT_DATA_NOTE})

    change = _daily_change_after(published_at, prices)
    if change is None:
        results.append(
            {"horizon": "1日", "change_pct": None, "note": "この期間の分析データが不足しています"}
        )
    else:
        results.append({"horizon": "1日", "change_pct": change, "note": None})

    return results
