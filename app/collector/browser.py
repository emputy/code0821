"""Playwright 浏览器渲染抓取：解决 JS 渲染站点、TLS 指纹拦截、部分 WAF。

用法：sources.json 的源 options 里加 "browser": true，html 抓取器会改用
真实 Chromium 渲染后再解析链接。
"""
import os
import threading
from pathlib import Path

# 把 Chromium 安装目录固定到项目 vendor/pw-browsers（避免默认 %LOCALAPPDATA% 找不到）
_browsers_dir = Path(__file__).resolve().parents[2] / "vendor" / "pw-browsers"
if _browsers_dir.is_dir():
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", str(_browsers_dir))

_lock = threading.Lock()
_pw = None
_browser = None
_unavailable = False  # 启动失败后置位，后续调用直接抛错（避免每源反复尝试启动）


def _get_browser():
    global _pw, _browser, _unavailable
    with _lock:
        if _unavailable:
            raise RuntimeError("Playwright 浏览器不可用（此前启动失败）")
        if _browser is None:
            try:
                from playwright.sync_api import sync_playwright
                _pw = sync_playwright().start()
                _browser = _pw.chromium.launch(headless=True,
                                               args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
            except Exception:
                _unavailable = True
                raise
        return _browser


def render_html(url: str, timeout_ms: int = 40000, proxy: str = "") -> str:
    """用真实浏览器打开页面并返回渲染后的 HTML。"""
    browser = _get_browser()
    ctx_kwargs = {
        "user_agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
        "ignore_https_errors": True,
        "viewport": {"width": 1366, "height": 900},
    }
    if proxy:
        ctx_kwargs["proxy"] = {"server": proxy}
    ctx = browser.new_context(**ctx_kwargs)
    try:
        page = ctx.new_page()
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)  # 等待 JS 渲染完成
        html = page.content()
        page.close()
        return html
    finally:
        ctx.close()


def close():
    global _pw, _browser
    with _lock:
        if _browser is not None:
            try:
                _browser.close()
            except Exception:
                pass
            _browser = None
        if _pw is not None:
            try:
                _pw.stop()
            except Exception:
                pass
            _pw = None
