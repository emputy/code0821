import argparse
import sys
from pathlib import Path

# 控制台用 UTF-8 输出，避免源名含特殊字符（如 ÚREK）触发 GBK 编码崩溃
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
DB = BASE_DIR / "data" / "intel.db"

from app.collector.fetch import fetch_all
from app.storage.database import Database


def main():
    parser = argparse.ArgumentParser(description="450MHz / 无线专网情报采集（存全部原始数据）")
    parser.add_argument("--config", default=str(CONFIG), help="数据源配置文件路径")
    parser.add_argument("--db", default=str(DB), help="SQLite 数据库路径")
    args = parser.parse_args()

    print("== 采集阶段 ==")
    items = fetch_all(args.config)
    print(f"共采集 {len(items)} 条原始内容")

    print("== 入库阶段（存全部，界面查看时按关键词实时过滤）==")
    db = Database(args.db)
    added = db.save(items)
    total, by_source = db.summary()
    db.close()
    print(f"新增 {added} 条，数据库共 {total} 条")
    for name, cnt in by_source:
        print(f"  {name}: {cnt}")


if __name__ == "__main__":
    main()
