"""打包入口：PyInstaller 从这里启动 GUI（--windowed 无控制台）。

源码运行：python run.py  或  python -m app.gui
"""
import sys

from app.paths import ensure_runtime_files

if __name__ == "__main__":
    ensure_runtime_files()
    from app.gui.main_window import run

    run()
