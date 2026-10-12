#!/usr/bin/env python
"""Bump version, rebuild, and publish a GitHub release.

Usage:
    python scripts/release.py 0.3.0

Steps performed:
    1. Validate version string (X.Y.Z) and confirm git working tree is clean.
    2. Update version constants in:
         - frontend/src/version.ts
         - installer.iss (AppVersion + OutputBaseFilename)
         - backend/app/version.py (APP_VERSION)
         - backend/app/main.py (FastAPI title version)
    3. Append a placeholder entry to CHANGELOG.md (caller fills in
       the bullet list afterwards).
    4. Commit on a release branch, push, then create a GitHub Release
       via the `gh` CLI attaching the freshly built installer + exe.
       Tag = v<version>.

Pre-requisites: gh CLI authenticated, npm + backend/.venv ready.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd, **kw):
    print(f"$ {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, check=True, **kw)


def parse_version(v: str) -> tuple[int, int, int]:
    m = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", v)
    if not m:
        raise SystemExit(f"invalid version: {v!r} (expected X.Y.Z)")
    return tuple(int(x) for x in m.groups())


def check_clean_tree():
    r = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if r.stdout.strip():
        raise SystemExit("git working tree not clean — commit/stash first")


def replace_in_file(path: Path, pattern: str, repl: str):
    text = path.read_text(encoding="utf-8")
    new = re.sub(pattern, repl, text, count=1)
    if new == text:
        raise SystemExit(f"pattern not found in {path}: {pattern!r}")
    path.write_text(new, encoding="utf-8")


def update_version_files(new_version: str):
    replace_in_file(
        ROOT / "frontend/src/version.ts",
        r"'v\d+\.\d+\.\d+'",
        f"'v{new_version}'",
    )
    replace_in_file(
        ROOT / "installer.iss",
        r"AppVersion=\d+\.\d+\.\d+",
        f"AppVersion={new_version}",
    )
    replace_in_file(
        ROOT / "installer.iss",
        r"OutputBaseFilename=PersonalPM-Setup-\d+\.\d+\.\d+",
        f"OutputBaseFilename=PersonalPM-Setup-{new_version}",
    )
    replace_in_file(
        ROOT / "backend/app/version.py",
        r'APP_VERSION = "\d+\.\d+\.\d+"',
        f'APP_VERSION = "{new_version}"',
    )
    replace_in_file(
        ROOT / "backend/app/main.py",
        r'version="\d+\.\d+\.\d+"',
        f'version="{new_version}"',
    )


def ensure_changelog_entry(new_version: str):
    path = ROOT / "CHANGELOG.md"
    if not path.exists():
        path.write_text(
            "# 更新日志\n\n"
            f"## v{new_version} ({_today()})\n\n_待补充_\n",
            encoding="utf-8",
        )
        return
    text = path.read_text(encoding="utf-8")
    header = f"## v{new_version} "
    if header in text:
        return
    text = text.replace(
        "# 更新日志\n\n",
        f"# 更新日志\n\n## v{new_version} ({_today()})\n\n_待补充_\n\n",
        1,
    )
    path.write_text(text, encoding="utf-8")


def _today() -> str:
    from datetime import date

    return date.today().isoformat()


def build_artifacts():
    print("\n=== building frontend ===")
    run(["npm", "run", "build"], cwd=ROOT / "frontend")
    print("\n=== building exe ===")
    run([sys.executable, "build.py"], cwd=ROOT)
    print("\n=== building installer ===")
    iscc = Path(r"C:\Users\leonj\AppData\Local\Programs\Inno Setup 6\ISCC.exe")
    if not iscc.exists():
        raise SystemExit(f"iscc not found at {iscc}")
    run([str(iscc), "installer.iss"])


def commit_and_tag(new_version: str):
    run(["git", "add", "-A"])
    run(["git", "commit", "-m", f"chore(release): v{new_version}"])
    run(["git", "push", "origin", "HEAD"])
    tag = f"v{new_version}"
    run(["git", "tag", "-f", tag])
    run(["git", "push", "origin", tag, "--force"])


def create_release(new_version: str):
    tag = f"v{new_version}"
    installer = ROOT / "installer" / f"PersonalPM-Setup-{new_version}.exe"
    portable = ROOT / "dist" / "personal-pm.exe"
    run(
        [
            "gh",
            "release",
            "create",
            tag,
            "--repo",
            "leonkangxi-dev/personal-pm",
            "--title",
            f"Personal PM v{new_version}",
            "--notes-file",
            str(ROOT / "CHANGELOG.md"),
            str(installer),
            str(portable),
        ]
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("version")
    args = ap.parse_args()
    new_version = args.version
    parse_version(new_version)

    if shutil.which("gh") is None:
        raise SystemExit("gh CLI not found — install GitHub CLI and auth first")

    print(f"\n=== releasing v{new_version} ===")
    check_clean_tree()
    update_version_files(new_version)
    ensure_changelog_entry(new_version)
    build_artifacts()
    commit_and_tag(new_version)
    create_release(new_version)
    print(f"\n✓ v{new_version} released")


if __name__ == "__main__":
    main()
