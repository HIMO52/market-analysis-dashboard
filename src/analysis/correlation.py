"""
相関分析の計算ロジック。

【方針】
- 単純な価格同士の相関ではなく、日次リターン同士のPearson相関係数を使う
  （価格はトレンドを持つため、そのまま相関を取ると見かけ上の相関になりやすい）。
- 複数銘柄・複数期間の組み合わせをまとめて計算する。
"""

from __future__ import annotations

import itertools

import pandas as pd


def compute_daily_returns(price_by_ticker: dict[str, pd.Series]) -> pd.DataFrame:
    """
    {ticker: 価格Series(timestampをindexに持つ)} の辞書から、
    日次リターンの一枚のDataFrame（列=ticker、行=日付）を作る。

    日付が揃っていない銘柄同士は、共通する日付だけが使われる
    （pandasのDataFrame結合時に自動的に揃えられる）。
    """
    price_df = pd.DataFrame(price_by_ticker)
    return price_df.pct_change().dropna(how="all")


def correlation_for_window(daily_returns: pd.DataFrame, window_days: int) -> pd.DataFrame:
    """
    直近window_days日分の日次リターンを使って、銘柄間のPearson相関係数行列を計算する。

    Returns:
        銘柄×銘柄の相関係数行列（DataFrame）。データが足りない場合はNaNを含む。
    """
    recent = daily_returns.tail(window_days)
    return recent.corr(method="pearson", min_periods=max(2, window_days // 2))


def correlation_matrix_multi_window(
    daily_returns: pd.DataFrame,
    windows: dict[str, int],
) -> dict[str, pd.DataFrame]:
    """
    複数期間分の相関係数行列をまとめて計算する。

    Args:
        windows: {"1M": 21, "3M": 63, ...} のような期間の辞書

    Returns:
        {"1M": <相関行列>, "3M": <相関行列>, ...}
    """
    return {label: correlation_for_window(daily_returns, days) for label, days in windows.items()}


def pairwise_correlation_table(
    matrices: dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    複数期間の相関行列を、銘柄ペアごとの一覧表（縦持ち）にまとめる。

    戻り値の列: ticker_a, ticker_b, <期間ラベル>...
    例: SPY, TLT, 1M列, 3M列, 6M列, 1Y列, 3Y列
    """
    if not matrices:
        return pd.DataFrame(columns=["ticker_a", "ticker_b"])

    tickers = sorted(next(iter(matrices.values())).columns)
    pairs = list(itertools.combinations(tickers, 2))

    rows = []
    for ticker_a, ticker_b in pairs:
        row = {"ticker_a": ticker_a, "ticker_b": ticker_b}
        for label, matrix in matrices.items():
            value = matrix.loc[ticker_a, ticker_b] if (ticker_a in matrix.index and ticker_b in matrix.columns) else None
            row[label] = value
        rows.append(row)

    return pd.DataFrame(rows)


def find_inverse_correlation_candidates(
    pair_table: pd.DataFrame,
    threshold: float,
    reference_column: str = "1Y",
) -> pd.DataFrame:
    """
    相関係数が threshold 以下（強い逆相関）のペアを抽出する。

    Args:
        pair_table: pairwise_correlation_table() の出力
        threshold: この値以下を逆相関候補とする（例: -0.50）。設定ファイルから渡す。
        reference_column: どの期間の相関係数を基準に抽出するか（デフォルトは1年）

    Returns:
        条件を満たす行だけを抽出したDataFrame。相関係数が低い（より逆相関が強い）順に並べる。
    """
    if reference_column not in pair_table.columns:
        raise ValueError(f"reference_column '{reference_column}' が pair_table に存在しません")

    candidates = pair_table[pair_table[reference_column] <= threshold].copy()
    return candidates.sort_values(reference_column, ascending=True).reset_index(drop=True)


def classify_inverse_correlation_stability(
    row: pd.Series,
    window_labels: list[str],
    threshold: float,
) -> str:
    """
    ある銘柄ペアについて、逆相関が「安定的」か「最近だけ」かを分類する。

    判定ロジック（シンプルなルールベース、断定的な投資判断は行わない）:
        - すべての期間で threshold 以下 → "全期間で安定した逆相関"
        - 短期（最初のラベル）だけ threshold 以下 → "直近のみの逆相関"
        - 長期（最後のラベル）だけ threshold 以下 → "長期のみの逆相関（直近は弱まっている）"
        - それ以外 → "一部の期間のみ逆相関"
    """
    values = [row.get(label) for label in window_labels]
    is_inverse = [v is not None and pd.notna(v) and v <= threshold for v in values]

    if all(is_inverse):
        return "全期間で安定した逆相関"
    if is_inverse[0] and not any(is_inverse[1:]):
        return "直近のみの逆相関"
    if is_inverse[-1] and not any(is_inverse[:-1]):
        return "長期のみの逆相関（直近は弱まっている）"
    return "一部の期間のみ逆相関"
