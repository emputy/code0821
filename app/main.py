import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
DB = BASE_DIR / "data" / "intel.db"

from app.collector.fetch import fetch_all
from app.filter.keywords import load_keywords, filter_items
from app.storage.database import Database


def main():
    parser = argparse.ArgumentParser(description="450MHz / 无线专网情报采集")
    parser.add_argument("--config", default=str(CONFIG), help="数据源配置文件路径")
    parser.add_argument("--db", default=str(DB), help="SQLite 数据库路径")
    parser.add_argument("--no-filter", action="store_true", help="跳过关键词过滤")
    args = parser.parse_args()

    print("== 采集阶段 ==")
    items = fetch_all(args.config)
    print(f"共采集 {len(items)} 条原始内容")

    if not args.no_filter:
        print("== 过滤阶段 ==")
        keywords = load_keywords(args.config)
        items = filter_items(items, keywords)
        print(f"关键词过滤后剩 {len(items)} 条")

    print("== 入库阶段 ==")
    db = Database(args.db)
    added = db.save(items)
    total, by_source = db.summary()
    db.close()
    print(f"新增 {added} 条，数据库共 {total} 条")
    for name, cnt in by_source:
        print(f"  {name}: {cnt}")


if __name__ == "__main__":
    main()
