"""
【1回だけ実行するメンテナンス用スクリプト】

過去のバグにより保存されてしまった「終値(close)が空の行」を
データベースから削除する。

実行方法:
    python scripts/clean_null_rows.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import get_db_path  # noqa: E402
from src.storage.db import get_connection  # noqa: E402


def main() -> int:
    conn = get_connection(get_db_path())
    before = conn.execute("SELECT COUNT(*) FROM prices WHERE close IS NULL").fetchone()[0]

    if before == 0:
        print("終値が空の行はありませんでした。何もする必要はありません。")
        return 0

    conn.execute("DELETE FROM prices WHERE close IS NULL")
    conn.commit()
    conn.close()

    print(f"終値が空だった {before} 行を削除しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
