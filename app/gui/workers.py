import contextlib
import io

from PySide6.QtCore import QThread, Signal


class CollectWorker(QThread):
    """采集工作线程：抓取 → 过滤 → 入库。"""
    log = Signal(str)
    done = Signal(int, int)
    failed = Signal(str)

    def __init__(self, config, customers, db, parent=None):
        super().__init__(parent)
        self.config = config
        self.customers = customers
        self.db = db

    def run(self):
        from app.collector.fetch import fetch_all
        from app.filter.entities import build_entity_matcher, build_entity_terms, load_customers
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


class DeepSeekWorker(QThread):
    """调用 DeepSeek API 的通用工作线程。"""
    done = Signal(str)
    failed = Signal(str)

    def __init__(self, api_key, model, messages, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.model = model
        self.messages = messages

    def run(self):
        import requests
        url = "https://api.deepseek.com/chat/completions"
        headers = {"Authorization": "Bearer " + self.api_key, "Content-Type": "application/json"}
        payload = {"model": self.model, "messages": self.messages, "stream": False}
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=90)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            self.done.emit(content)
        except Exception as e:
            self.failed.emit(str(e))


class TestKeyWorker(QThread):
    """测试 API Key 是否有效（调用 models 接口）。"""
    ok = Signal()
    failed = Signal(str)

    def __init__(self, api_key, parent=None):
        super().__init__(parent)
        self.api_key = api_key

    def run(self):
        import requests
        try:
            resp = requests.get(
                "https://api.deepseek.com/models",
                headers={"Authorization": "Bearer " + self.api_key},
                timeout=30,
            )
            if resp.status_code == 200:
                self.ok.emit()
            else:
                self.failed.emit("HTTP " + str(resp.status_code) + ": " + resp.text[:200])
        except Exception as e:
            self.failed.emit(str(e))
