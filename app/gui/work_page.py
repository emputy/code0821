import html as html_mod
import sqlite3
from pathlib import Path

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QHBoxLayout, QLabel, QMessageBox, QTextBrowser, QVBoxLayout, QWidget,
)

from qfluentwidgets import CardWidget, PushButton, SubtitleLabel

from app.collector.fetch import load_sources
from app.filter.entities import build_entity_matcher, build_entity_terms, load_customers
from app.filter.keywords import filter_db_rows
from app.gui.settings_store import load_settings
from app.gui.workers import DeepSeekWorker

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG = BASE_DIR / "config" / "sources.json"
CUSTOMERS = BASE_DIR / "config" / "customers.json"
DB = BASE_DIR / "data" / "intel.db"
EXPORTS = BASE_DIR / "data" / "exports"


class WorkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.customers = load_customers(str(CUSTOMERS))
        self.entity_re = build_entity_matcher(build_entity_terms(self.customers))
        self.source_cats = {s.id: s.category for s in load_sources(str(CONFIG))}
        self._build_ui()
        self.refresh_buttons()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)
        lay.addWidget(SubtitleLabel("工作页面"))

        row = QHBoxLayout()
        row.addWidget(QLabel("时间范围:"))
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate(2026, 1, 1))
        self.dt_start.dateChanged.connect(lambda _: self.show_raw())
        row.addWidget(self.dt_start)
        row.addWidget(QLabel("至"))
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate())
        self.dt_end.dateChanged.connect(lambda _: self.show_raw())
        row.addWidget(self.dt_end)
        self.chk_dated = QCheckBox("只看有发布日期")
        self.chk_dated.setChecked(False)
        self.chk_dated.toggled.connect(lambda _: self.show_raw())
        row.addWidget(self.chk_dated)
        row.addStretch(1)
        lay.addLayout(row)

        card = CardWidget()
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(16, 16, 16, 16)
        self.chat = QTextBrowser()
        self.chat.setOpenExternalLinks(True)
        self.chat.document().setDefaultStyleSheet(
            "table{border-collapse:collapse;margin:8px 0;}"
            "td,th{border:1px solid #999999;padding:4px 8px;}"
            "th{font-weight:bold;}"
        )
        card_lay.addWidget(self.chat)
        lay.addWidget(card, 1)

        btns = QHBoxLayout()
        self.chk_filter = QCheckBox("只看相关（关键词实时过滤）")
        self.chk_filter.setChecked(True)
        self.chk_filter.toggled.connect(lambda _: self.show_raw())
        btns.addWidget(self.chk_filter)
        self.btn_raw = PushButton("数据汇总")
        self.btn_raw.clicked.connect(self.show_raw)
        self.btn_analyze = PushButton("分析信息数据")
        self.btn_analyze.clicked.connect(self.analyze)
        self.btn_export = PushButton("导出内容")
        self.btn_export.clicked.connect(self.export)
        btns.addWidget(self.btn_raw)
        btns.addWidget(self.btn_analyze)
        btns.addWidget(self.btn_export)
        lay.addLayout(btns)

    def refresh_buttons(self):
        s = load_settings()
        self.btn_analyze.setVisible(bool(s.get("ai_enabled")))

    def _bubble(self, title, body_html, _color=None):
        """不自定义配色，交给主题渲染；用结构（粗体+分隔线）组织内容。"""
        h = ""
        if title:
            h += f"<div style='font-weight:600;margin-top:12px;'>{html_mod.escape(title)}</div>"
        h += f"<div style='margin:4px 0 10px 0;'>{body_html}</div>"
        h += "<hr style='border:none;border-top:1px solid rgba(128,128,128,0.3);'>"
        self.chat.append(h)

    def _load_rows(self):
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute(
                "SELECT id, source_id, source_name, title, url, published, summary, country, fetched_at "
                "FROM items ORDER BY fetched_at DESC, id DESC"
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
            self._bubble("", "数据库暂无数据，请先到「数据源」模块点击「立即抓取」。")
            return
        if self.chk_filter.isChecked():
            rows = filter_db_rows(rows, self.entity_re, self.source_cats)
        start_s = self.dt_start.date().toString("yyyy-MM-dd")
        end_s = self.dt_end.date().toString("yyyy-MM-dd")
        if self.chk_dated.isChecked():
            rows = [r for r in rows if r[5] and start_s <= r[5][:10] <= end_s]
        else:
            rows = [r for r in rows if (not r[5]) or (start_s <= r[5][:10] <= end_s)]
        custom = [k.lower() for k in load_settings().get("custom_keywords", []) if k.strip()]
        if custom:
            rows = [r for r in rows if any(k in (r[3] or "").lower() or k in (r[6] or "").lower() for k in custom)]
        cn_map = {s.name: (s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        mode = "相关" if self.chk_filter.isChecked() else "全部原始"
        self._bubble("", f"共 {len(rows)} 条{mode}数据（原文未删减，关键词实时过滤）：")
        for row in rows[:100]:
            src, title, url, summary = row[2], row[3], row[4], row[6]
            if row[5]:
                time_str = "发布：" + row[5][:10]
            elif row[8]:
                time_str = "抓取：" + row[8][:10] + "（未注明发布日期）"
            else:
                time_str = "时间：—"
            body = f"[{html_mod.escape(cn_map.get(src, src))}] {html_mod.escape(time_str)}<br/><b>{html_mod.escape(title)}</b>"
            if url.startswith("http"):
                body += f"<br/><a href='{html_mod.escape(url)}'>{html_mod.escape(url)}</a>"
            if summary:
                body += f"<br/>{html_mod.escape(summary)}"
            self._bubble("", body)

    def analyze(self):
        """分析信息数据：调用 AI 生成总结分析。"""
        s = load_settings()
        if not s.get("ai_enabled"):
            self._bubble("", "AI 功能未启用，请到「AI 设置」模块开启。")
            return
        if not s.get("api_key"):
            self._bubble("", "尚未配置 API Key，请到「AI 设置」模块填写后重试。")
            return
        rows = self._load_rows()
        if self.chk_filter.isChecked():
            rows = filter_db_rows(rows, self.entity_re, self.source_cats)
        start_s = self.dt_start.date().toString("yyyy-MM-dd")
        end_s = self.dt_end.date().toString("yyyy-MM-dd")
        if self.chk_dated.isChecked():
            rows = [r for r in rows if r[5] and start_s <= r[5][:10] <= end_s]
        else:
            rows = [r for r in rows if (not r[5]) or (start_s <= r[5][:10] <= end_s)]
        custom = [k.lower() for k in load_settings().get("custom_keywords", []) if k.strip()]
        if custom:
            rows = [r for r in rows if any(k in (r[3] or "").lower() or k in (r[6] or "").lower() for k in custom)]
        if not rows:
            self._bubble("", "当前条件下没有可分析的数据（可调整时间范围、关键词或『只看相关』）。")
            return
        cn_map = {s.name: (s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        lines = []
        for row in rows[:30]:
            src_cn = cn_map.get(row[2], row[2])
            lines.append(f"- [{src_cn}] {row[3]} | {row[4]}")
        text = "\n".join(lines)
        messages = [
            {"role": "system", "content": "你是电力行业无线专网情报分析师。基于下面提供的情报条目（每条含来源/标题/链接），产出一份简洁专业的中文情报简报。要求：1) 只基于实际提供的情报，不臆造不扩展；2) 结构为：核心要点 → 逐条分析（引用对应条目） → 趋势研判 → 行动建议；3) 明确标注与电力无线专网、450MHz、频谱、客户进展的直接关联程度；4) 篇幅精炼，可用 Markdown 表格对比。"},
            {"role": "user", "content": text},
        ]
        self._bubble("", "正在生成分析（基于相关条目），请稍候……")
        self.worker = DeepSeekWorker(s["api_key"], s.get("model", "deepseek-chat"), messages, self)
        self.worker.done.connect(self._show_analysis)
        self.worker.failed.connect(lambda e: self._bubble("分析失败", html_mod.escape(str(e))))
        self.worker.start()

    def _show_analysis(self, content):
        try:
            import markdown
            html = markdown.markdown(content, extensions=["tables"])
        except Exception:
            html = content.replace("\n", "<br/>")
        self._bubble("分析结果", html)

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
            for row in rows:
                src, title, url = row[2], row[3], row[4]
                pub = row[5][:10] if row[5] else ("抓取 " + row[8][:10] if row[8] else "未注明")
                doc.add_heading(title, level=2)
                doc.add_paragraph(f"来源：{src}  时间：{pub}  链接：{url}")
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
            for row in rows[:100]:
                src, title, url = row[2], row[3], row[4]
                pub = row[5][:10] if row[5] else ("抓取 " + row[8][:10] if row[8] else "未注明")
                story.append(Paragraph(escape(title), styles["Heading2"]))
                story.append(Paragraph(f"来源：{escape(src)}  时间：{escape(pub)}  链接：{escape(url)}", styles["BodyText"]))
                story.append(Spacer(1, 8))
            doc.build(story)
        except Exception as e:
            pdf_err = str(e)

        msgs = []
        if word_path:
            msgs.append(f"Word：{word_path}")
        else:
            msgs.append("Word 导出失败：" + html_mod.escape(word_err))
        if pdf_path:
            msgs.append(f"PDF：{pdf_path}")
        else:
            msgs.append("PDF 导出失败：" + html_mod.escape(pdf_err))
        self._bubble("导出完成", "<br/>".join(msgs))
