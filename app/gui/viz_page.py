import sqlite3
from collections import Counter
from pathlib import Path

from PySide6.QtCharts import (
    QBarSeries, QBarSet, QCategoryAxis, QChart, QChartView, QPieSeries, QPieSlice, QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import PushButton, SegmentedWidget


class ZoomChartView(QChartView):
    """支持滚轮缩放 / 双击重置的图表视图。

    缩放通过调整坐标轴范围实现，纵轴始终从 0 开始，保证柱子与横轴相连。
    """

    def __init__(self, chart, parent=None):
        super().__init__(chart, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(380)
        self._orig = {}
        for axis in chart.axes(Qt.Vertical):
            self._orig["y"] = (axis.min(), axis.max())
        for axis in chart.axes(Qt.Horizontal):
            self._orig["x"] = (axis.min(), axis.max())

    def _apply_zoom(self, factor):
        chart = self.chart()
        verts = chart.axes(Qt.Vertical)
        if not verts:  # 饼图没有坐标轴，用场景缩放
            chart.zoom(factor)
            return
        for axis in verts:
            if isinstance(axis, QValueAxis):
                rmin, rmax = axis.min(), axis.max()
                _, omax = self._orig.get("y", (rmin, rmax))
                new_max = min(omax, rmax / factor)
                if new_max > rmin + 1:
                    axis.setRange(rmin, new_max)  # 纵轴始终从 0 起
        for axis in chart.axes(Qt.Horizontal):
            if isinstance(axis, QCategoryAxis):
                rmin, rmax = axis.min(), axis.max()
                omin, omax = self._orig.get("x", (rmin, rmax))
                span = min((rmax - rmin) / factor, omax - omin)
                mid = (rmin + rmax) / 2
                new_min = max(omin, mid - span / 2)
                new_max = min(omax, mid + span / 2)
                if new_max - new_min > 1:
                    axis.setRange(new_min, new_max)

    def _reset(self):
        chart = self.chart()
        for axis in chart.axes(Qt.Vertical):
            if isinstance(axis, QValueAxis) and "y" in self._orig:
                axis.setRange(*self._orig["y"])
        for axis in chart.axes(Qt.Horizontal):
            if isinstance(axis, QCategoryAxis) and "x" in self._orig:
                axis.setRange(*self._orig["x"])
        chart.zoomReset()

    def wheelEvent(self, event):
        self._apply_zoom(1.2 if event.angleDelta().y() > 0 else 1 / 1.2)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        self._reset()
        event.accept()

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

        toolbar = QHBoxLayout()
        btn_zin = PushButton("放大")
        btn_zin.clicked.connect(lambda: self._zoom_current(1.2))
        btn_zout = PushButton("缩小")
        btn_zout.clicked.connect(lambda: self._zoom_current(1 / 1.2))
        btn_reset = PushButton("重置")
        btn_reset.clicked.connect(self._zoom_reset)
        toolbar.addWidget(btn_zin)
        toolbar.addWidget(btn_zout)
        toolbar.addWidget(btn_reset)
        toolbar.addStretch(1)
        hint = QLabel("滚轮缩放 / 拖拽框选放大 / 双击重置")
        toolbar.addWidget(hint)
        lay.addLayout(toolbar)

        lay.addWidget(self.stack, 1)
        self.customers = load_customers(str(CUSTOMERS))
        self.entity_re = build_entity_matcher(build_entity_terms(self.customers))
        self.source_cats = {s.id: s.category for s in load_sources(str(CONFIG))}
        self.refresh()

    def _zoom_current(self, factor):
        w = self.stack.currentWidget()
        if isinstance(w, ZoomChartView):
            w._apply_zoom(factor)

    def _zoom_reset(self):
        w = self.stack.currentWidget()
        if isinstance(w, ZoomChartView):
            w._reset()

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
        ax = QCategoryAxis()
        ax.setStartValue(0)
        for i, cat in enumerate(categories):
            ax.append(cat, i + 1)
        ax.setLabelsPosition(QCategoryAxis.AxisLabelsPositionCenter)
        chart.addAxis(ax, Qt.AlignBottom)
        series.attachAxis(ax)
        ay = QValueAxis()
        ay.setRange(0, max(values + [1]))
        chart.addAxis(ay, Qt.AlignLeft)
        series.attachAxis(ay)
        chart.legend().hide()
        return ZoomChartView(chart)

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

    @staticmethod
    def _label_pie(series):
        total = sum(s.value() for s in series.slices())
        for s in series.slices():
            pct = (s.value() / total * 100) if total else 0
            s.setLabel(f"{s.label()}: {int(s.value())} ({pct:.0f}%)")
            s.setLabelVisible(True)

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
        self._label_pie(series)
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("来源分类分布（联盟 / 重点国家 / 友商）")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        return ZoomChartView(chart)

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
        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("情报分布（客户阶段 / 来源）")
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        return ZoomChartView(chart)
