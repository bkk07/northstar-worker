"""Browser-test harness (Phase 10): real backend + real Vite + real Chromium.

Isolated ports (backend 8001, Vite 5174) keep these tests clear of dev
servers and the e2e suite. Seeded world, tmp storage/screenshots.
"""

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_PORT = 8001
FRONTEND_PORT = 5174
FRONTEND_ORIGIN = f"http://localhost:{FRONTEND_PORT}"

_backend_proc = None
_frontend_proc = None


def _wait_for(url: str, timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"server never came up: {url}")


@pytest.fixture(scope="session")
def servers():
    """Boot backend + frontend once per session; seed the world."""
    global _backend_proc, _frontend_proc
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(["common", "backend"])
    _backend_proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--app-dir",
            "backend",
            "--port",
            str(BACKEND_PORT),
        ],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    npm = shutil.which("npm")
    assert npm, "npm is required for browser tests"
    frontend_env = dict(os.environ)
    frontend_env["BACKEND_URL"] = f"http://127.0.0.1:{BACKEND_PORT}"
    _frontend_proc = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"],
        cwd=REPO_ROOT / "frontend",
        env=frontend_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for(f"http://127.0.0.1:{BACKEND_PORT}/api/health", 30)
        _wait_for(f"http://localhost:{FRONTEND_PORT}/", 90)
        from database.seeds import loader

        loader.seed()
        yield {"backend": BACKEND_PORT, "frontend": FRONTEND_ORIGIN}
    finally:
        for proc in (_frontend_proc, _backend_proc):
            if proc is not None:
                proc.terminate()
                try:
                    proc.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    proc.kill()
        _backend_proc = _frontend_proc = None


@pytest.fixture()
def run_dirs(tmp_path):
    """Per-test storage + screenshot dirs (no cross-test leakage)."""
    storage = tmp_path / "storage"
    shots = tmp_path / "shots"
    storage.mkdir()
    shots.mkdir()
    return storage, shots


@pytest.fixture()
def session(servers, run_dirs):
    """Fresh headless session per test (starts blank, no stored state)."""
    from browser.session import BrowserSession

    storage, shots = run_dirs
    browser_session = BrowserSession(
        f"test-{os.getpid()}",
        frontend_origin=servers["frontend"],
        storage_dir=storage,
        screenshot_dir=shots,
    ).start()
    try:
        yield browser_session
    finally:
        browser_session.stop()
