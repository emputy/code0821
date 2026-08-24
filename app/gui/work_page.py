import html as html_mod
import sqlite3
from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextBrowser, QVBoxLayout, QWidget,
)

from app.gui.settings_store import load_settings
from app.gui.workers import DeepSeekWorker

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB = BASE_DIR / "data" / "intel.db"
EXPORTS = BASE_DIR / "data" / "exports"


class WorkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self._build_ui()
        self.refresh_buttons()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        title = QLabel("工作页面")
        title.setStyleSheet("font-size:16px;font-weight:bold;")
        lay.addWidget(title)

        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        lay.addWidget(self.chat, 1)

        btns = QHBoxLayout()
        self.btn_raw = QPushButton("数据汇总")
        self.btn_raw.clicked.connect(self.show_raw)
        self.btn_analyze = QPushButton("分析信息数据")
        self.btn_analyze.clicked.connect(self.analyze)
        self.btn_export = QPushButton("导出内容")
        self.btn_export.clicked.connect(self.export)
        btns.addWidget(self.btn_raw)
        btns.addWidget(self.btn_analyze)
        btns.addWidget(self.btn_export)
        lay.addLayout(btns)

    def refresh_buttons(self):
        s = load_settings()
        self.btn_analyze.setVisible(bool(s.get("ai_enabled") and s.get("api_key")))

    def _bubble(self, title, body_html, color):
        h = f'<div style="background:{color};border-radius:8px;padding:8px;margin:4px 0;">'
        if title:
            h += f"<b>{html_mod.escape(title)}</b><br/>"
        h += body_html + "</div><br/>"
        self.chat.append(h)

    def _load_rows(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute(
                "SELECT fetched_at, source_name, title, url, summary FROM items ORDER BY fetched_at DESC, id DESC"
            ).fetchall()
            conn.close()
            return rows
        except Exception:
            return []

    def show_raw(self):
        """数据汇总：直接呈现原文，不分析不删减。"""
        self.chat.clear()
        rows = self._load_rows()
        if not rows:
            self._bubble("", "数据库暂无数据，请先到「数据源」模块点击「立即抓取」。", "#fff3cd")
            return
        self._bubble("", f"共 {len(rows)} 条原始数据（未经任何修改/总结）：", "#f0f0f0")
        for t, src, title, url, summary in rows[:50]:
            body = f"[{html_mod.escape(src)}] {html_mod.escape(t)}<br/><b>{html_mod.escape(title)}</b>"
            if url.startswith("http"):
                body += f"<br/><a href='{html_mod.escape(url)}'>{html_mod.escape(url)}</a>"
            if summary:
                body += f"<br/>摘要：{html_mod.escape(summary)}"
            self._bubble("", body, "#e8f4fd")

    def analyze(self):
        """分析信息数据：调用 AI 生成总结分析。"""
        s = load_settings()
        if not (s.get("ai_enabled") and s.get("api_key")):
            self._bubble("", "AI 功能未启用或未配置 API Key，请到「AI 设置」模块配置。", "#ffd9d9")
            return
        rows = self._load_rows()
        if not rows:
            self._bubble("", "数据库暂无数据。", "#fff3cd")
            return
        lines = []
        for t, src, title, url, summary in rows[:30]:
            lines.append(f"- [{src}] {title} ({url})")
        text = "\n".join(lines)
        messages = [
            {"role": "system", "content": "你是电力行业无线专网情报分析师。请对以下情报进行总结和分析，指出与电力无线专网、450MHz、频谱动态、客户进展相关的要点。"},
            {"role": "user", "content": text},
        ]
        self._bubble("", "正在生成分析，请稍候……", "#f0f0f0")
        self.worker = DeepSeekWorker(s["api_key"], s.get("model", "deepseek-chat"), messages, self)
        self.worker.done.connect(lambda c: self._bubble("分析结果", c.replace("\n", "<br/>"), "#eafaf1"))
        self.worker.failed.connect(lambda e: self._bubble("分析失败", html_mod.escape(str(e)), "#ffd9d9"))
        self.worker.start()

    def export(self):
        """导出 PDF / Word。"""
        rows = self._load_rows()
        if not rows:
            QMessageBox.information(self, "导出", "数据库暂无数据")
            return
        from datetime import datetime
        EXPORTS.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        word_path, pdf_path = None, None
        word_err = pdf_err = ""

        try:
            from docx import Document
            doc = Document()
            doc.add_heading("无线专网情报汇总", 0)
            for t, src, title, url, summary in rows:
                doc.add_heading(title, level=2)
                doc.add_paragraph(f"来源：{src}　时间：{t}\n链接：{url}")
                if summary:
                    doc.add_paragraph(summary)
            word_path = EXPORTS / f"intel_{stamp}.docx"
            doc.save(str(word_path))
        except Exception as e:
            word_err = str(e)

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
            from xml.sax.saxutils import escape
            pdf_path = EXPORTS / f"intel_{stamp}.pdf"
            doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
            styles = getSampleStyleSheet()
            story = [Paragraph("无线专网情报汇总", styles["Title"])]
            for t, src, title, url, summary in rows[:100]:
                story.append(Paragraph(escape(title), styles["Heading2"]))
                story.append(Paragraph(f"来源：{escape(src)}　时间：{escape(t)}<br/>链接：{escape(url)}", styles["BodyText"]))
                if summary:
                    story.append(Paragraph(escape(summary), styles["BodyText"]))
                story.append(Spacer(1, 8))
            doc.build(story)
        except Exception as e:
            pdf_err = str(e)

        msgs = []
        if word_path:
            msgs.append(f"✅ Word：{word_path}")
        else:
            msgs.append("❌ Word 导出失败：" + html_mod.escape(word_err))
        if pdf_path:
            msgs.append(f"✅ PDF：{pdf_path}")
        else:
            msgs.append("❌ PDF 导出失败：" + html_mod.escape(pdf_err))
        self._bubble("导出完成", "<br/>".join(msgs), "#eafaf1")
