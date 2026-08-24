from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, Signal
from PySide6.QtWidgets import (
    QDateTimeEdit, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
    QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget,
)

from qfluentwidgets import ComboBox, LineEdit, PushButton, SwitchButton

from app.gui.settings_store import load_settings, save_settings
from app.gui.workers import TestKeyWorker


class SettingsPage(QWidget):
    settings_changed = Signal()
    run_collect = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.test_worker = None
        self._build_ui()
        self.load_from_settings()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)
        form = QFormLayout()

        self.edt_key = LineEdit()
        self.edt_key.setEchoMode(LineEdit.Password)
        self.edt_key.setPlaceholderText("输入 DeepSeek API Key（sk-...），回车或点别处即自动保存")
        self.edt_key.editingFinished.connect(self._on_key_edited)
        form.addRow("API Key：", self.edt_key)

        self.edt_test_key = LineEdit()
        self.edt_test_key.setEchoMode(LineEdit.Password)
        self.edt_test_key.setPlaceholderText("可临时输入 Key 测试连接（不会改动已保存的 Key）")
        form.addRow("测试连接 Key：", self.edt_test_key)

        self.lbl_test_result = QLabel("")
        form.addRow("", self.lbl_test_result)

        self.chk_ai = SwitchButton("启用 AI 功能（关闭后工作页面不显示「分析信息数据」按钮）")
        self.chk_ai.checkedChanged.connect(self._on_ai_toggled)
        form.addRow("", self.chk_ai)

        self.chk_translate = SwitchButton("启用原文翻译（原文 → 中文）")
        self.chk_translate.checkedChanged.connect(self._on_translate_toggled)
        form.addRow("", self.chk_translate)

        self.cmb_model = ComboBox()
        self.cmb_model.addItems(["deepseek-v4-flash", "deepseek-v4-pro"])
        self.cmb_model.setToolTip("deepseek-v4-flash：快速版；deepseek-v4-pro：专业版（分析更强）")
        form.addRow("模型：", self.cmb_model)

        self.spin_days = QSpinBox()
        self.spin_days.setRange(1, 365)
        self.spin_days.setSuffix(" 天")
        form.addRow("定时采集间隔：", self.spin_days)

        self.dt_schedule_start = QDateTimeEdit()
        self.dt_schedule_start.setCalendarPopup(True)
        self.dt_schedule_start.setDateTime(QDateTime.currentDateTime())
        form.addRow("定时开始时间：", self.dt_schedule_start)

        self.lbl_last = QLabel("")
        self.lbl_next = QLabel("")
        form.addRow("上次运行：", self.lbl_last)
        form.addRow("下次运行：", self.lbl_next)

        self.edt_keywords = QPlainTextEdit()
        self.edt_keywords.setPlaceholderText("每行一个关键词（固定数据源采集后二次筛选用），如：
450MHz
DEWA
巴西
ANATEL
频谱")
        self.edt_keywords.setFixedHeight(120)
        form.addRow("自定义筛选关键词：", self.edt_keywords)

        lay.addLayout(form)

        btns = QHBoxLayout()
        btn_test = PushButton("测试连接")
        btn_test.clicked.connect(self.test_connection)
        btn_save = PushButton("保存设置")
        btn_save.clicked.connect(self.save)
        btn_run = PushButton("立即采集一次")
        btn_run.clicked.connect(self.run_collect.emit)
        btns.addWidget(btn_test)
        btns.addWidget(btn_save)
        btns.addWidget(btn_run)
        lay.addLayout(btns)
        lay.addStretch(1)

    def _on_key_edited(self):
        s = load_settings()
        s["api_key"] = self.edt_key.text().strip()
        save_settings(s)
        self.settings_changed.emit()

    def _on_ai_toggled(self, checked):
        s = load_settings()
        s["ai_enabled"] = bool(checked)
        save_settings(s)
        self.settings_changed.emit()

    def _on_translate_toggled(self, checked):
        s = load_settings()
        s["translate_enabled"] = bool(checked)
        save_settings(s)

    def load_from_settings(self):
        s = load_settings()
        self.edt_key.setText(s.get("api_key", ""))
        self.chk_ai.blockSignals(True)
        self.chk_ai.setChecked(bool(s.get("ai_enabled")))
        self.chk_ai.blockSignals(False)
        self.chk_translate.blockSignals(True)
        self.chk_translate.setChecked(bool(s.get("translate_enabled", True)))
        self.chk_translate.blockSignals(False)
        self.cmb_model.setCurrentText(s.get("model", "deepseek-chat"))
        self.spin_days.setValue(int(s.get("schedule_interval_days", 14)))
        start = s.get("schedule_start", "")
        if start:
            try:
                self.dt_schedule_start.setDateTime(QDateTime.fromString(start, "yyyy-MM-dd HH:mm"))
            except Exception:
                pass
        kws = s.get("custom_keywords", [])
        self.edt_keywords.setPlainText("\n".join(kws))
        self._update_schedule_labels(s)

    def _update_schedule_labels(self, s=None):
        s = s or load_settings()
        last = s.get("last_run_at", "")
        self.lbl_last.setText(last or "从未运行")
        if last:
            try:
                nxt = datetime.fromisoformat(last) + timedelta(days=int(s.get("schedule_interval_days", 14)))
                self.lbl_next.setText(nxt.strftime("%Y-%m-%d %H:%M"))
            except Exception:
                self.lbl_next.setText("—")
        else:
            self.lbl_next.setText("—")

    def save(self):
        s = load_settings()
        s["api_key"] = self.edt_key.text().strip()
        s["ai_enabled"] = self.chk_ai.isChecked()
        s["translate_enabled"] = self.chk_translate.isChecked()
        s["model"] = self.cmb_model.currentText()
        s["schedule_interval_days"] = self.spin_days.value()
        s["schedule_start"] = self.dt_schedule_start.dateTime().toString("yyyy-MM-dd HH:mm")
        s["custom_keywords"] = [k.strip() for k in self.edt_keywords.toPlainText().splitlines() if k.strip()]
        save_settings(s)
        self._update_schedule_labels(s)
        self.settings_changed.emit()
        QMessageBox.information(self, "保存", "设置已保存")

    def test_connection(self):
        key = self.edt_test_key.text().strip() or self.edt_key.text().strip()
        if not key:
            self.lbl_test_result.setText("请先输入 API Key")
            return
        self.lbl_test_result.setText("测试中……")
        self.test_worker = TestKeyWorker(key, self)
        self.test_worker.ok.connect(lambda: self.lbl_test_result.setText("✅ Key 有效，连接正常"))
        self.test_worker.failed.connect(lambda e: self.lbl_test_result.setText("❌ " + str(e)[:90]))
        self.test_worker.start()
