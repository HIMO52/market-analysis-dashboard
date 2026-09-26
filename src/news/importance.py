"""
ニュースの重要度分類（LOW / MEDIUM / HIGH）。

【重要な方針】
- ルールベースのキーワードマッチのみで判定する。AI APIは一切使わない
  （AI APIが無くても基本機能が動くようにする、という要件のため）。
- 分類ルールはすべてこのファイル内に明示する。
- 「買い」「売り」の判断は一切行わない。あくまで「話題としての重要度の目安」。
"""

from __future__ import annotations

# HIGH: 金融政策・マクロ経済指標・企業の存続に関わるような、
#       市場全体に影響しうる可能性がある重要イベント
HIGH_KEYWORDS = [
    "fomc", "federal reserve", "fed chair", "rate hike", "rate cut",
    "interest rate decision", "cpi", "consumer price index", "inflation report",
    "nonfarm payrolls", "jobs report", "unemployment rate", "gdp report",
    "recession", "bankruptcy", "merger", "acquisition", "buyout", "m&a",
    "earnings beat", "earnings miss", "profit warning", "guidance cut",
    "sec charges", "antitrust", "government shutdown", "credit downgrade",
    "credit rating downgrade",
]

# MEDIUM: 決算・業績見通し・規制・契約など、個別銘柄や業界に影響しうる話題
MEDIUM_KEYWORDS = [
    "earnings", "quarterly results", "guidance", "forecast", "outlook",
    "interest rate", "rate decision", "regulation", "regulator", "lawsuit",
    "contract", "deal", "partnership", "upgrade", "downgrade", "ipo",
    "stock split", "dividend", "layoffs", "job cuts",
]


def classify_importance(text: str) -> dict:
    """
    ニュースのタイトル（または本文）から重要度を分類する。

    判定ロジック:
        1. HIGH_KEYWORDS のいずれかを含む → "HIGH"
        2. 含まなければ、MEDIUM_KEYWORDS のいずれかを含む → "MEDIUM"
        3. どちらも含まなければ → "LOW"

    Returns:
        {"level": "HIGH" | "MEDIUM" | "LOW", "matched_keywords": [...]}
    """
    text_lower = (text or "").lower()

    matched_high = [kw for kw in HIGH_KEYWORDS if kw in text_lower]
    if matched_high:
        return {"level": "HIGH", "matched_keywords": matched_high}

    matched_medium = [kw for kw in MEDIUM_KEYWORDS if kw in text_lower]
    if matched_medium:
        return {"level": "MEDIUM", "matched_keywords": matched_medium}

    return {"level": "LOW", "matched_keywords": []}
