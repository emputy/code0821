import json
import re


def load_customers(config_path: str) -> list[dict]:
    """读取客户清单，返回展平的客户列表（每条带 stage/region/country/utility）。"""
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    customers = []
    for stage in data.get("stages", []):
        for c in stage.get("customers", []):
            customers.append({
                "stage": stage.get("stage"),
                "stage_name": stage.get("name", ""),
                "region": c.get("region", ""),
                "country": c.get("country", ""),
                "country_en": c.get("country_en", ""),
                "utility": c.get("utility", ""),
            })
    return customers


def _split_terms(*values: str) -> list[str]:
    """把 'PPC/Delgaz'、'PEA, MEA' 拆成单个检索词。"""
    terms = []
    for v in values:
        if not v:
            continue
        for part in re.split(r"[/、,，;；|\s]+", v):
            part = part.strip()
            if part:
                terms.append(part)
    return terms


def build_entity_terms(customers: list[dict]) -> list[str]:
    """生成需要跟踪的实体词：客户缩写 + 英文国家名。"""
    terms = []
    for c in customers:
        terms.extend(_split_terms(c.get("utility", "")))
        if c.get("country_en"):
            terms.append(c["country_en"])
    seen = set()
    out = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def build_entity_matcher(terms: list[str]):
    """构建实体匹配正则（纯字母数字词加词边界，避免误匹配）。"""
    patterns = []
    for t in terms:
        if re.fullmatch(r"[A-Za-z0-9]+", t):
            patterns.append(r"\b" + re.escape(t) + r"\b")
        else:
            patterns.append(re.escape(t))
    return re.compile("|".join(patterns), re.I)
