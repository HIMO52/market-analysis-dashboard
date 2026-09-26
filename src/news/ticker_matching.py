"""
ニュース記事と銘柄の関連付け（キーワードベース）。

【重要な方針】
- 「記事タイトルに企業名・関連キーワードが含まれる」ことと、
  「その銘柄の株価に必ず影響する」ことはイコールではない。
  このモジュールは「関連する可能性がある」候補を、根拠(マッチしたキーワード)
  付きで示すだけであり、断定はしない。
- AI APIは使わず、単純なキーワード一致（大文字小文字を区別しない）で判定する。
"""

from __future__ import annotations


def find_related_tickers(
    text: str,
    tickers: list[dict],
) -> list[dict]:
    """
    記事のタイトル(または本文)に含まれるキーワードから、
    関連する可能性のある銘柄を推定する。

    Args:
        text: 記事のタイトルなど、判定対象のテキスト
        tickers: config.load_tickers() が返す銘柄リスト
                 （各要素に "symbol" と "keywords" を含む）

    Returns:
        [{"ticker": "XLE", "matched_keywords": ["oil", "opec"]}, ...]
        マッチしたキーワードが無い銘柄は結果に含まれない（関連付けの根拠が
        無いものを「関連あり」として出さないため）。
    """
    text_lower = (text or "").lower()
    results = []

    for ticker_info in tickers:
        keywords = ticker_info.get("keywords", [])
        matched = [kw for kw in keywords if kw.lower() in text_lower]
        if matched:
            results.append({"ticker": ticker_info["symbol"], "matched_keywords": matched})

    return results
