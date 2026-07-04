import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_API_PORT = 8000
DEFAULT_UI_PORT = 8501


def find_available_port(preferred: int) -> int:
    for port in range(preferred, preferred + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No available port found from {preferred} to {preferred + 49}.")


def wait_for_url(url: str, timeout_seconds: int = 60) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 500:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1)
    return False


def start_process(args: list[str], env: dict[str, str]) -> subprocess.Popen:
    return subprocess.Popen(
        args,
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )


def terminate_process(process: subprocess.Popen, name: str) -> None:
    if process.poll() is not None:
        return
    print(f"Stopping {name}...")
    process.terminate()
    try:
        process.wait(timeout=8)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description="Start Intern-Hunter FastAPI backend and Streamlit frontend.")
    parser.add_argument("--api-port", type=int, default=DEFAULT_API_PORT, help="Preferred FastAPI port.")
    parser.add_argument("--ui-port", type=int, default=DEFAULT_UI_PORT, help="Preferred Streamlit port.")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser automatically.")
    args = parser.parse_args()

    api_port = find_available_port(args.api_port)
    ui_port = find_available_port(args.ui_port)
    api_url = f"http://127.0.0.1:{api_port}"
    ui_url = f"http://127.0.0.1:{ui_port}"

    env = os.environ.copy()
    env["API_BASE_URL"] = api_url
    env.setdefault("PYTHONUTF8", "1")

    if not (PROJECT_ROOT / ".env").exists():
        print("Warning: .env not found. DeepSeek calls will fail unless environment variables are already set.")
        print("Create it from .env.example and set DEEPSEEK_API_KEY before using LLM features.")

    print("Starting Intern-Hunter...")
    print(f"Backend API: {api_url}")
    print(f"Frontend UI: {ui_url}")

    api_process = start_process(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
        ],
        env,
    )

    if not wait_for_url(f"{api_url}/health", timeout_seconds=60):
        terminate_process(api_process, "FastAPI")
        print("FastAPI failed to start. Run `uvicorn app.main:app --reload` to view detailed errors.")
        return 1

    ui_process = start_process(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "frontend/streamlit_app.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(ui_port),
            "--server.headless",
            "true",
        ],
        env,
    )

    if not wait_for_url(ui_url, timeout_seconds=60):
        terminate_process(ui_process, "Streamlit")
        terminate_process(api_process, "FastAPI")
        print("Streamlit failed to start. Run `streamlit run frontend/streamlit_app.py` to view detailed errors.")
        return 1

    if not args.no_browser:
        webbrowser.open(ui_url)

    print("Intern-Hunter is running.")
    print("Press Ctrl+C to stop both backend and frontend.")
    try:
        while True:
            if api_process.poll() is not None:
                print("FastAPI process exited unexpectedly.")
                return 1
            if ui_process.poll() is not None:
                print("Streamlit process exited unexpectedly.")
                return 1
            time.sleep(1)
    except KeyboardInterrupt:
        print()
        return 0
    finally:
        terminate_process(ui_process, "Streamlit")
        terminate_process(api_process, "FastAPI")


if __name__ == "__main__":
    raise SystemExit(main())
