import json
import sqlite3
from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QFormLayout, QHeaderView, QHBoxLayout, QLabel, QMessageBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from qfluentwidgets import CardWidget, ComboBox, LineEdit, PushButton, SegmentedWidget, TableWidget

from app.collector.fetch import load_sources
from app.filter.entities import build_customer_matchers, build_entity_matcher, build_entity_terms, load_customers
from app.filter.keywords import filter_db_rows

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
CUSTOMERS = BASE_DIR / "config" / "customers.json"
DB = BASE_DIR / "data" / "intel.db"


class SourcesPage(QWidget):
    collect_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.customers = load_customers(str(CUSTOMERS))
        self.matchers = build_customer_matchers(self.customers)
        self.entity_re = build_entity_matcher(build_entity_terms(self.customers))
        self.source_cats = {s.id: s.category for s in load_sources(str(CONFIG))}
        self.src_info = {s.name: (s.category, s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        self.all_rows = []

        self.pivot = SegmentedWidget(self)
        self.stack = QStackedWidget(self)
        self.pivot.addItem("k1", "情报列表", lambda: self.stack.setCurrentIndex(0))
        self.pivot.addItem("k2", "客户全景", lambda: self.stack.setCurrentIndex(1))
        self.pivot.addItem("k3", "数据源管理", lambda: self.stack.setCurrentIndex(2))
        self.stack.addWidget(self._build_list_tab())
        self.stack.addWidget(self._build_customers_tab())
        self.stack.addWidget(self._build_sources_tab())
        self.stack.setCurrentIndex(0)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(self.pivot)
        lay.addWidget(self.stack, 1)

        self.refresh_items()
        self.refresh_sources_table()

    # ---------- 情报列表 ----------
    def _build_list_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        tb = QHBoxLayout()
        self.btn_collect = PushButton("立即抓取")
        self.btn_collect.clicked.connect(self.collect_requested.emit)
        tb.addWidget(self.btn_collect)
        self.lbl_progress = QLabel("")
        tb.addWidget(self.lbl_progress)
        tb.addStretch(1)

        tb.addWidget(QLabel("来源:"))
        self.cmb_source = ComboBox()
        self.cmb_source.setFixedWidth(150)
        self.cmb_source.currentTextChanged.connect(lambda _: self.apply_filter())
        tb.addWidget(self.cmb_source)

        tb.addWidget(QLabel("阶段:"))
        self.cmb_stage = ComboBox()
        self.cmb_stage.setFixedWidth(110)
        for s in ["全部", "阶段 1", "阶段 2", "阶段 3", "阶段 4", "阶段 5", "未匹配"]:
            self.cmb_stage.addItem(s)
        self.cmb_stage.currentTextChanged.connect(lambda _: self.apply_filter())
        tb.addWidget(self.cmb_stage)

        tb.addWidget(QLabel("搜索:"))
        self.edt_keyword = LineEdit()
        self.edt_keyword.setPlaceholderText("标题关键词...")
        self.edt_keyword.setFixedWidth(150)
        self.edt_keyword.textChanged.connect(lambda _: self.apply_filter())
        tb.addWidget(self.edt_keyword)

        self.chk_relevant = QCheckBox("只看相关")
        self.chk_relevant.setChecked(True)
        self.chk_relevant.toggled.connect(lambda _: self.refresh_items())
        tb.addWidget(self.chk_relevant)
        lay.addLayout(tb)

        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["时间", "来源", "阶段", "国家", "标题", "链接"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellDoubleClicked.connect(self._open_link)
        lay.addWidget(self.table)

        self.txt_log = QTextEdit()
        self.txt_log.setReadOnly(True)
        self.txt_log.setMaximumHeight(140)
        lay.addWidget(self.txt_log)
        return w

    def append_log(self, text):
        self.txt_log.append(text)

    def _open_link(self, row, col):
        if col == 5:
            url = self.table.item(row, 5).text()
            if url.startswith("http"):
                QDesktopServices.openUrl(QUrl(url))

    # ---------- 客户全景 ----------
    def _build_customers_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        tree = QTreeWidget()
        tree.setHeaderLabels(["阶段", "地区", "国家", "客户"])
        tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        groups = {}
        for c in self.customers:
            groups.setdefault(c["stage"], []).append(c)
        for stage in sorted(groups):
            items = groups[stage]
            top = QTreeWidgetItem([f"阶段 {stage}：{items[0]['stage_name']}", "", "", ""])
            tree.addTopLevelItem(top)
            for c in items:
                QTreeWidgetItem(top, ["", c["region"], c["country"], c["utility"]])
        tree.expandAll()
        lay.addWidget(tree)
        return w

    # ---------- 数据源管理 ----------
    def _build_sources_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        self.src_table = TableWidget(self)
        self.src_table.setColumnCount(5)
        self.src_table.setHorizontalHeaderLabels(["分类", "名称", "类型", "URL", "启用"])
        self.src_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        lay.addWidget(self.src_table)

        card = CardWidget()
        card.setMinimumHeight(180)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(20, 16, 20, 16)
        form = QFormLayout()
        self.edt_name = LineEdit()
        self.edt_name.setPlaceholderText("如：巴西 ANATEL")
        self.cmb_type = ComboBox()
        self.cmb_type.addItems(["rss", "html", "sitemap"])
        self.edt_url = LineEdit()
        self.edt_url.setPlaceholderText("https://...")
        self.edt_country = LineEdit()
        self.edt_country.setPlaceholderText("如：brazil（留空默认 global）")
        card_lay.addLayout(form)
        btn_add = PushButton("添加数据源")
        btn_add.clicked.connect(self.add_source)
        card_lay.addWidget(btn_add)
        lay.addWidget(card)
        form.addRow("名称：", self.edt_name)
        form.addRow("类型：", self.cmb_type)
        form.addRow("URL：", self.edt_url)
        form.addRow("国家：", self.edt_country)
        return w

    def refresh_sources_table(self):
        sources = load_sources(str(CONFIG))
        self.src_table.setRowCount(len(sources))
        for i, s in enumerate(sources):
            cat_cn = {"alliance": "联盟", "country": "重点国家", "competitor": "友商"}
            vals = [cat_cn.get(s.category, s.category), s.name_cn or s.name, s.type, s.url, "是" if s.enabled else "否"]
            for j, val in enumerate(vals):
                self.src_table.setItem(i, j, QTableWidgetItem(str(val)))

    def add_source(self):
        name = self.edt_name.text().strip()
        url = self.edt_url.text().strip()
        if not name or not url:
            QMessageBox.warning(self, "添加数据源", "名称和 URL 不能为空")
            return
        with open(CONFIG, encoding="utf-8") as f:
            data = json.load(f)
        data["sources"].append({
            "id": name.lower().replace(" ", "_"),
            "name": name,
            "type": self.cmb_type.currentText(),
            "url": url,
            "country": self.edt_country.text().strip() or "global",
            "enabled": True,
        })
        with open(CONFIG, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.refresh_sources_table()
        QMessageBox.information(self, "添加数据源", "已添加：" + name + "\n（下次抓取时生效）")

    # ---------- 数据 ----------
    def refresh_items(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute(
                "SELECT id, source_id, source_name, title, url, published, summary, country, fetched_at "
                "FROM items ORDER BY fetched_at DESC, id DESC"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        if self.chk_relevant.isChecked():
            rows = filter_db_rows(rows, self.entity_re, self.source_cats)
        self.all_rows = []
        for row in rows:
            t, src, title, url = row[8], row[2], row[3], row[4]
            stage, country = self._match_item(title, src)
            self.all_rows.append({
                "time": t, "source": src, "stage": stage,
                "country": country, "title": title, "url": url,
            })
        self.source_cn_map = {s.name: (s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        sources = sorted(set(self.source_cn_map.values()))
        self.cmb_source.blockSignals(True)
        self.cmb_source.clear()
        self.cmb_source.addItem("全部")
        for s in sources:
            self.cmb_source.addItem(s)
        self.cmb_source.blockSignals(False)
        self.apply_filter()

    def _match_item(self, text, src_name):
        for rx, c in self.matchers:
            if rx.search(text):
                return f"阶段 {c['stage']}", c["country"]
        cat, name_cn = self.src_info.get(src_name, ("", ""))
        if cat == "alliance":
            return name_cn or "联盟", ""
        if cat == "competitor":
            return name_cn or "友商", ""
        return "未匹配", ""

    def apply_filter(self):
        src = self.cmb_source.currentText()
        stage = self.cmb_stage.currentText()
        kw = self.edt_keyword.text().strip().lower()
        src_target = {v: k for k, v in getattr(self, "source_cn_map", {}).items()}.get(src, src)
        rows = []
        for r in self.all_rows:
            if src != "全部" and r["source"] != src_target:
                continue
            if stage != "全部" and r["stage"] != stage:
                continue
            if kw and kw not in r["title"].lower():
                continue
            rows.append(r)
        self.table.setRowCount(0)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["time"], r["source"], r["stage"], r["country"], r["title"], r["url"]]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setToolTip(str(val))
                self.table.setItem(i, j, item)
        self.lbl_progress.setText(f"显示 {len(rows)} / {len(self.all_rows)} 条")
