from __future__ import annotations

import os
import socket
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT_DIR / "tests" / "fixtures" / "real_audio" / "neutral.wav"
REPORT_PATH = ROOT_DIR / "performance_report.md"


def _get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    with httpx.Client(timeout=2.0) as client:
        while time.time() < deadline:
            try:
                response = client.get(f"{base_url}/")
                if response.status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            time.sleep(0.5)
    raise RuntimeError("Timed out waiting for uvicorn to start")


def _working_set_bytes(pid: int) -> int | None:
    if os.name != "nt":
        return None

    command = f"(Get-Process -Id {pid}).WorkingSet64"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    try:
        return int(result.stdout.strip())
    except ValueError:
        return None


def _create_auth_header(client: httpx.Client, base_url: str) -> dict[str, str]:
    username = f"perf_{int(time.time() * 1000)}"
    response = client.post(
        f"{base_url}/user/init",
        json={"username": username, "password": "secret123"},
    )
    response.raise_for_status()
    token = response.json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}


def _post_audio(client: httpx.Client, base_url: str, headers: dict[str, str]) -> tuple[float, httpx.Response]:
    started = time.perf_counter()
    with FIXTURE_PATH.open("rb") as audio_file:
        response = client.post(
            f"{base_url}/mood/analyze",
            headers=headers,
            data={"language": "en"},
            files={"audio_file": (FIXTURE_PATH.name, audio_file, "audio/wav")},
        )
    elapsed = time.perf_counter() - started
    return elapsed, response


@pytest.mark.slow
def test_performance_smoke_writes_report():
    port = _get_free_port()
    base_url = f"http://127.0.0.1:{port}"
    env = os.environ.copy()
    env.setdefault("DATABASE_URL", f"sqlite:///{(ROOT_DIR / 'tests' / 'perf_test.db').as_posix()}")
    env.setdefault("SECRET_KEY", "perf-secret-key")
    env.setdefault("FASTER_WHISPER_MODEL", "tiny")
    env.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        _wait_for_server(base_url)
        rss_before = _working_set_bytes(process.pid)

        with httpx.Client(timeout=120.0) as client:
            headers = _create_auth_header(client, base_url)

            cold_latency, cold_response = _post_audio(client, base_url, headers)
            assert cold_response.status_code == 200

            rss_after = _working_set_bytes(process.pid)
            latencies: list[float] = []
            for _ in range(10):
                elapsed, response = _post_audio(client, base_url, headers)
                assert response.status_code == 200
                latencies.append(elapsed)

        p50 = statistics.median(latencies)
        p95 = sorted(latencies)[max(0, min(len(latencies) - 1, int(len(latencies) * 0.95) - 1))]

        lines = [
            "# Performance Report",
            "",
            f"- Cold-start latency: {cold_latency:.3f}s",
            f"- Warm-call p50: {p50:.3f}s",
            f"- Warm-call p95: {p95:.3f}s",
            f"- RSS before model load: {rss_before if rss_before is not None else 'unavailable'} bytes",
            f"- RSS after model load: {rss_after if rss_after is not None else 'unavailable'} bytes",
            "",
            "These are smoke-test measurements from a local CPU run using `tests/fixtures/real_audio/neutral.wav`.",
        ]
        REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
