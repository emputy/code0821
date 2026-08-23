import re
import sqlite3
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QComboBox, QHeaderView, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMessageBox, QPushButton, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
    QWidget,
)

from app.filter.entities import load_customers

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
CUSTOMERS = BASE_DIR / "config" / "customers.json"
DB = BASE_DIR / "data" / "intel.db"


def _split_terms(*values):
    terms = []
    for v in values:
        if not v:
            continue
        for part in re.split(r"[/、,，;；|\s]+", v):
            part = part.strip()
            if part:
                terms.append(part)
    return terms


def build_customer_matchers(customers):
    """为每个客户构建匹配规则（客户缩写 + 英文国家名）。"""
    matchers = []
    for c in customers:
        for u in _split_terms(c.get("utility", "")):
            if re.fullmatch(r"[A-Za-z0-9]+", u):
                matchers.append((re.compile(r"\b" + re.escape(u) + r"\b", re.I), c))
            else:
                matchers.append((re.compile(re.escape(u), re.I), c))
        en = c.get("country_en", "")
        if en:
            matchers.append((re.compile(re.escape(en), re.I), c))
    return matchers


class CollectWorker(QThread):
    log = Signal(str)
    done = Signal(int, int)
    failed = Signal(str)

    def __init__(self, config, customers, db, parent=None):
        super().__init__(parent)
        self.config = config
        self.customers = customers
        self.db = db

    def run(self):
        import contextlib
        import io
        from app.collector.fetch import fetch_all
        from app.filter.entities import build_entity_matcher, build_entity_terms
        from app.filter.keywords import filter_items, load_keywords
        from app.storage.database import Database

        buf = io.StringIO()
        added, total = 0, 0
        try:
            with contextlib.redirect_stdout(buf):
                items = fetch_all(self.config)
                keywords = load_keywords(self.config)
                cust = load_customers(self.customers)
                terms = build_entity_terms(cust)
                matcher = build_entity_matcher(terms)
                items = filter_items(items, keywords, matcher)
                db = Database(self.db)
                added = db.save(items)
                total, _ = db.summary()
                db.close()
            self.log.emit(buf.getvalue())
            self.done.emit(added, total)
        except Exception as e:
            self.log.emit(buf.getvalue())
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无线专网情报监测系统")
        self.resize(1150, 720)
        self.customers = load_customers(str(CUSTOMERS))
        self.matchers = build_customer_matchers(self.customers)
        self.worker = None
        self.all_rows = []

        tabs = QTabWidget()
        tabs.addTab(self._build_items_tab(), "情报列表")
        tabs.addTab(self._build_customers_tab(), "客户全景")
        self.setCentralWidget(tabs)

        self.statusBar().showMessage("就绪")
        self.refresh_items()

    # ---------- 情报列表 ----------
    def _build_items_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)

        tb = QHBoxLayout()
        self.btn_collect = QPushButton("立即抓取")
        self.btn_collect.clicked.connect(self.start_collect)
        tb.addWidget(self.btn_collect)
        self.lbl_progress = QLabel("")
        tb.addWidget(self.lbl_progress)
        tb.addStretch(1)

        tb.addWidget(QLabel("来源:"))
        self.cmb_source = QComboBox()
        self.cmb_source.currentTextChanged.connect(lambda _: self.apply_filter())
        tb.addWidget(self.cmb_source)

        tb.addWidget(QLabel("阶段:"))
        self.cmb_stage = QComboBox()
        for s in ["全部", "阶段 1", "阶段 2", "阶段 3", "阶段 4", "阶段 5", "未匹配"]:
            self.cmb_stage.addItem(s)
        self.cmb_stage.currentTextChanged.connect(lambda _: self.apply_filter())
        tb.addWidget(self.cmb_stage)

        tb.addWidget(QLabel("搜索:"))
        self.edt_keyword = QLineEdit()
        self.edt_keyword.setPlaceholderText("标题关键词...")
        self.edt_keyword.textChanged.connect(lambda _: self.apply_filter())
        tb.addWidget(self.edt_keyword)
        lay.addLayout(tb)

        self.table = QTableWidget(0, 6)
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

    def _build_customers_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
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

    # ---------- 数据 ----------
    def refresh_items(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute(
                "SELECT fetched_at, source_name, title, url FROM items ORDER BY fetched_at DESC, id DESC"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        self.all_rows = []
        for t, src, title, url in rows:
            stage, country = self._match_item(title)
            self.all_rows.append({
                "time": t, "source": src, "stage": stage,
                "country": country, "title": title, "url": url,
            })
        sources = sorted({r["source"] for r in self.all_rows})
        self.cmb_source.blockSignals(True)
        self.cmb_source.clear()
        self.cmb_source.addItem("全部")
        for s in sources:
            self.cmb_source.addItem(s)
        self.cmb_source.blockSignals(False)
        self.apply_filter()

    def _match_item(self, text):
        for rx, c in self.matchers:
            if rx.search(text):
                return f"阶段 {c['stage']}", c["country"]
        return "未匹配", ""

    def apply_filter(self):
        src = self.cmb_source.currentText()
        stage = self.cmb_stage.currentText()
        kw = self.edt_keyword.text().strip().lower()
        rows = []
        for r in self.all_rows:
            if src != "全部" and r["source"] != src:
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
        self.statusBar().showMessage(f"显示 {len(rows)} / {len(self.all_rows)} 条")

    def _open_link(self, row, col):
        if col == 5:
            url = self.table.item(row, 5).text()
            if url.startswith("http"):
                QDesktopServices.openUrl(QUrl(url))

    # ---------- 抓取 ----------
    def start_collect(self):
        if self.worker and self.worker.isRunning():
            return
        self.btn_collect.setEnabled(False)
        self.lbl_progress.setText("采集中，请稍候（约 5-8 分钟）...")
        self.txt_log.clear()
        self.worker = CollectWorker(str(CONFIG), str(CUSTOMERS), str(DB), self)
        self.worker.log.connect(self.txt_log.append)
        self.worker.done.connect(self._collect_done)
        self.worker.failed.connect(self._collect_failed)
        self.worker.start()

    def _collect_done(self, added, total):
        self.btn_collect.setEnabled(True)
        self.lbl_progress.setText("")
        self.statusBar().showMessage(f"抓取完成：新增 {added} 条，共 {total} 条")
        self.refresh_items()

    def _collect_failed(self, msg):
        self.btn_collect.setEnabled(True)
        self.lbl_progress.setText("")
        QMessageBox.warning(self, "抓取失败", msg)


def run():
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()
