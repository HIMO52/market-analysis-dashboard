"""
株価データを取得して data/raw/ にCSVとして保存するスクリプト。

実行方法:
    python scripts/fetch_market_data.py

一部の銘柄取得が失敗しても、他の銘柄の取得・保存は続行する。
失敗理由は data/raw/errors.log に追記される。
"""

from __future__ import annotations

import sys
from pathlib import Path

# このスクリプトを直接実行したときに src/ を import できるようにする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import PROJECT_ROOT, get_ticker_symbols  # noqa: E402
from src.data_sources.fetcher import fetch_all  # noqa: E402
from src.data_sources.yfinance_source import YFinanceSource  # noqa: E402


def main() -> int:
    symbols = get_ticker_symbols()
    source = YFinanceSource()

    print(f"[fetch_market_data] {len(symbols)}銘柄の取得を開始します（データ取得元: {source.name}）")

    results, errors = fetch_all(source, symbols)

    raw_dir = PROJECT_ROOT / "data" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    for symbol, df in results.items():
        out_path = raw_dir / f"{symbol}.csv"
        df.to_csv(out_path, index=False)
        print(f"{symbol} OK  ({len(df)}行 -> {out_path.relative_to(PROJECT_ROOT)})")

    if errors:
        log_path = raw_dir / "errors.log"
        with open(log_path, "a", encoding="utf-8") as f:
            for symbol, message in errors.items():
                print(f"{symbol} ERROR  {message}")
                f.write(f"{message}\n")

    print(
        f"[fetch_market_data] 完了: 成功 {len(results)}件 / 失敗 {len(errors)}件"
    )

    # 全銘柄が失敗した場合のみ異常終了扱いにする（一部失敗は正常終了）
    return 1 if (errors and not results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
