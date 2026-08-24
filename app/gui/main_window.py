from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout, QListWidget, QMainWindow, QMessageBox, QStackedWidget, QWidget,
)

from app.gui.settings_page import SettingsPage
from app.gui.settings_store import load_settings, save_settings
from app.gui.sources_page import SourcesPage
from app.gui.viz_page import VizPage
from app.gui.work_page import WorkPage
from app.gui.workers import CollectWorker

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
CUSTOMERS = BASE_DIR / "config" / "customers.json"
DB = BASE_DIR / "data" / "intel.db"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无线专网情报监测系统")
        self.resize(1250, 780)
        self.collect_worker = None

        self.nav = QListWidget()
        self.nav.addItems(["工作页面", "可视化", "AI 设置", "数据源"])
        self.nav.setFixedWidth(140)
        self.nav.setStyleSheet("QListWidget::item{padding:10px;}")
        self.nav.currentRowChanged.connect(self._switch)

        self.stack = QStackedWidget()
        self.work_page = WorkPage()
        self.viz_page = VizPage()
        self.settings_page = SettingsPage()
        self.sources_page = SourcesPage()
        for p in (self.work_page, self.viz_page, self.settings_page, self.sources_page):
            self.stack.addWidget(p)

        central = QWidget()
        lay = QHBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self.nav)
        lay.addWidget(self.stack, 1)
        self.setCentralWidget(central)

        # 模块间联动
        self.settings_page.settings_changed.connect(self.work_page.refresh_buttons)
        self.settings_page.run_collect.connect(self.start_collect)
        self.sources_page.collect_requested.connect(self.start_collect)

        self.nav.setCurrentRow(0)

        # 定时检查（每分钟一次）
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_schedule)
        self.timer.start(60000)
        self._check_schedule()

        self.statusBar().showMessage("就绪")

    def _switch(self, row):
        self.stack.setCurrentIndex(row)
        if row == 1:
            self.viz_page.refresh()

    # ---------- 采集 ----------
    def start_collect(self):
        if self.collect_worker and self.collect_worker.isRunning():
            QMessageBox.information(self, "采集", "采集正在进行中，请稍候")
            return
        self.statusBar().showMessage("正在采集最新数据……（约 5-8 分钟）")
        self.collect_worker = CollectWorker(str(CONFIG), str(CUSTOMERS), str(DB), self)
        self.collect_worker.log.connect(self.sources_page.append_log)
        self.collect_worker.done.connect(self._collect_done)
        self.collect_worker.failed.connect(self._collect_failed)
        self.collect_worker.start()

    def _collect_done(self, added, total):
        self.statusBar().showMessage(f"采集完成：新增 {added} 条，共 {total} 条")
        s = load_settings()
        s["last_run_at"] = datetime.now().isoformat(timespec="seconds")
        save_settings(s)
        self.settings_page.load_from_settings()
        self.sources_page.refresh_items()
        self.work_page.refresh_buttons()

    def _collect_failed(self, msg):
        self.statusBar().showMessage("采集失败：" + str(msg)[:80])
        QMessageBox.warning(self, "采集失败", str(msg))

    # ---------- 定时 ----------
    def _check_schedule(self):
        s = load_settings()
        last = s.get("last_run_at", "")
        interval = int(s.get("schedule_interval_days", 14))
        if not last:
            return
        try:
            last_dt = datetime.fromisoformat(last)
        except Exception:
            return
        if datetime.now() >= last_dt + timedelta(days=interval):
            self.statusBar().showMessage("定时采集时间到，开始自动采集……")
            QMessageBox.information(self, "定时采集", "定时采集时间到了，正在自动采集最新数据……")
            self.start_collect()


def run():
    from PySide6.QtWidgets import QApplication
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()
