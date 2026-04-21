import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

"""
QuantLab — Unified Scheduler Setup
Registers ALL Windows Task Scheduler jobs for the QuantLab pipeline:
    Dashboard collectors (run_all.py): 6:15 AM CT, Mon-Fri
    News scanner — master:  6:30 AM / 7:30 AM / 8:06 AM CT, Mon-Fri
    News scanner — focus:   7:15 AM / 10:30 AM / 3:30 PM CT, Mon-Fri + Sun 6:00 PM CT

Idempotent — safe to run on every VS Code workspace open.
No admin required — creates user-level tasks.

Auto-triggered by VS Code folderOpen task (see .vscode/tasks.json).
Manual run:
    python C:\\QuantLab\\Data_Lab\\scripts\\setup_all_schedulers.py
"""

import subprocess
from pathlib import Path

PYTHON_EXE    = r'C:\QuantLab\Data_Lab\.venv\Scripts\python.exe'
RUN_ALL       = r'C:\QuantLab\Data_Lab\run_all.py'
SCAN_NEWS     = r'C:\QuantLab\Data_Lab\tools\watchlist_scanner\scan_news.py'

# ── All scheduled tasks ───────────────────────────────────────────────────────
TASKS = [
    # Dashboard collectors — fresh data before war room
    {
        'name': 'QuantLab_Dashboard_0615',
        'script': RUN_ALL,
        'time': '06:15',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
        'group': 'Dashboard',
    },
    # News scanner — master watchlist
    {
        'name': 'QuantLab_News_Flow_0630',
        'script': SCAN_NEWS,
        'time': '06:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
        'group': 'News (Master)',
    },
    {
        'name': 'QuantLab_News_Flow_0730',
        'script': SCAN_NEWS,
        'time': '07:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
        'group': 'News (Master)',
    },
    {
        'name': 'QuantLab_News_Flow_0806',
        'script': SCAN_NEWS,
        'time': '08:06',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
        'group': 'News (Master)',
    },
    # News scanner — focus list
    {
        'name': 'QuantLab_Focus_News_0715',
        'script': SCAN_NEWS,
        'time': '07:15',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': ['--feed', 'focus', '--skip-tavily'],
        'group': 'News (Focus)',
    },
    {
        'name': 'QuantLab_Focus_News_1030',
        'script': SCAN_NEWS,
        'time': '10:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': ['--feed', 'focus', '--skip-tavily'],
        'group': 'News (Focus)',
    },
    {
        'name': 'QuantLab_Focus_News_1530',
        'script': SCAN_NEWS,
        'time': '15:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': ['--feed', 'focus', '--skip-tavily'],
        'group': 'News (Focus)',
    },
    {
        'name': 'QuantLab_Focus_News_SUN_1800',
        'script': SCAN_NEWS,
        'time': '18:00',
        'days': 'SUN',
        'args': ['--feed', 'focus', '--skip-tavily'],
        'group': 'News (Focus)',
    },
]

# Legacy task names to clean up
LEGACY_TASKS = ['QuantLab_News_Flow']


# ── Helpers (same pattern as tools/watchlist_scanner/setup_scheduler.py) ──────

def check_python_exe() -> str:
    if Path(PYTHON_EXE).exists():
        return PYTHON_EXE
    import shutil
    system_py = shutil.which('python')
    if system_py:
        print(f'[WARN] .venv python not found at {PYTHON_EXE}')
        print(f'       Using system python: {system_py}')
        return system_py
    raise FileNotFoundError(
        f'No python found. Expected: {PYTHON_EXE}\n'
        'Create the venv first: python -m venv C:\\QuantLab\\Data_Lab\\.venv'
    )


def delete_task(name: str) -> bool:
    result = subprocess.run(
        ['schtasks', '/Delete', '/TN', name, '/F'],
        capture_output=True, text=True
    )
    return result.returncode == 0


def create_task(name: str, script: str, start_time: str, days: str,
                python_exe: str, script_args: list[str]) -> subprocess.CompletedProcess:
    arg_str = ' '.join(script_args).strip()
    task_cmd = f'"{python_exe}" "{script}"'
    if arg_str:
        task_cmd = f'{task_cmd} {arg_str}'

    cmd = [
        'schtasks', '/Create',
        '/TN', name,
        '/TR', task_cmd,
        '/SC', 'WEEKLY',
        '/D',  days,
        '/ST', start_time,
        '/F',
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    # Enable "run as soon as possible after missed" so tasks catch up after sleep/wake
    if result.returncode == 0:
        subprocess.run([
            'powershell', '-Command',
            f'$t = Get-ScheduledTask -TaskName "{name}"; '
            f'$t.Settings.StartWhenAvailable = $true; '
            f'Set-ScheduledTask -InputObject $t'
        ], capture_output=True, text=True)

    return result


def get_next_run(name: str) -> str:
    result = subprocess.run(
        ['schtasks', '/Query', '/TN', name, '/FO', 'LIST'],
        capture_output=True, text=True
    )
    for line in result.stdout.splitlines():
        if 'Next Run' in line:
            return line.strip()
    return ''


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print()
    print('=' * 60)
    print('  QuantLab — Unified Scheduler Setup')
    print('=' * 60)
    print('  Dashboard:     Mon-Fri @ 6:15 AM CT')
    print('  News (Master): Mon-Fri @ 6:30 / 7:30 / 8:06 AM CT')
    print('  News (Focus):  Mon-Fri @ 7:15 / 10:30 / 15:30 CT')
    print('                 Sun @ 18:00 CT')
    print('  StartWhenAvailable: ON (catches up after sleep)')
    print('-' * 60)

    python_exe = check_python_exe()
    print(f'  Python: {python_exe}')
    print()

    # Clean up legacy tasks
    for legacy in LEGACY_TASKS:
        if delete_task(legacy):
            print(f'  Removed legacy task: {legacy}')

    # Register all tasks
    created = 0
    failed = 0

    for task in TASKS:
        name = task['name']
        delete_task(name)  # idempotent — remove before recreating

        result = create_task(
            name=name,
            script=task['script'],
            start_time=task['time'],
            days=task['days'],
            python_exe=python_exe,
            script_args=task['args'],
        )

        if result.returncode == 0:
            next_run = get_next_run(name)
            next_str = f' | {next_run}' if next_run else ''
            print(f'  OK  {task["group"]:<16} {name:<38} @ {task["time"]} [{task["days"]}]{next_str}')
            created += 1
        else:
            print(f'  ERR {name}: {result.stderr.strip() or result.stdout.strip()}')
            failed += 1

    print()
    print('-' * 60)
    if failed == 0:
        print(f'  All {created} tasks registered successfully.')
    else:
        print(f'  {created}/{created + failed} tasks registered. {failed} failed.')
    print('  Missed tasks will run as soon as PC wakes up.')
    print('=' * 60)
    print()


if __name__ == '__main__':
    main()
