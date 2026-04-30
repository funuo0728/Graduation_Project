from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import shutil
import re


ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "frontend"

BACKEND_URL = "http://127.0.0.1:8002"
FRONTEND_URL = "http://localhost:5173"


def run(cmd: list[str], cwd: Path) -> None:
    print(f"\n$ ({cwd})> {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd, cwd=str(cwd), shell=False)


def popen(cmd: list[str], cwd: Path) -> subprocess.Popen:
    print(f"\n$ ({cwd})> {' '.join(cmd)}", flush=True)
    if os.name == "nt":
        # allow terminating the whole process tree
        return subprocess.Popen(cmd, cwd=str(cwd), creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    return subprocess.Popen(cmd, cwd=str(cwd))


def which_or_raise(candidates: list[str], display_name: str) -> str:
    for c in candidates:
        found = shutil.which(c)
        if found:
            return found
    raise FileNotFoundError(
        f"Cannot find {display_name} in PATH. Tried: {candidates}. "
        "Please install Node.js and ensure npm is available in PATH."
    )


def wait_for_health(timeout_s: int = 40) -> None:
    import requests

    deadline = time.time() + timeout_s
    last_err: Exception | None = None
    while time.time() < deadline:
        try:
            r = requests.get(f"{BACKEND_URL}/api/health", timeout=2)
            if r.ok:
                print("Backend OK:", r.json())
                return
        except Exception as e:
            last_err = e
        time.sleep(0.6)
    raise RuntimeError(f"Backend health check failed: {last_err}")


def backend_is_up() -> bool:
    try:
        import requests

        r = requests.get(f"{BACKEND_URL}/api/health", timeout=1.5)
        return bool(r.ok)
    except Exception:
        return False


def frontend_is_up() -> bool:
    try:
        import requests

        r = requests.get(FRONTEND_URL, timeout=1.5)
        return bool(r.ok)
    except Exception:
        return False


def find_listening_pid(port: int) -> int | None:
    if os.name != "nt":
        return None
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore")
    except Exception:
        return None
    # Example line: TCP    127.0.0.1:8002   0.0.0.0:0   LISTENING   9352
    pat = re.compile(rf"^\\s*TCP\\s+[^\\s]+:{port}\\s+[^\\s]+\\s+LISTENING\\s+(\\d+)\\s*$", re.MULTILINE)
    m = pat.search(out)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def kill_pid(pid: int) -> None:
    if os.name != "nt":
        return
    try:
        subprocess.check_call(["taskkill", "/PID", str(pid), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def scrape(categories: list[str], max_pages: int = 1) -> None:
    import requests

    payload = {"categories": categories, "max_pages": max_pages}
    r = requests.post(f"{BACKEND_URL}/api/scrape", json=payload, timeout=120)
    r.raise_for_status()
    print("Scrape result:", r.json())


def terminate(proc: subprocess.Popen, name: str) -> None:
    if proc.poll() is not None:
        return
    print(f"Stopping {name}...", flush=True)
    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            time.sleep(1)
        proc.terminate()
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def main() -> int:
    try:
        # Make logs show up immediately in Windows terminals too.
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass

    if not BACKEND_DIR.exists() or not FRONTEND_DIR.exists():
        print("Error: backend/ or frontend/ directory not found.")
        print(f"ROOT={ROOT}")
        return 1

    # 1) Install deps
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], cwd=BACKEND_DIR)
    npm = which_or_raise(["npm", "npm.cmd"], "npm")
    run([npm, "install"], cwd=FRONTEND_DIR)

    backend: subprocess.Popen | None = None
    frontend: subprocess.Popen | None = None

    # 2) Start backend (or reuse)
    try:
        if backend_is_up():
            print("Backend already running, reusing:", BACKEND_URL, flush=True)
        else:
            pid = find_listening_pid(8002)
            if pid:
                print(f"Port 8002 is in use by PID={pid}, killing it...", flush=True)
                kill_pid(pid)
                time.sleep(0.8)
            backend = popen(["uvicorn", "app.main:app", "--port", "8002"], cwd=BACKEND_DIR)
            wait_for_health()

        # 3) Scrape initial data (can comment out if you want it manual)
        scrape(["notices"], max_pages=1)
        scrape(["news"], max_pages=1)

        # 4) Start frontend (or reuse)
        if frontend_is_up():
            print("Frontend already running, reusing:", FRONTEND_URL, flush=True)
        else:
            pid = find_listening_pid(5173)
            if pid:
                print(f"Port 5173 is in use by PID={pid}, killing it...", flush=True)
                kill_pid(pid)
                time.sleep(0.8)
            frontend = popen([npm, "run", "dev", "--", "--port", "5173"], cwd=FRONTEND_DIR)

        print("\nPortal is starting.", flush=True)
        print("Backend:", BACKEND_URL, flush=True)
        print("Frontend:", FRONTEND_URL, flush=True)
        try:
            webbrowser.open(FRONTEND_URL)
        except Exception:
            pass

        # Wait until one of them exits
        while True:
            if backend is not None and backend.poll() is not None:
                raise RuntimeError("Backend exited unexpectedly.")
            if frontend is not None and frontend.poll() is not None:
                raise RuntimeError("Frontend exited unexpectedly.")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nCtrl+C received, shutting down...")
        return 0
    finally:
        # best-effort cleanup
        if backend is not None:
            try:
                terminate(backend, "backend")
            except Exception:
                pass
        if frontend is not None:
            try:
                terminate(frontend, "frontend")
            except Exception:
                pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

