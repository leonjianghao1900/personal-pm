"""
个人 PM 启动/停止/重启/状态管理。
使用：python start.py [serve|start|stop|restart|status]（默认 serve）
  - serve    单进程模式：仅启动后端，直接托管前端构建产物（只需 Python）【默认】
  - start    开发模式：启动后端 + Vite 前端并打开浏览器（需 Node）
  - stop     停止后端和前端（按端口清理占用进程）
  - restart  停止后重新启动
  - status   显示前后端运行状态
双击 pm.bat 提供菜单选择。
"""
import os
import sys
import time
import socket
import subprocess
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

PYTHON = sys.executable
NPM = "npm.cmd"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BACKEND_PORT = 8765
FRONTEND_PORT = 5173


def port_in_use(port: int) -> bool:
    for family, addr in (
        (socket.AF_INET, ("127.0.0.1", port)),
        (socket.AF_INET6, ("::1", port, 0, 0)),
    ):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as s:
                if s.connect_ex(addr) == 0:
                    return True
        except OSError:
            pass
    return False


def wait_for_port(port: int, timeout: float = 60) -> bool:
    start = time.time()
    while time.time() - start < timeout:
        if port_in_use(port):
            return True
        time.sleep(0.5)
    return False


def kill_port(port: int) -> None:
    """Kill whatever is currently listening on the port (Windows-only via PowerShell)."""
    try:
        subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-Command",
                f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
                f"ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}"
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass


def stop_all() -> None:
    """Stop backend and frontend by freeing their ports."""
    for port in (BACKEND_PORT, FRONTEND_PORT):
        if port_in_use(port):
            print(f"→ 停止端口 {port} 上的进程 ...")
            kill_port(port)
            time.sleep(1)
        else:
            print(f"→ 端口 {port} 未占用，跳过")
    print("✓ 已停止（后端 + 前端）")


def print_status() -> None:
    """Print running status of backend and frontend."""
    print("🚀 个人 PM 状态")
    print("─" * 40)
    for name, port in (("后端 FastAPI", BACKEND_PORT), ("前端 Vite", FRONTEND_PORT)):
        url = f"http://localhost:{port}"
        if port_in_use(port):
            print(f"● {name} : http://localhost:{port}  运行中")
        else:
            print(f"○ {name} : http://localhost:{port}  未运行")
    print("─" * 40)


def _deps_stamp(venv_python: Path) -> Path:
    return venv_python.parent / ".deps-stamp"


def init_backend() -> None:
    venv = BACKEND_DIR / ".venv"
    if not venv.exists():
        print("→ 创建 Python 虚拟环境 ...")
        subprocess.check_call([PYTHON, "-m", "venv", str(venv)])
    pip = venv / "Scripts" / "pip.exe"
    stamp = _deps_stamp(venv / "Scripts" / "python.exe")
    pyproject_mtime = (BACKEND_DIR / "pyproject.toml").stat().st_mtime
    if stamp.exists() and stamp.stat().st_mtime >= pyproject_mtime:
        return
    print("→ 安装/更新后端依赖（首次或 pyproject.toml 变更后）...")
    subprocess.check_call([str(pip), "install", "-e", ".[dev]"], cwd=BACKEND_DIR)
    stamp.touch()


def init_frontend() -> None:
    if not (FRONTEND_DIR / "node_modules").exists():
        print("→ 安装前端依赖（首次需要 1-3 分钟）...")
        subprocess.check_call([NPM, "install"], cwd=FRONTEND_DIR)


def start_backend() -> None:
    if port_in_use(BACKEND_PORT):
        print(f"⚠ 端口 {BACKEND_PORT} 已占用，假设后端已在运行")
        return
    init_backend()
    print(f"→ 启动后端 (FastAPI @ {BACKEND_PORT}) ...")
    venv_python = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(BACKEND_PORT)],
        cwd=BACKEND_DIR,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def start_frontend() -> None:
    if port_in_use(FRONTEND_PORT):
        print(f"⚠ 端口 {FRONTEND_PORT} 已占用，假设前端已在运行")
        return
    init_frontend()
    print(f"→ 启动前端 (Vite @ {FRONTEND_PORT}) ...")
    flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
    subprocess.Popen(
        [NPM, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(FRONTEND_PORT)],
        cwd=FRONTEND_DIR,
        creationflags=flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if command == "stop":
        stop_all()
        return 0

    if command == "status":
        print_status()
        return 0

    if command == "restart":
        print("↻ 停止当前服务 ...")
        stop_all()
        command = "serve"

    if command not in ("start", "serve"):
        print(f"✗ 未知命令: {command}")
        print("  用法: python start.py [serve|start|stop|restart|status]")
        print("         默认 serve (单进程)；start 是开发模式（需 Node）")
        return 1

    serve_mode = command == "serve"

    print("🚀 个人 PM 启动器")
    print("─" * 40)

    if serve_mode:
        if not (FRONTEND_DIR / "dist" / "index.html").exists():
            print("✗ 未找到前端构建产物 frontend/dist/index.html")
            print("  请在开发机上先执行: cd frontend && npm run build")
            print("  然后把整个项目目录（含 dist）拷贝到目标电脑")
            return 1
        if port_in_use(BACKEND_PORT):
            print(f"→ 端口 {BACKEND_PORT} 已占用，先清理 ...")
            kill_port(BACKEND_PORT)
            time.sleep(1)
        start_backend()
        print("→ 等待后端就绪 ...")
        if not wait_for_port(BACKEND_PORT, timeout=30):
            print(f"✗ 后端启动超时（{BACKEND_PORT}）")
            return 1
        print("✓ 服务就绪，打开浏览器 ...")
        time.sleep(1)
        webbrowser.open(f"http://localhost:{BACKEND_PORT}")
        print()
        print("📌 已启动（单进程模式）：")
        print(f"   - 访问地址      : http://localhost:{BACKEND_PORT}")
        print(f"   - 关闭方式      : 双击 pm.bat 选 2 停止，或 python start.py stop")
        print(f"   - 重启          : 双击 pm.bat 选 3，或 python start.py restart")
        return 0

    for port in (BACKEND_PORT, FRONTEND_PORT):
        if port_in_use(port):
            print(f"→ 端口 {port} 已占用，先清理 ...")
            kill_port(port)
            time.sleep(1)

    start_backend()
    start_frontend()

    print("→ 等待后端就绪 ...")
    if not wait_for_port(BACKEND_PORT, timeout=30):
        print(f"✗ 后端启动超时（{BACKEND_PORT}）")
        return 1
    print("→ 等待前端就绪 ...")
    if not wait_for_port(FRONTEND_PORT, timeout=60):
        print(f"✗ 前端启动超时（{FRONTEND_PORT}）")
        return 1

    print("✓ 服务就绪，打开浏览器 ...")
    time.sleep(1)
    webbrowser.open(f"http://localhost:{FRONTEND_PORT}")

    print()
    print("📌 已启动：")
    print("   - 后端 FastAPI  : http://localhost:8765/docs")
    print("   - 前端 Vite     : http://localhost:5173")
    print("   - 关闭方式      : 双击 pm.bat 选 2 停止，或 python start.py stop")
    print("   - 重启          : 双击 pm.bat 选 3，或 python start.py restart")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n已取消")
        sys.exit(130)
    except Exception as e:
        print(f"✗ 启动失败: {e}")
        input("按 Enter 退出...")
        sys.exit(1)
