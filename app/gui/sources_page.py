import json
import sqlite3

from PySide6.QtCore import QDate, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox, QDateEdit, QFormLayout, QHeaderView, QHBoxLayout, QLabel, QMessageBox,
    QStackedWidget, QTableWidget, QTableWidgetItem, QTextEdit, QTreeWidget,
    QTreeWidgetItem, QVBoxLayout, QWidget,
)

from qfluentwidgets import CardWidget, ComboBox, LineEdit, PushButton, SegmentedWidget, TableWidget

from app.collector.fetch import load_sources
from app.filter.entities import build_customer_matchers, load_customers
from app.filter.keywords import is_strong_relevant
from app.paths import BASE_DIR

CONFIG = BASE_DIR / "config" / "sources.json"
CUSTOMERS = BASE_DIR / "config" / "customers.json"
DB = BASE_DIR / "data" / "intel.db"
COUNTRIES_JSON = BASE_DIR / "config" / "countries.json"


def _load_countries() -> list:
    """从 config/countries.json 加载联合国 195 国清单。"""
    try:
        with open(COUNTRIES_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return [(c["code"], c["cn"], c["en"], c["region"]) for c in data.get("countries", [])]
    except Exception:
        return []


# 优先使用联合国 195 国清单（config/countries.json）；读取失败时回退内联清单
COUNTRY_LIST = _load_countries() or [
# (code, 中文名, 英文名, 地区) — fallback
    ("uae", "阿联酋", "UAE", "中东中亚"),
    ("saudi-arabia", "沙特", "Saudi Arabia", "中东中亚"),
    ("iraq", "伊拉克", "Iraq", "中东中亚"),
    ("oman", "阿曼", "Oman", "中东中亚"),
    ("pakistan", "巴基斯坦", "Pakistan", "中东中亚"),
    ("turkey", "土耳其", "Turkey", "中东中亚"),
    ("iran", "伊朗", "Iran", "中东中亚"),
    ("qatar", "卡塔尔", "Qatar", "中东中亚"),
    ("kuwait", "科威特", "Kuwait", "中东中亚"),
    ("jordan", "约旦", "Jordan", "中东中亚"),
    ("kazakhstan", "哈萨克斯坦", "Kazakhstan", "中东中亚"),
    ("uzbekistan", "乌兹别克斯坦", "Uzbekistan", "中东中亚"),
    ("china", "中国", "China", "亚太"),
    ("japan", "日本", "Japan", "亚太"),
    ("south-korea", "韩国", "South Korea", "亚太"),
    ("india", "印度", "India", "亚太"),
    ("indonesia", "印尼", "Indonesia", "亚太"),
    ("malaysia", "马来西亚", "Malaysia", "亚太"),
    ("thailand", "泰国", "Thailand", "亚太"),
    ("vietnam", "越南", "Vietnam", "亚太"),
    ("philippines", "菲律宾", "Philippines", "亚太"),
    ("singapore", "新加坡", "Singapore", "亚太"),
    ("bangladesh", "孟加拉", "Bangladesh", "亚太"),
    ("sri-lanka", "斯里兰卡", "Sri Lanka", "亚太"),
    ("australia", "澳大利亚", "Australia", "亚太"),
    ("new-zealand", "新西兰", "New Zealand", "亚太"),
    ("france", "法国", "France", "欧洲"),
    ("germany", "德国", "Germany", "欧洲"),
    ("united-kingdom", "英国", "United Kingdom", "欧洲"),
    ("italy", "意大利", "Italy", "欧洲"),
    ("spain", "西班牙", "Spain", "欧洲"),
    ("portugal", "葡萄牙", "Portugal", "欧洲"),
    ("netherlands", "荷兰", "Netherlands", "欧洲"),
    ("switzerland", "瑞士", "Switzerland", "欧洲"),
    ("sweden", "瑞典", "Sweden", "欧洲"),
    ("norway", "挪威", "Norway", "欧洲"),
    ("denmark", "丹麦", "Denmark", "欧洲"),
    ("finland", "芬兰", "Finland", "欧洲"),
    ("poland", "波兰", "Poland", "欧洲"),
    ("romania", "罗马尼亚", "Romania", "欧洲"),
    ("greece", "希腊", "Greece", "欧洲"),
    ("slovakia", "斯洛伐克", "Slovakia", "欧洲"),
    ("hungary", "匈牙利", "Hungary", "欧洲"),
    ("czechia", "捷克", "Czechia", "欧洲"),
    ("ireland", "爱尔兰", "Ireland", "欧洲"),
    ("austria", "奥地利", "Austria", "欧洲"),
    ("belgium", "比利时", "Belgium", "欧洲"),
    ("egypt", "埃及", "Egypt", "北部非洲"),
    ("algeria", "阿尔及利亚", "Algeria", "北部非洲"),
    ("morocco", "摩洛哥", "Morocco", "北部非洲"),
    ("tunisia", "突尼斯", "Tunisia", "北部非洲"),
    ("libya", "利比亚", "Libya", "北部非洲"),
    ("sudan", "苏丹", "Sudan", "北部非洲"),
    ("ethiopia", "埃塞俄比亚", "Ethiopia", "北部非洲"),
    ("south-africa", "南非", "South Africa", "南部非洲"),
    ("nigeria", "尼日利亚", "Nigeria", "南部非洲"),
    ("kenya", "肯尼亚", "Kenya", "南部非洲"),
    ("ghana", "加纳", "Ghana", "南部非洲"),
    ("angola", "安哥拉", "Angola", "南部非洲"),
    ("mozambique", "莫桑比克", "Mozambique", "南部非洲"),
    ("tanzania", "坦桑尼亚", "Tanzania", "南部非洲"),
    ("uganda", "乌干达", "Uganda", "南部非洲"),
    ("zambia", "赞比亚", "Zambia", "南部非洲"),
    ("zimbabwe", "津巴布韦", "Zimbabwe", "南部非洲"),
    ("cote-divoire", "科特迪瓦", "Cote d Ivoire", "南部非洲"),
    ("cameroon", "喀麦隆", "Cameroon", "南部非洲"),
    ("senegal", "塞内加尔", "Senegal", "南部非洲"),
    ("mali", "马里", "Mali", "南部非洲"),
    ("burkina-faso", "布基纳法索", "Burkina Faso", "南部非洲"),
    ("guinea", "几内亚", "Guinea", "南部非洲"),
    ("dr-congo", "刚果金", "DR Congo", "南部非洲"),
    ("brazil", "巴西", "Brazil", "拉美"),
    ("chile", "智利", "Chile", "拉美"),
    ("argentina", "阿根廷", "Argentina", "拉美"),
    ("ecuador", "厄瓜多尔", "Ecuador", "拉美"),
    ("colombia", "哥伦比亚", "Colombia", "拉美"),
    ("peru", "秘鲁", "Peru", "拉美"),
    ("mexico", "墨西哥", "Mexico", "拉美"),
    ("venezuela", "委内瑞拉", "Venezuela", "拉美"),
    ("bolivia", "玻利维亚", "Bolivia", "拉美"),
    ("paraguay", "巴拉圭", "Paraguay", "拉美"),
    ("uruguay", "乌拉圭", "Uruguay", "拉美"),
    ("panama", "巴拿马", "Panama", "拉美"),
    ("costa-rica", "哥斯达黎加", "Costa Rica", "拉美"),
    ("guatemala", "危地马拉", "Guatemala", "拉美"),
    ("honduras", "洪都拉斯", "Honduras", "拉美"),
]


class SourcesPage(QWidget):
    collect_requested = Signal()
    customers_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.customers = load_customers(str(CUSTOMERS))
        self.matchers = build_customer_matchers(self.customers)
        self.src_info = {s.name: (s.category, s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        self.all_rows = []

        self.pivot = SegmentedWidget(self)
        self.stack = QStackedWidget(self)
        self.pivot.addItem("k1", "情报列表", lambda: self.stack.setCurrentIndex(0))
        self.pivot.addItem("k2", "客户全景", lambda: self.stack.setCurrentIndex(1))
        self.pivot.addItem("k3", "数据源管理", lambda: (self.stack.setCurrentIndex(2), self.refresh_sources_table()))
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

        lay.addLayout(tb)

        # 第二行：搜索 + 筛选复选框（避免窄窗口挤压重叠）
        tb3 = QHBoxLayout()
        tb3.addWidget(QLabel("搜索:"))
        self.edt_keyword = LineEdit()
        self.edt_keyword.setPlaceholderText("搜标题/来源/阶段/国家...")
        self.edt_keyword.setFixedWidth(200)
        self.edt_keyword.setToolTip("按关键词过滤情报列表：匹配每条的标题、来源、阶段或国家（任一项包含即显示）")
        self.edt_keyword.textChanged.connect(lambda _: self.apply_filter())
        tb3.addWidget(self.edt_keyword)

        self.chk_strong = QCheckBox("只看强相关（450MHz/电力无线专网/频谱授用）")
        self.chk_strong.setChecked(True)
        self.chk_strong.setToolTip(
            "勾选：只显示与【450MHz / 电力无线专网 / 国家频谱授用】强相关的情报。\n"
            "命中任一关键词：450MHz、LTE450、专网、无线专网、电力专网、专用网络、private network、\n"
            "private LTE/5G、private wireless、industrial network、mission critical、critical communication、\n"
            "频谱、频谱拍卖/分配/牌照/许可/政策、spectrum (licence/auction/allocation/policy)、\n"
            "frequency、MHz、espectro、spektrum、spectre 等。\n"
            "取消勾选：显示全部原始数据。"
        )
        self.chk_strong.toggled.connect(lambda _: self.refresh_items())
        tb3.addWidget(self.chk_strong)
        self.chk_dated = QCheckBox("只看有发布日期")
        self.chk_dated.setChecked(False)
        self.chk_dated.toggled.connect(lambda _: self.refresh_items())
        tb3.addWidget(self.chk_dated)
        tb3.addStretch(1)
        lay.addLayout(tb3)

        tb2 = QHBoxLayout()
        tb2.addWidget(QLabel("时间范围:"))
        self.dt_start = QDateEdit()
        self.dt_start.setCalendarPopup(True)
        self.dt_start.setDate(QDate(2025, 1, 1))
        self.dt_start.setFixedWidth(110)
        self.dt_start.dateChanged.connect(lambda _: self.refresh_items())
        tb2.addWidget(self.dt_start)
        tb2.addWidget(QLabel("至"))
        self.dt_end = QDateEdit()
        self.dt_end.setCalendarPopup(True)
        self.dt_end.setDate(QDate.currentDate())
        self.dt_end.setFixedWidth(110)
        self.dt_end.dateChanged.connect(lambda _: self.refresh_items())
        tb2.addWidget(self.dt_end)
        tb2.addStretch(1)
        lay.addLayout(tb2)

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
        self.txt_log.setMaximumHeight(56)
        self.txt_log.setPlaceholderText("采集日志：这里显示每次抓取的最新信息")
        lay.addWidget(self.txt_log)
        return w

    def append_log(self, text):
        self.txt_log.append(text)

    def set_collect_progress(self, done, total):
        """采集进度显示：已完成源数 / 总源数。"""
        self.lbl_progress.setText(f"正在抓取 {done}/{total} 个数据源……")

    def _open_link(self, row, col):
        if col == 5:
            item = self.table.item(row, 5)
            url = item.data(Qt.UserRole) or item.text()
            if str(url).startswith("http"):
                QDesktopServices.openUrl(QUrl(str(url)))

    # ---------- 客户全景 ----------
    def _build_customers_tab(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(12)

        # 添加客户表单
        card = CardWidget()
        form = QFormLayout(card)
        form.setContentsMargins(16, 12, 16, 12)
        row1 = QHBoxLayout()
        self.edt_utility = LineEdit()
        self.edt_utility.setPlaceholderText("客户名称，如：Eskom / PLN")
        self.edt_utility.setFixedWidth(220)
        row1.addWidget(self.edt_utility)
        self.cmb_stage = ComboBox()
        for i in range(1, 6):
            self.cmb_stage.addItem("阶段 " + str(i), None, i)
        self.cmb_stage.setFixedWidth(110)
        row1.addWidget(self.cmb_stage)
        self.cmb_country = ComboBox()
        for code, cn, en, reg in COUNTRY_LIST:
            self.cmb_country.addItem(cn + "（" + en + "）", None, code)
        self.cmb_country.setFixedWidth(230)
        row1.addWidget(self.cmb_country)
        btn_add = PushButton("添加客户")
        btn_add.clicked.connect(self.add_customer)
        row1.addWidget(btn_add)
        row1.addStretch(1)
        form.addRow("新客户：", row1)
        lay.addWidget(card)

        self.cust_tree = QTreeWidget()
        self.cust_tree.setHeaderLabels(["阶段", "地区", "国家", "客户"])
        self.cust_tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        lay.addWidget(self.cust_tree, 1)
        self._fill_customers_tree()
        return w

    def _fill_customers_tree(self):
        tree = self.cust_tree
        tree.clear()
        groups = {}
        for c in self.customers:
            groups.setdefault(c["stage"], []).append(c)
        for stage in sorted(groups):
            items = groups[stage]
            top = QTreeWidgetItem(["阶段 " + str(stage) + "：" + items[0]["stage_name"], "", "", ""])
            tree.addTopLevelItem(top)
            for c in items:
                QTreeWidgetItem(top, ["", c["region"], c["country"], c["utility"]])
        tree.expandAll()

    def add_customer(self):
        """添加客户：写入 customers.json，自动启用该国情报源，联动刷新可视化。"""
        try:
            self._add_customer_impl()
        except Exception as e:
            import traceback
            try:
                with open(BASE_DIR / "data" / "error.log", "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc() + "\n")
            except Exception:
                pass
            QMessageBox.warning(self, "添加客户", "操作出错：" + str(e))

    def _add_customer_impl(self):
        name = self.edt_utility.text().strip()
        stage = int(self.cmb_stage.currentData() or 1)
        code = self.cmb_country.currentData()
        if not name:
            QMessageBox.warning(self, "添加客户", "请填写客户名称")
            return
        info = next((c for c in COUNTRY_LIST if c[0] == code), None)
        if not info:
            QMessageBox.warning(self, "添加客户", "请选择国家")
            return
        with open(CUSTOMERS, encoding="utf-8") as f:
            data = json.load(f)
        for st in data.get("stages", []):
            if st.get("stage") == stage:
                st.setdefault("customers", []).append({
                    "region": info[3], "country": info[1],
                    "country_en": info[2], "utility": name,
                })
                break
        with open(CUSTOMERS, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # 国家 -> 数据源联动：sources.json 中有该国的源则自动启用
        msgs = [self._ensure_source(code)]
        # 刷新本页与下游模块
        self.customers = load_customers(str(CUSTOMERS))
        self.matchers = build_customer_matchers(self.customers)
        self._fill_customers_tree()
        self.customers_changed.emit()
        extra = (" " + "；".join(msgs)) if msgs else ""
        QMessageBox.information(
            self, "添加客户",
            "已添加：" + name + "（阶段 " + str(stage) + "，" + info[1] + "）" + extra,
        )
        self.edt_utility.clear()

    def _ensure_source(self, code) -> str:
        """sources.json 中有该国的数据源则启用；返回提示文字。"""
        with open(CONFIG, encoding="utf-8") as f:
            data = json.load(f)
        hits = [s for s in data.get("sources", []) if s.get("country") == code]
        if not hits:
            return "该国家暂无内置情报源，可在「数据源管理」手动添加监管机构网址"
        msgs = []
        changed = False
        for s in hits:
            if not s.get("enabled", True):
                s["enabled"] = True
                changed = True
                msgs.append("已启用「" + (s.get("name_cn") or s["name"]) + "」")
        if changed:
            with open(CONFIG, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.refresh_sources_table()
        return "；".join(msgs) if msgs else "该国情报源「" + (hits[0].get("name_cn") or hits[0]["name"]) + "」已在抓取列表中"

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
            cat_cn = {"alliance": "联盟", "country": "重点国家", "competitor": "友商", "other": "其他国家"}
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
        if self.dt_start.date() > self.dt_end.date():
            self.lbl_progress.setText("时间范围无效：开始日期不能晚于结束日期")
            self.table.setRowCount(0)
            return
        try:
            conn = sqlite3.connect(str(DB))
            rows = conn.execute(
                "SELECT id, source_id, source_name, title, url, published, summary, country, fetched_at "
                "FROM items ORDER BY (published = '' OR published IS NULL), published DESC, id DESC"
            ).fetchall()
            conn.close()
        except Exception:
            rows = []
        start_s = self.dt_start.date().toString("yyyy-MM-dd")
        end_s = self.dt_end.date().toString("yyyy-MM-dd")
        if self.chk_dated.isChecked():
            rows = [r for r in rows if r[5] and start_s <= r[5][:10] <= end_s]
        else:
            rows = [r for r in rows if (not r[5]) or (start_s <= r[5][:10] <= end_s)]
        from app.gui.settings_store import load_settings as _ls
        custom = [k.lower() for k in _ls().get("custom_keywords", []) if k.strip()]
        if custom:
            rows = [r for r in rows if any(k in (r[3] or "").lower() or k in (r[6] or "").lower() for k in custom)]
        if getattr(self, "chk_strong", None) and self.chk_strong.isChecked():
            rows = [r for r in rows if is_strong_relevant((r[3] or "") + " " + (r[6] or ""))]
        self.all_rows = []
        for row in rows:
            t = row[5][:10] if row[5] else "—"
            src, title, url = row[2], row[3], row[4]
            stage, country = self._match_item(title, src, row[7], row[6])
            self.all_rows.append({
                "time": t, "source": src, "stage": stage,
                "country": country, "title": title, "url": url,
            })
        self.source_cn_map = {s.name: (s.name_cn or s.name) for s in load_sources(str(CONFIG))}
        sources = sorted(set(self.source_cn_map.values()))
        # 重建筛选下拉并复位为「全部」，保证默认显示全部数据
        self.cmb_source.blockSignals(True)
        self.cmb_source.clear()
        self.cmb_source.addItem("全部")
        for s in sources:
            self.cmb_source.addItem(s)
        self.cmb_source.setCurrentIndex(0)
        self.cmb_source.blockSignals(False)
        self.cmb_stage.blockSignals(True)
        self.cmb_stage.setCurrentIndex(0)
        self.cmb_stage.blockSignals(False)
        self.apply_filter()

    def _match_item(self, text, src_name, src_country="", summary=""):
        """给条目打阶段标签：客户实体（标题/摘要）-> 来源国家对应客户 -> 联盟/友商 -> 未匹配。"""
        for rx, c in self.matchers:
            if rx.search(text) or (summary and rx.search(summary)):
                return f"阶段 {c['stage']}", c["country"]
        if src_country:
            target = src_country.lower().replace("-", "").replace(" ", "")
            for c in self.customers:
                en = c.get("country_en", "").lower().replace("-", "").replace(" ", "")
                if en and en == target:
                    return f"阶段 {c['stage']}", c["country"]
        cat, name_cn = self.src_info.get(src_name, ("", ""))
        if cat == "alliance":
            return name_cn or "联盟", ""
        if cat == "competitor":
            return name_cn or "友商", ""
        return "未匹配", ""

    def apply_filter(self):
        try:
            self._apply_filter_impl()
        except Exception as e:
            import traceback
            try:
                with open(BASE_DIR / "data" / "error.log", "a", encoding="utf-8") as f:
                    f.write(traceback.format_exc() + "\n")
            except Exception:
                pass
            self.lbl_progress.setText("筛选出错：" + str(e))

    def _apply_filter_impl(self):
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
            if kw:
                hay = " ".join([
                    r["title"], r["source"], r["stage"], r["country"],
                ]).lower()
                if kw not in hay:
                    continue
            rows.append(r)
        self.table.setRowCount(0)
        self.table.setRowCount(len(rows))
        for i, r in enumerate(rows):
            vals = [r["time"], r["source"], r["stage"], r["country"], r["title"], "查看原文"]
            for j, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                if j == 5:
                    item.setData(Qt.UserRole, r["url"])
                    item.setToolTip(r["url"])
                    item.setForeground(QColor("#1a73e8"))
                else:
                    item.setToolTip(str(val))
                self.table.setItem(i, j, item)
        mode = "全部情报"
        self.lbl_progress.setText(f"显示 {len(rows)} / {len(self.all_rows)} 条{mode}")
