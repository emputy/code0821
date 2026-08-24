import sqlite3
from collections import Counter
from pathlib import Path

from PySide6.QtCharts import (
    QBarCategoryAxis, QBarSeries, QBarSet, QChart, QChartView, QPieSeries, QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from app.collector.fetch import load_sources
from app.filter.entities import (
    build_customer_matchers, build_entity_matcher, build_entity_terms, load_customers,
)
from app.filter.keywords import filter_db_rows

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
DB = BASE_DIR / "data" / "intel.db"
CUSTOMERS = BASE_DIR / "config" / "customers.json"


class VizPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(
            "QTabWidget::pane{border:1px solid rgba(255,255,255,0.12);border-radius:8px;}"
            "QTabBar::tab{background:transparent;padding:8px 16px;}"
            "QTabBar::tab:selected{background:rgba(255,255,255,0.12);border-radius:6px;}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.addWidget(self.tabs)
        self.customers = load_customers(str(CUSTOMERS))
        self.entity_re = build_entity_matcher(build_entity_terms(self.customers))
        self.source_cats = {s.id: s.category for s in load_sources(str(CONFIG))}
        self.refresh()

    def _relevant_rows(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute(
                "SELECT id, source_id, source_name, title, url, published, summary, country, fetched_at FROM items"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        return filter_db_rows(rows, self.entity_re, self.source_cats)

    def refresh(self):
        self.tabs.clear()
        self.tabs.addTab(self._chart_stage(), "客户阶段全景")
        self.tabs.addTab(self._chart_region(), "地区分布")
        self.tabs.addTab(self._chart_category(), "来源分类分布")
        self.tabs.addTab(self._chart_source(), "情报来源分布")
        self.tabs.addTab(self._chart_time(), "时间趋势")
        self.tabs.addTab(self._chart_stage_pie(), "情报阶段分布")

    @staticmethod
    def _bar_chart(categories, values, title, color):
        series = QBarSeries()
        bs = QBarSet("数量")
        for v in values:
            bs.append(v)
        bs.setColor(QColor(color))
        series.append(bs)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(title)
        ax = QBarCategoryAxis()
        ax.append(categories)
        chart.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)
        ay = QValueAxis()
        ay.setRange(0, max(values + [1]))
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ay)
        chart.legend().hide()
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view

    def _chart_stage(self):
        customers = load_customers(str(CUSTOMERS))
        counts = Counter(c["stage"] for c in customers)
        cats = [f"阶段 {i}" for i in range(1, 6)]
        vals = [counts.get(i, 0) for i in range(1, 6)]
        return self._bar_chart(cats, vals, "客户阶段全景（每阶段客户数）", "#4a90d9")

    def _chart_region(self):
        customers = load_customers(str(CUSTOMERS))
        counts = Counter(c["region"] for c in customers)
        cats = list(counts.keys())
        vals = [counts[c] for c in cats]
        return self._bar_chart(cats, vals, "客户地区分布", "#e67e22")

    def _chart_source(self):
        sources = load_sources(str(CONFIG))
        rows = self._relevant_rows()
        counts = Counter(r[2] for r in rows)
        cats, vals = [], []
        for s in sorted(sources, key=lambda x: (x.category, x.name)):
            cats.append(s.name_cn or s.name)
            vals.append(counts.get(s.name, 0))
        return self._bar_chart(cats, vals, "各来源相关情报量", "#27ae60")

    def _chart_category(self):
        sources = load_sources(str(CONFIG))
        rows = self._relevant_rows()
        counts = Counter(r[2] for r in rows)
        cat_cn = {"alliance": "联盟动态", "country": "重点国家", "competitor": "友商动态"}
        agg = Counter()
        for s in sources:
            if s.enabled:
                agg[cat_cn.get(s.category, s.category)] += counts.get(s.name, 0)
        series = QPieSeries()
        for k in ["联盟动态", "重点国家", "友商动态"]:
            series.append(k, agg.get(k, 0))
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("来源分类分布（联盟 / 重点国家 / 友商）")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view

    def _chart_time(self):
        rows = self._relevant_rows()
        days = Counter((r[8] or "")[:10] for r in rows)
        cats = sorted(days.keys())[-14:]
        vals = [days[d] for d in cats]
        if not cats:
            cats, vals = ["暂无数据"], [0]
        return self._bar_chart(cats, vals, "近 14 天情报趋势（按采集日）", "#8e44ad")

    def _chart_stage_pie(self):
        rows = self._relevant_rows()
        customers = load_customers(str(CUSTOMERS))
        matchers = build_customer_matchers(customers)
        counts = Counter()
        for row in rows:
            title = row[3]
            for rx, c in matchers:
                if rx.search(title or ""):
                    counts[f"阶段 {c['stage']}"] += 1
                    break
            else:
                counts["未匹配"] += 1
        series = QPieSeries()
        for k, v in counts.items():
            series.append(k, v)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("情报阶段分布")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view
