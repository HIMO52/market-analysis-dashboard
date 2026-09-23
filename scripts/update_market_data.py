"""
株価データを取得し、SQLiteデータベースに保存するメインスクリプト。
（このスクリプトが、後でGitHub Actionsから定期実行されるものになります）

実行方法:
    python scripts/update_market_data.py

処理の流れ:
    1. config/tickers.yaml から銘柄一覧を読み込む
    2. yfinanceで各銘柄の株価を取得（失敗した銘柄があっても続行）
    3. data/db/market.sqlite に保存（重複データは自動的にスキップ）
    4. 結果を SPY OK / TLT ERROR のように表示
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_db_path, get_ticker_symbols  # noqa: E402
from src.data_sources.fetcher import fetch_all  # noqa: E402
from src.data_sources.yfinance_source import YFinanceSource  # noqa: E402
from src.storage.db import get_connection, init_db, save_prices  # noqa: E402


def main() -> int:
    symbols = get_ticker_symbols()
    source = YFinanceSource()

    print(f"[update_market_data] {len(symbols)}銘柄を取得します（データ取得元: {source.name}）")
    results, errors = fetch_all(source, symbols)

    db_path = get_db_path()
    conn = get_connection(db_path)
    init_db(conn)

    total_inserted = 0
    for symbol, df in results.items():
        inserted = save_prices(conn, df)
        total_inserted += inserted
        skipped = len(df) - inserted
        print(f"{symbol} OK  新規{inserted}行 / 重複スキップ{skipped}行")

    for symbol, message in errors.items():
        print(f"{symbol} ERROR  {message}")

    conn.close()

    print(
        f"[update_market_data] 完了: 成功 {len(results)}銘柄 / 失敗 {len(errors)}銘柄 "
        f"/ 新規保存 {total_inserted}行 (保存先: {db_path})"
    )

    return 1 if (errors and not results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
