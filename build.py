"""Build a single-file executable via PyInstaller.

Usage:
    backend\.venv\Scripts\python.exe build.py [--full-clean]

Output: dist\personal-pm.exe

默认行为：只删除要重新生成的 dist\personal-pm.exe，保留 dist\ 下其它文件
（如 dist\data\ 用户的 SQLite 数据库、dist\bak.*\ 备份目录）。这是防呆默认。
加 --full-clean 才会清空整个 dist/ 和 build/（仅在你确认没有 live 数据时使用）。
"""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--full-clean",
        action="store_true",
        help="删除整个 dist/ 和 build/ 再打包（危险，会清掉用户的 data/ 和备份）",
    )
    args = parser.parse_args()

    dist_dir = ROOT / "dist"
    build_dir = ROOT / "build"
    spec = ROOT / "personal-pm.spec"
    pyinstaller = ROOT / "backend" / ".venv" / "Scripts" / "pyinstaller.exe"
    if not pyinstaller.exists():
        print(f"✗ 未找到 {pyinstaller}")
        print("  请先安装: backend\\.venv\\Scripts\\pip.exe install pyinstaller")
        return 1

    if args.full_clean:
        for d in (dist_dir, build_dir):
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
    else:
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)
        exe_out = dist_dir / "personal-pm.exe"
        if exe_out.exists():
            exe_out.unlink()

    cmd = [str(pyinstaller), "--noconfirm", str(spec)]
    print("→", " ".join(cmd))
    rc = subprocess.call(cmd, cwd=str(ROOT))
    if rc != 0:
        print(f"✗ PyInstaller 退出码 {rc}")
        return rc
    out = dist_dir / "personal-pm.exe"
    if not out.exists():
        print("✗ 未生成 dist\\personal-pm.exe")
        return 1
    size_mb = out.stat().st_size / (1024 * 1024)
    print(f"✓ 已生成 {out} ({size_mb:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())