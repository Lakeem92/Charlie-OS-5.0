import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import argparse
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = ROOT / '.venv' / 'Scripts' / 'python.exe'
RUN_ALL = ROOT / 'run_all.py'
SCAN_NEWS = ROOT / 'tools' / 'watchlist_scanner' / 'scan_news.py'
SERVE = ROOT / 'Diet Bloomberg' / 'serve.py'
LOG_PATH = ROOT / 'logs' / 'diet_bloomberg_server.log'
PORT = 8766
HEALTH_URL = f'http://127.0.0.1:{PORT}/health'


def _python_cmd(script: Path, *args: str) -> list[str]:
    return [str(PYTHON_EXE), '-X', 'utf8', str(script), *args]


def _is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            return True
    except OSError:
        return False


def _server_health() -> tuple[bool, str]:
    if not _is_port_open(PORT):
        return False, 'port closed'

    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=3) as response:
            body = response.read().decode('utf-8', errors='replace').strip()
            if response.status == 200 and body == 'ok':
                return True, 'healthy'
            return False, f'health check returned {response.status}: {body[:160]}'
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace').strip()
        return False, f'health check returned {exc.code}: {body[:160]}'
    except OSError as exc:
        return False, str(exc)


def _find_listener_pid(port: int) -> int | None:
    result = subprocess.run(
        ['netstat', '-ano', '-p', 'tcp'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if result.returncode != 0:
        return None

    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address = parts[1]
        state = parts[3]
        if state != 'LISTENING' or not local_address.endswith(f':{port}'):
            continue
        try:
            return int(parts[4])
        except ValueError:
            return None
    return None


def _stop_listener(port: int, dry_run: bool) -> bool:
    pid = _find_listener_pid(port)
    if pid is None:
        return True

    print(f'[Diet Bloomberg] Stop unhealthy listener on port {port} (PID {pid})')
    if dry_run:
        return True

    result = subprocess.run(
        ['taskkill', '/PID', str(pid), '/F'],
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if result.stdout and result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr and result.stderr.strip():
        print(result.stderr.strip())
    return result.returncode == 0


def _run_step(label: str, cmd: list[str], dry_run: bool) -> bool:
    print(f'[{label}]')
    print('  ' + ' '.join(f'"{part}"' if ' ' in part else part for part in cmd))
    if dry_run:
        return True

    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    if result.stdout and result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr and result.stderr.strip():
        print(result.stderr.strip())
    print(f'  Exit code: {result.returncode}')
    return result.returncode == 0


def _start_server(dry_run: bool) -> bool:
    healthy, detail = _server_health()
    if healthy:
        print(f'[Diet Bloomberg] Already healthy on http://localhost:{PORT}')
        return True

    if _is_port_open(PORT):
        print(f'[Diet Bloomberg] Listener is up but unhealthy: {detail}')
        if not _stop_listener(PORT, dry_run):
            print(f'  Failed to stop unhealthy listener on port {PORT}.')
            return False

    cmd = _python_cmd(SERVE)
    print('[Diet Bloomberg] Launch server')
    print('  ' + ' '.join(f'"{part}"' if ' ' in part else part for part in cmd))
    if dry_run:
        return True

    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open('a', encoding='utf-8') as log_file:
        subprocess.Popen(
            cmd,
            cwd=ROOT,
            stdout=log_file,
            stderr=log_file,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
        )

    for _ in range(10):
        time.sleep(1)
        healthy, detail = _server_health()
        if healthy:
            print(f'  Server healthy on http://localhost:{PORT}')
            return True

    print(f'  Failed to confirm healthy server on port {PORT} ({detail}). Check {LOG_PATH}.')
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description='Refresh QuantLab dashboard data and start Diet Bloomberg.')
    parser.add_argument('--dry-run', action='store_true', help='Print planned actions without running them.')
    args = parser.parse_args()

    if not PYTHON_EXE.exists():
        raise FileNotFoundError(f'Python executable not found: {PYTHON_EXE}')

    ok = True
    ok = _start_server(args.dry_run) and ok
    ok = _run_step('Dashboard data refresh', _python_cmd(RUN_ALL), args.dry_run) and ok
    ok = _run_step(
        'Focus news refresh',
        _python_cmd(SCAN_NEWS, '--feed', 'focus', '--skip-tavily'),
        args.dry_run,
    ) and ok

    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())