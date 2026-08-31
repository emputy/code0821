"""打包入口：PyInstaller 从这里启动 GUI（--windowed 无控制台）。

源码运行：python run.py  或  python -m app.gui
"""
import sys
from pathlib import Path

# 源码运行时把 vendor/（curl_cffi、playwright 等按需依赖）加入搜索路径
_vendor = Path(__file__).resolve().parent / "vendor"
if _vendor.is_dir() and str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))

from app.paths import ensure_runtime_files

if __name__ == "__main__":
    ensure_runtime_files()
    from app.gui.main_window import run

    run()
