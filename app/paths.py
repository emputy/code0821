"""打包感知的路径工具：源码运行与 PyInstaller 打包后都能正确定位 config / data。

- 源码运行：项目仓库根目录（<repo>/app/paths.py 的上两级）
- 打包运行（onefile/onedir）：exe 所在目录 —— 可写，便于把整个目录拷到其他电脑直接使用
"""
import shutil
import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def bundle_dir() -> Path:
    """PyInstaller 解包临时目录（仅打包后存在；源码运行时即仓库根）。"""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


BASE_DIR = base_dir()

# 打包后首次运行需要“就地初始化”的默认配置文件（settings.json 含个人 API Key，刻意不打包）
SEED_FILES = ("sources.json", "customers.json", "countries.json")


def ensure_runtime_files() -> None:
    """打包后首次运行：把内置的默认 config 复制到 exe 旁，并确保 data 目录存在。"""
    (BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
    if not is_frozen():
        return
    dst = BASE_DIR / "config"
    dst.mkdir(parents=True, exist_ok=True)
    src = bundle_dir() / "config"
    for name in SEED_FILES:
        s = src / name
        if s.exists() and not (dst / name).exists():
            try:
                shutil.copy2(s, dst / name)
            except OSError:
                pass
