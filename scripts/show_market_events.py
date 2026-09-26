"""
市場イベントカレンダーを表示するスクリプト。

実行方法:
    python scripts/show_market_events.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import load_market_events  # noqa: E402
from src.events.calendar import split_past_and_upcoming  # noqa: E402


def main() -> int:
    events = load_market_events()
    past, upcoming = split_past_and_upcoming(events)

    print("=== 今後の市場イベント ===")
    if not upcoming:
        print("登録されているイベントはありません。")
    for e in upcoming:
        print(f"{e['start_date']} 〜 {e['end_date']}  {e['name']}")

    print("\n=== 直近の過去イベント ===")
    for e in past[-3:]:
        print(f"{e['start_date']} 〜 {e['end_date']}  {e['name']}")

    print(
        "\n(注: CPI・雇用統計・GDPなどは、信頼できる無料データソースが"
        "確認できていないため、このカレンダーには含まれていません)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
