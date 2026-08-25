import sqlite3
from collections import Counter
from pathlib import Path

from PySide6.QtCharts import (
    QBarSeries, QBarSet, QCategoryAxis, QChart, QChartView, QHorizontalBarSeries,
    QPieSeries, QPieSlice, QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import SegmentedWidget


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
        self.pivot = SegmentedWidget(self)
        self.stack = QStackedWidget(self)
        self.pivot.addItem("k0", "客户阶段全景", lambda: self.stack.setCurrentIndex(0))
        self.pivot.addItem("k1", "地区分布", lambda: self.stack.setCurrentIndex(1))
        self.pivot.addItem("k2", "来源分类分布", lambda: self.stack.setCurrentIndex(2))
        self.pivot.addItem("k3", "情报来源分布", lambda: self.stack.setCurrentIndex(3))
        self.pivot.addItem("k4", "情报阶段分布", lambda: self.stack.setCurrentIndex(4))
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(self.pivot)
        lay.addWidget(self.stack, 1)
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
        charts = [
            self._chart_stage(), self._chart_region(), self._chart_category(),
            self._chart_source(), self._chart_stage_pie(),
        ]
        while self.stack.count() > 0:
            w = self.stack.widget(0)
            self.stack.removeWidget(w)
            w.deleteLater()
        for c in charts:
            self.stack.addWidget(c)
        self.stack.setCurrentIndex(0)

    def _hbar_chart(self, categories, values, title, color):
        """横向柱状图：分类名放左侧纵轴，适合分类多的情况。"""
        series = QHorizontalBarSeries()
        bs = QBarSet("数量")
        for v in values:
            bs.append(v)
        bs.setColor(QColor(color))
        series.append(bs)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle(title)

        ay = QCategoryAxis()
        ay.setStartValue(-0.5)
        for i, cat in enumerate(categories):
            ay.append(cat, i + 0.5)
        ay.setLabelsPosition(QCategoryAxis.AxisLabelsPositionCenter)
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ay)

        ax = QValueAxis()
        ax.setRange(0, max(values + [1]))
        chart.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)

        chart.legend().hide()
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        # 分类多时给足高度，但最小值控制在小值，避免把整个窗口撑大无法缩小
        view.setMinimumHeight(min(320, max(260, len(categories) * 24)))
        return view

    def _chart_stage(self):
        customers = load_customers(str(CUSTOMERS))
        counts = Counter(c["stage"] for c in customers)
        cats = [f"阶段 {i}" for i in range(1, 6)]
        vals = [counts.get(i, 0) for i in range(1, 6)]
        return self._hbar_chart(cats, vals, "客户阶段全景（每阶段客户数）", "#4a90d9")

    def _chart_region(self):
        customers = load_customers(str(CUSTOMERS))
        counts = Counter(c["region"] for c in customers)
        cats = list(counts.keys())
        vals = [counts[c] for c in cats]
        return self._hbar_chart(cats, vals, "客户地区分布", "#e67e22")

    def _chart_source(self):
        sources = load_sources(str(CONFIG))
        rows = self._relevant_rows()
        counts = Counter(r[2] for r in rows)
        # 只显示有数据的源，最多 Top 20（源太多时避免标签挤在一起）
        pairs = [(s.name_cn or s.name, counts.get(s.name, 0)) for s in sources]
        pairs = [(n, c) for n, c in pairs if c > 0]
        pairs.sort(key=lambda x: -x[1])
        pairs = pairs[:20]
        cats = [n for n, _ in pairs]
        vals = [c for _, c in pairs]
        return self._hbar_chart(cats, vals, "各来源相关情报量", "#27ae60")

    @staticmethod
    def _label_pie(series):
        """每个扇区都标注"名称: 数量 (占比)"：下方图例批注全部列出；
        占比 <5% 的小扇区不在图上画标签（避免文字叠加），但批注里仍然完整。"""
        total = sum(s.value() for s in series.slices())
        for s in series.slices():
            pct = (s.value() / total * 100) if total else 0
            # setLabel 同时影响扇区标签与下方图例批注
            s.setLabel(f"{s.label()}: {int(s.value())} ({pct:.0f}%)")
            s.setLabelVisible(pct >= 5)

    @staticmethod
    def _setup_pie_hover(series):
        """鼠标悬停到任意扇区时，弹出提示显示该扇区的数量与占比。"""
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QToolTip

        def _on_hover(slice, state):
            if state:
                QToolTip.showText(QCursor.pos(), slice.label())
            else:
                QToolTip.hideText()

        series.hovered.connect(_on_hover)

    def _chart_category(self):
        sources = load_sources(str(CONFIG))
        rows = self._relevant_rows()
        counts = Counter(r[2] for r in rows)
        cat_cn = {"alliance": "联盟动态", "country": "重点国家", "competitor": "友商动态", "other": "其他国家"}
        agg = Counter()
        for s in sources:
            if s.enabled:
                agg[cat_cn.get(s.category, s.category)] += counts.get(s.name, 0)
        series = QPieSeries()
        for k in ["联盟动态", "重点国家", "友商动态", "其他国家"]:
            series.append(k, agg.get(k, 0))
        self._label_pie(series)
        self._setup_pie_hover(series)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("来源分类分布（联盟 / 重点国家 / 友商）")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view

    def _chart_stage_pie(self):
        rows = self._relevant_rows()
        customers = load_customers(str(CUSTOMERS))
        matchers = build_customer_matchers(customers)
        src_info = {s.name: (s.category, s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        counts = Counter()
        for row in rows:
            title, src = row[3], row[2]
            matched = False
            for rx, c in matchers:
                if rx.search(title or ""):
                    counts[f"阶段 {c['stage']}"] += 1
                    matched = True
                    break
            if matched:
                continue
            cat, name_cn = src_info.get(src, ("", ""))
            if cat == "alliance":
                counts[name_cn or "联盟"] += 1
            elif cat == "competitor":
                counts[name_cn or "友商"] += 1
            else:
                counts["未匹配"] += 1
        series = QPieSeries()
        for k, v in counts.items():
            series.append(k, v)
        self._label_pie(series)
        self._setup_pie_hover(series)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("情报分布（客户阶段 / 来源）")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view
