"""PyInstaller 打包后的入口脚本。

启动 FastAPI 应用，并把前端构建产物作为静态文件托管。
数据目录默认在 exe 同级 data/ 下，可通过 PM_DATA_DIR 覆盖。
"""
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path

PORT = 8765


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _dist_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "frontend" / "dist"
    return _base_dir() / "frontend" / "dist"


BASE_DIR = _base_dir()
DIST_DIR = _dist_dir()

os.environ["PM_DATA_DIR"] = str(BASE_DIR.parent / "exe_data")

from fastapi.responses import FileResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from app.main import app  # noqa: E402

INDEX = DIST_DIR / "index.html"
if INDEX.exists():
    assets = DIST_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = DIST_DIR / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(INDEX)


def _wait_and_open_browser() -> None:
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(("127.0.0.1", PORT)) == 0:
                    webbrowser.open(f"http://localhost:{PORT}")
                    return
        except OSError:
            pass
        time.sleep(0.3)


if __name__ == "__main__":
    threading.Thread(target=_wait_and_open_browser, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="info")