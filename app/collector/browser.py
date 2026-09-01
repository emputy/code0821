"""Playwright 浏览器渲染抓取：解决 JS 渲染站点、TLS 指纹拦截、部分 WAF。

用法：sources.json 的源 options 里加 "browser": true，html 抓取器会改用
真实 Chromium 渲染后再解析链接。

实现：Playwright sync API 不能在多个线程间切换 greenlet，因此用一个
专属浏览器线程 + 任务队列串行渲染，采集工作线程只需提交 URL 并等待结果。
"""
import os
import queue
import threading
import time
from pathlib import Path

# 把 Chromium 安装目录固定到项目 vendor/pw-browsers（避免默认 %LOCALAPPDATA% 找不到）
_browsers_dir = Path(__file__).resolve().parents[2] / "vendor" / "pw-browsers"
if _browsers_dir.is_dir():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_browsers_dir))

_q = queue.Queue()
_thread = None
_start_lock = threading.Lock()
_unavailable = False  # 启动失败后置位，后续调用直接抛错

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def _worker():
    """专属浏览器线程：串行处理渲染请求。"""
    global _unavailable
    try:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
    except Exception as e:  # 启动失败：回掉所有排队请求
        _unavailable = True
        while True:
            try:
                item = _q.get_nowait()
            except queue.Empty:
                break
            if item is not None:
                item[3].append((None, e))
        return

    try:
        while True:
            item = _q.get()
            if item is None:
                break
            url, timeout_ms, proxy, result = item
            html, err = None, None
            try:
                ctx_kwargs = {
                    "user_agent": UA,
                    "ignore_https_errors": True,
                    "viewport": {"width": 1366, "height": 900},
                }
                if proxy:
                    ctx_kwargs["proxy"] = {"server": proxy}
                ctx = browser.new_context(**ctx_kwargs)
                try:
                    page = ctx.new_page()
                    page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                    page.wait_for_timeout(1200)  # 等待 JS 渲染
                    html = page.content()
                    page.close()
                finally:
                    ctx.close()
            except Exception as e:
                err = e
            result.append((html, err))
    finally:
        try:
            browser.close()
        except Exception:
            pass
        try:
            pw.stop()
        except Exception:
            pass


def _ensure_thread():
    global _thread, _unavailable
    with _start_lock:
        if _unavailable:
            raise RuntimeError("Playwright 浏览器不可用（此前启动失败）")
        if _thread is None or not _thread.is_alive():
            try:
                _thread = threading.Thread(target=_worker, daemon=True)
                _thread.start()
            except Exception:
                _unavailable = True
                raise


def render_html(url: str, timeout_ms: int = 40000, proxy: str = "") -> str:
    """用真实浏览器打开页面并返回渲染后的 HTML。"""
    _ensure_thread()
    result = []
    _q.put((url, timeout_ms, proxy, result))
    deadline = time.time() + (timeout_ms / 1000) + 60
    while not result and time.time() < deadline:
        time.sleep(0.1)
    if not result:
        raise TimeoutError("浏览器渲染超时")
    html, err = result[0]
    if err:
        raise err
    return html


def close():
    try:
        _q.put(None)
    except Exception:
        pass
