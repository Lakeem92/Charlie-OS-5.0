import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import argparse
import socket
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_EXE = ROOT / '.venv' / 'Scripts' / 'python.exe'
RUN_ALL = ROOT / 'run_all.py'
SCAN_NEWS = ROOT / 'tools' / 'watchlist_scanner' / 'scan_news.py'
SERVE = ROOT / 'Diet Bloomberg' / 'serve.py'
LOG_PATH = ROOT / 'logs' / 'diet_bloomberg_server.log'
PORT = 8766


def _python_cmd(script: Path, *args: str) -> list[str]:
    return [str(PYTHON_EXE), '-X', 'utf8', str(script), *args]


def _is_port_open(port: int) -> bool:
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=1):
            return True
    except OSError:
        return False


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
    if _is_port_open(PORT):
        print(f'[Diet Bloomberg] Already running on http://localhost:{PORT}')
        return True

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

    time.sleep(2)
    if _is_port_open(PORT):
        print(f'  Server running on http://localhost:{PORT}')
        return True

    print(f'  Failed to confirm server on port {PORT}. Check {LOG_PATH}.')
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