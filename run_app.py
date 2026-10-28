"""Convenience runner for AI Business Intelligence Assistant.

Supports running:
- FastAPI backend only: python run_app.py --backend
- Streamlit UI only:   python run_app.py --ui
- Both simultaneously: python run_app.py
"""

import argparse
import os
import subprocess
import sys
import time


def get_python_executable():
    """Returns path to the virtualenv python if available, else sys.executable."""
    venv_py = os.path.join(os.path.dirname(__file__), ".venv", "Scripts", "python.exe")
    if os.path.exists(venv_py):
        return venv_py
    venv_py_unix = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python")
    if os.path.exists(venv_py_unix):
        return venv_py_unix
    return sys.executable


def run_backend(port: int = 8000):
    """Starts the FastAPI backend using uvicorn."""
    py = get_python_executable()
    cmd = [py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port), "--reload"]
    print(f"[*] Starting FastAPI backend on http://127.0.0.1:{port}...")
    subprocess.run(cmd)


def run_ui(port: int = 8501, server_port: int = 8000):
    """Starts the Streamlit UI."""
    py = get_python_executable()
    env = os.environ.copy()
    env["FASTAPI_URL"] = f"http://127.0.0.1:{server_port}"
    cmd = [
        py, "-m", "streamlit", "run", "ui.py",
        "--server.port", str(port),
        "--server.address", "0.0.0.0"
    ]
    print(f"[*] Starting Streamlit UI on http://127.0.0.1:{port}...")
    subprocess.run(cmd, env=env)


def run_all(backend_port: int = 8000, ui_port: int = 8501):
    """Starts both FastAPI backend and Streamlit UI concurrently."""
    py = get_python_executable()
    env = os.environ.copy()
    env["FASTAPI_URL"] = f"http://127.0.0.1:{backend_port}"

    print("=" * 65)
    print("      AI Business Intelligence Assistant - Dual Runner")
    print("=" * 65)
    print(f"[*] Launching FastAPI backend on http://127.0.0.1:{backend_port}")
    backend_proc = subprocess.Popen(
        [py, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(backend_port)],
        env=env
    )

    # Wait 1.5 seconds for FastAPI to bind
    time.sleep(1.5)

    print(f"[*] Launching Streamlit UI on http://127.0.0.1:{ui_port}")
    ui_proc = subprocess.Popen(
        [
            py, "-m", "streamlit", "run", "ui.py",
            "--server.port", str(ui_port),
            "--server.address", "0.0.0.0"
        ],
        env=env
    )

    print("\n[+] Both services are running!")
    print(f"    • FastAPI Docs: http://127.0.0.1:{backend_port}/docs")
    print(f"    • Streamlit UI: http://127.0.0.1:{ui_port}")
    print("\nPress Ctrl+C to terminate both services cleanly.\n")

    try:
        backend_proc.wait()
        ui_proc.wait()
    except KeyboardInterrupt:
        print("\n[*] Terminating services...")
        backend_proc.terminate()
        ui_proc.terminate()
        backend_proc.wait()
        ui_proc.wait()
        print("[+] All services stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Business Intelligence Assistant Runner")
    parser.add_argument("--backend", action="store_true", help="Run FastAPI backend only")
    parser.add_argument("--ui", action="store_true", help="Run Streamlit UI only")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--ui-port", type=int, default=8501, help="Streamlit port (default: 8501)")

    args = parser.parse_args()

    if args.backend and not args.ui:
        run_backend(args.backend_port)
    elif args.ui and not args.backend:
        run_ui(args.ui_port, args.backend_port)
    else:
        run_all(args.backend_port, args.ui_port)
