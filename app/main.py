import argparse
from pathlib import Path

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
