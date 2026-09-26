"""ticker_matching.py と importance.py のテスト。"""

from __future__ import annotations

from src.news.importance import classify_importance
from src.news.ticker_matching import find_related_tickers


def _sample_tickers():
    return [
        {"symbol": "XLE", "keywords": ["oil", "energy sector", "opec"]},
        {"symbol": "TLT", "keywords": ["treasury", "interest rate", "fed"]},
        {"symbol": "SMH", "keywords": ["semiconductor", "chipmaker"]},
    ]


def test_find_related_tickers_matches_keyword_case_insensitive():
    text = "OPEC agrees to cut Oil production"
    result = find_related_tickers(text, _sample_tickers())

    tickers = [r["ticker"] for r in result]
    assert "XLE" in tickers
    xle_result = next(r for r in result if r["ticker"] == "XLE")
    assert "oil" in xle_result["matched_keywords"]
    assert "opec" in xle_result["matched_keywords"]


def test_find_related_tickers_no_match_returns_empty_list():
    text = "Local bakery wins award for best bread"
    result = find_related_tickers(text, _sample_tickers())
    assert result == []


def test_find_related_tickers_can_match_multiple_tickers():
    text = "Fed raises interest rate as semiconductor exports slow"
    result = find_related_tickers(text, _sample_tickers())
    tickers = {r["ticker"] for r in result}
    assert tickers == {"TLT", "SMH"}


def test_classify_importance_high_keyword():
    result = classify_importance("FOMC signals possible rate hike next month")
    assert result["level"] == "HIGH"
    assert "fomc" in result["matched_keywords"]


def test_classify_importance_medium_keyword():
    result = classify_importance("Company X reports quarterly earnings above forecast")
    assert result["level"] == "MEDIUM"


def test_classify_importance_low_when_no_keywords_match():
    result = classify_importance("Local team wins championship game")
    assert result["level"] == "LOW"
    assert result["matched_keywords"] == []


def test_classify_importance_high_takes_priority_over_medium():
    # "earnings"(MEDIUM)と"merger"(HIGH)の両方を含む → HIGH優先
    result = classify_importance("Company earnings boosted after merger announcement")
    assert result["level"] == "HIGH"
