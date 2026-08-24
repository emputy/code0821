import argparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
CUSTOMERS = BASE_DIR / "config" / "customers.json"
DB = BASE_DIR / "data" / "intel.db"

from app.collector.fetch import fetch_all, load_sources
from app.filter.entities import build_entity_matcher, build_entity_terms, load_customers
from app.filter.keywords import filter_items, load_keywords
from app.storage.database import Database


def build_source_keywords(config_path):
    """按来源读取 extra_keywords（用于友商等放宽过滤）。"""
    out = {}
    for s in load_sources(config_path):
        extras = (s.options or {}).get("extra_keywords", [])
        if extras:
            out[s.id] = extras
    return out


def main():
    parser = argparse.ArgumentParser(description="450MHz / 无线专网情报采集")
    parser.add_argument("--config", default=str(CONFIG), help="数据源配置文件路径")
    parser.add_argument("--customers", default=str(CUSTOMERS), help="重点客户清单路径")
    parser.add_argument("--db", default=str(DB), help="SQLite 数据库路径")
    parser.add_argument("--no-filter", action="store_true", help="跳过过滤")
    args = parser.parse_args()

    print("== 采集阶段 ==")
    items = fetch_all(args.config)
    print(f"共采集 {len(items)} 条原始内容")

    if not args.no_filter:
        print("== 过滤阶段 ==")
        keywords = load_keywords(args.config)
        customers = load_customers(args.customers)
        entity_terms = build_entity_terms(customers)
        entity_re = build_entity_matcher(entity_terms)
        src_kw = build_source_keywords(args.config)
        items = filter_items(items, keywords, entity_re, src_kw)
        print(f"领域关键词 {len(keywords)} 个 + 跟踪客户/国家 {len(entity_terms)} 个 + 来源级关键词 {sum(len(v) for v in src_kw.values())} 个")
        print(f"过滤后剩 {len(items)} 条")

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
