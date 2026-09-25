"""config.py が設定ファイルを正しく読み込めるかを確認するテスト。"""

from src.config import get_db_path, get_news_sources, get_ticker_symbols, load_settings, load_tickers


def test_load_settings_returns_dict():
    settings = load_settings()
    assert isinstance(settings, dict)
    assert "database" in settings
    assert "analysis" in settings


def test_inverse_correlation_threshold_is_negative():
    settings = load_settings()
    threshold = settings["analysis"]["inverse_correlation_threshold"]
    assert threshold < 0


def test_load_tickers_returns_expected_symbols():
    tickers = load_tickers()
    assert isinstance(tickers, list)
    assert len(tickers) == 20

    symbols = get_ticker_symbols()
    assert "SPY" in symbols
    assert "TLT" in symbols
    assert "SMH" in symbols


def test_each_ticker_has_required_fields():
    for ticker in load_tickers():
        assert "symbol" in ticker
        assert "category" in ticker
        assert "name" in ticker


def test_get_db_path_is_under_data_db():
    path = get_db_path()
    assert "data" in path.parts
    assert "db" in path.parts
    assert path.name == "market.sqlite"


def test_get_news_sources_returns_list_with_name_and_url():
    sources = get_news_sources()
    assert isinstance(sources, list)
    assert len(sources) >= 1
    for src in sources:
        assert "name" in src
        assert "url" in src
