from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

from qfluentwidgets import FluentIcon, FluentWindow, InfoBar, InfoBarPosition, Theme, setTheme

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


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("无线专网情报监测系统")
        self.resize(1280, 800)
        self.collect_worker = None

        s0 = load_settings()
        setTheme(Theme.DARK if s0.get("dark_theme", True) else Theme.LIGHT)

        self.work_page = WorkPage()
        self.viz_page = VizPage()
        self.settings_page = SettingsPage()
        self.sources_page = SourcesPage()
        self.work_page.setObjectName("workPage")
        self.viz_page.setObjectName("vizPage")
        self.settings_page.setObjectName("settingsPage")
        self.sources_page.setObjectName("sourcesPage")

        self.addSubInterface(self.work_page, FluentIcon.HOME, "工作页面")
        self.addSubInterface(self.viz_page, FluentIcon.LIBRARY, "可视化")
        self.addSubInterface(self.settings_page, FluentIcon.ROBOT, "AI 设置")
        self.addSubInterface(self.sources_page, FluentIcon.CLOUD, "数据源")
        self.navigationInterface.expand(useAni=False)
        self.stackedWidget.currentChanged.connect(self._on_page_changed)

        self.settings_page.settings_changed.connect(self.work_page.refresh_buttons)
        self.settings_page.theme_changed.connect(self._apply_theme)
        self.settings_page.run_collect.connect(self.start_collect)
        self.sources_page.collect_requested.connect(self.start_collect)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._check_schedule)
        self.timer.start(60000)
        self._check_schedule()

    def _on_page_changed(self, index):
        if self.stackedWidget.currentWidget() is self.viz_page:
            self.viz_page.refresh()

    def _apply_theme(self):
        s = load_settings()
        setTheme(Theme.DARK if s.get("dark_theme", True) else Theme.LIGHT)

    def start_collect(self):
        if self.collect_worker and self.collect_worker.isRunning():
            QMessageBox.information(self, "采集", "采集正在进行中，请稍候")
            return
        InfoBar.info("采集", "正在采集最新数据……（约 10-15 分钟）", parent=self, position=InfoBarPosition.TOP)
        self.collect_worker = CollectWorker(str(CONFIG), str(CUSTOMERS), str(DB), self)
        self.collect_worker.log.connect(self.sources_page.append_log)
        self.collect_worker.done.connect(self._collect_done)
        self.collect_worker.failed.connect(self._collect_failed)
        self.collect_worker.start()

    def _collect_done(self, added, total):
        InfoBar.success("采集完成", f"新增 {added} 条，共 {total} 条", parent=self, position=InfoBarPosition.TOP)
        s = load_settings()
        s["last_run_at"] = datetime.now().isoformat(timespec="seconds")
        save_settings(s)
        self.settings_page.load_from_settings()
        self.sources_page.refresh_items()
        self.work_page.refresh_buttons()

    def _collect_failed(self, msg):
        QMessageBox.warning(self, "采集失败", str(msg))

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
            QMessageBox.information(self, "定时采集", "定时采集时间到了，正在自动采集最新数据……")
            self.start_collect()


def run():
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()
