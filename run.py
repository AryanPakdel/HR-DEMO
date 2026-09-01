#!/usr/bin/env python3
"""راه‌انداز داشبورد تحلیل جذب و استخدام.

اجرا:  python3 run.py

در اولین اجرا یک محیط مجازی در پوشه .venv ساخته و بسته‌های لازم را نصب می‌کند،
سپس سرور را بالا می‌آورد و مرورگر را باز می‌کند. اجراهای بعدی مستقیماً سرور را
اجرا می‌کنند.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import venv
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "8000"))
URL = f"http://{HOST}:{PORT}/"

# بسته‌هایی که بک‌اند به آنها نیاز دارد و ماژولی که برای بررسی وجودشان import می‌شود
REQUIREMENTS = [
    ("fastapi", "fastapi"),
    ("uvicorn[standard]", "uvicorn"),
    ("python-multipart", "multipart"),
    ("openpyxl", "openpyxl"),
    ("pandas", "pandas"),
    ("numpy", "numpy"),
    ("scikit-learn", "sklearn"),
]


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def missing_packages(python: Path) -> list[str]:
    """بسته‌هایی که با مفسر داده‌شده قابل import نیستند."""
    modules = [module for _, module in REQUIREMENTS]
    code = (
        "import importlib.util, sys\n"
        f"mods = {modules!r}\n"
        "print(','.join(m for m in mods if importlib.util.find_spec(m) is None))\n"
    )
    result = subprocess.run([str(python), "-c", code], capture_output=True, text=True)
    absent = {m for m in result.stdout.strip().split(",") if m}
    return [pkg for pkg, module in REQUIREMENTS if module in absent]


def ensure_environment() -> Path:
    """محیط اجرا را آماده می‌کند و مسیر مفسر مناسب را برمی‌گرداند."""
    current = Path(sys.executable)

    # اگر مفسر فعلی همه چیز را دارد، نیازی به ساخت محیط مجازی نیست
    if not missing_packages(current):
        return current

    if not VENV_DIR.exists():
        print("در حال ساخت محیط مجازی در .venv ...", flush=True)
        # system_site_packages تا pandas و numpy نصب‌شده دوباره دانلود نشوند
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(VENV_DIR)

    python = venv_python()
    if not python.exists():
        print("ساخت محیط مجازی ناموفق بود؛ نصب روی مفسر فعلی انجام می‌شود.")
        python = current

    absent = missing_packages(python)
    if absent:
        print("در حال نصب بسته‌های لازم:", "، ".join(absent), flush=True)
        result = subprocess.run(
            [str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", *absent]
        )
        if result.returncode != 0:
            print("\nنصب بسته‌ها با خطا مواجه شد. دستور زیر را دستی اجرا کنید:")
            print(f"  {python} -m pip install {' '.join(absent)}\n")
            sys.exit(1)
        still = missing_packages(python)
        if still:
            print("این بسته‌ها همچنان در دسترس نیستند:", "، ".join(still))
            sys.exit(1)
        print("نصب بسته‌ها کامل شد.", flush=True)

    return python


def open_browser_later() -> None:
    def target() -> None:
        time.sleep(2.0)
        try:
            webbrowser.open(URL)
        except Exception:
            pass

    threading.Thread(target=target, daemon=True).start()


def main() -> None:
    if not (ROOT / "frontend" / "index.html").exists():
        print("پوشه frontend یافت نشد. run.py باید در ریشه پروژه اجرا شود.")
        sys.exit(1)

    python = ensure_environment()

    print(f"\n  داشبورد تحلیل جذب و استخدام\n  آدرس: {URL}\n  توقف سرور: Ctrl+C\n", flush=True)
    open_browser_later()

    command = [
        str(python), "-m", "uvicorn", "backend.main:app",
        "--host", HOST, "--port", str(PORT), "--log-level", "warning",
    ]
    try:
        subprocess.run(command, cwd=ROOT)
    except KeyboardInterrupt:
        print("\nسرور متوقف شد.")


if __name__ == "__main__":
    main()
