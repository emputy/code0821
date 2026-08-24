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
from app.filter.entities import build_customer_matchers, load_customers

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB = BASE_DIR / "data" / "intel.db"
CUSTOMERS = BASE_DIR / "config" / "customers.json"


class VizPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tabs = QTabWidget()
        lay = QVBoxLayout(self)
        lay.addWidget(self.tabs)
        self.refresh()

    def refresh(self):
        self.tabs.clear()
        self.tabs.addTab(self._chart_stage(), "客户阶段全景")
        self.tabs.addTab(self._chart_region(), "地区分布")
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
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute("SELECT source_name FROM items").fetchall()
            conn.close()
        except Exception:
            rows = []
        counts = Counter(r[0] for r in rows)
        cn_map = {s.name: (s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        cats = [cn_map.get(c, c) for c in counts.keys()]
        vals = [counts[c] for c in counts.keys()]
        return self._bar_chart(cats, vals, "各来源情报量", "#27ae60")

    def _chart_time(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute("SELECT fetched_at FROM items").fetchall()
            conn.close()
        except Exception:
            rows = []
        days = Counter((r[0] or "")[:10] for r in rows)
        cats = sorted(days.keys())[-14:]
        vals = [days[d] for d in cats]
        if not cats:
            cats, vals = ["暂无数据"], [0]
        return self._bar_chart(cats, vals, "近 14 天情报趋势（按采集日）", "#8e44ad")

    def _chart_stage_pie(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute("SELECT title FROM items").fetchall()
            conn.close()
        except Exception:
            rows = []
        customers = load_customers(str(CUSTOMERS))
        matchers = build_customer_matchers(customers)
        counts = Counter()
        for (title,) in rows:
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
