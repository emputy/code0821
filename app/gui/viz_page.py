import sqlite3
from collections import Counter

from PySide6.QtCharts import (
    QBarSeries, QBarSet, QCategoryAxis, QChart, QChartView, QHorizontalBarSeries,
    QPieSeries, QPieSlice, QValueAxis,
)
from PySide6.QtCore import QMargins, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QStackedWidget, QVBoxLayout, QWidget

from qfluentwidgets import SegmentedWidget

# 扇形图调色板：Tableau 10（公认美观柔和的图表配色），扇区多时循环使用
PIE_COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2", "#59A14F",
    "#EDC948", "#B07AA1", "#FF9DA7", "#9C755F", "#BAB0AC",
]


from app.collector.fetch import load_sources
from app.filter.entities import (
    build_customer_matchers, build_entity_matcher, build_entity_terms, load_customers,
)
from app.filter.keywords import is_strong_relevant
from app.paths import BASE_DIR

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
        self.pivot.addItem("k3", "情报阶段分布", lambda: self.stack.setCurrentIndex(3))
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
        # 与工作页面「数据汇总」保持一致：只统计强相关（450MHz/电力无线专网/国家频谱授用）条目
        return [r for r in rows if is_strong_relevant((r[3] or "") + " " + (r[6] or ""))]

    def refresh(self):
        charts = [
            self._chart_stage(), self._chart_region(), self._chart_category(),
            self._chart_stage_pie(),
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

    def _pie_view(self, series, title):
        """饼图视图：图上不画标签；每个扇区用差异明显的颜色区分，
        图下方批注卡片每行带对应色块 + 名称/数量/占比。"""
        from PySide6.QtGui import QCursor
        from PySide6.QtWidgets import QToolTip

        slices = series.slices()
        for i, s in enumerate(slices):
            s.setLabelVisible(False)  # 图上不标注，杜绝重叠
            color = PIE_COLORS[i % len(PIE_COLORS)]
            s.setBrush(QColor(color))
            s.setBorderColor(QColor("#ffffff"))

        def _on_hover(slice, state):
            if state:
                total = sum(x.value() for x in series.slices())
                pct = (slice.value() / total * 100) if total else 0
                QToolTip.showText(QCursor.pos(), f"{slice.label()}: {int(slice.value())} ({pct:.1f}%)")
            else:
                QToolTip.hideText()

        series.hovered.connect(_on_hover)

        chart = QChart()
        chart.addSeries(series)
        chart.legend().hide()
        chart.setTitle(title)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)

        total = sum(s.value() for s in slices)
        from PySide6.QtWidgets import QFrame

        card = QWidget()
        card.setStyleSheet("background:#f5f5f5; border:1px solid #dcdcdc; border-radius:6px;")
        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(14, 10, 14, 10)
        vlay.setSpacing(5)
        for i, s in enumerate(slices):
            pct = (s.value() / total * 100) if total else 0
            color = PIE_COLORS[i % len(PIE_COLORS)]
            row = QHBoxLayout()
            row.setSpacing(8)
            swatch = QFrame()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet("background:" + color + "; border-radius:3px; border:none;")
            row.addWidget(swatch)
            lbl = QLabel("<b>" + s.label() + "</b>：" + str(int(s.value())) + " 条（" + f"{pct:.1f}" + "%）")
            lbl.setStyleSheet("font-size:13px; color:#333333; background:transparent; border:none;")
            row.addWidget(lbl)
            row.addStretch(1)
            vlay.addLayout(row)

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(view, 1)
        lay.addWidget(card)
        return w

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
        return self._pie_view(series, "来源分类分布（联盟 / 重点国家 / 友商）")

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
        return self._pie_view(series, "情报分布（客户阶段 / 来源）")
