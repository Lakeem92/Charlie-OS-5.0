import sys, os
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

"""
QuantLab News Flow — Windows Task Scheduler Setup
Creates scheduled tasks to run scan_news.py for:
    Master watchlist: 6:30 AM, 7:30 AM, and 8:06 AM CT, Mon-Fri
    Focus list: 7:15 AM, 10:30 AM, and 3:30 PM CT, Mon-Fri, plus Sunday 6:00 PM CT

Run once (no admin required — creates user-level tasks):
    python C:\\QuantLab\\Data_Lab\\tools\\watchlist_scanner\\setup_scheduler.py
"""

import subprocess
from pathlib import Path

PYTHON_EXE = r'C:\QuantLab\Data_Lab\.venv\Scripts\python.exe'
SCRIPT     = r'C:\QuantLab\Data_Lab\tools\watchlist_scanner\scan_news.py'

# Named tasks — master and focus list scan windows
TASKS = [
    {
        'name': 'QuantLab_News_Flow_0630',
        'time': '06:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
    },
    {
        'name': 'QuantLab_News_Flow_0730',
        'time': '07:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
    },
    {
        'name': 'QuantLab_News_Flow_0806',
        'time': '08:06',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': [],
    },
    {
        'name': 'QuantLab_Focus_News_0715',
        'time': '07:15',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': ['--feed', 'focus', '--skip-tavily'],
    },
    {
        'name': 'QuantLab_Focus_News_1030',
        'time': '10:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': ['--feed', 'focus', '--skip-tavily'],
    },
    {
        'name': 'QuantLab_Focus_News_1530',
        'time': '15:30',
        'days': 'MON,TUE,WED,THU,FRI',
        'args': ['--feed', 'focus', '--skip-tavily'],
    },
    {
        'name': 'QuantLab_Focus_News_SUN_1800',
        'time': '18:00',
        'days': 'SUN',
        'args': ['--feed', 'focus', '--skip-tavily'],
    },
]

# Also clean up the old single-task name if it exists
LEGACY_TASK = 'QuantLab_News_Flow'


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


def create_task(name: str, start_time: str, days: str, python_exe: str, script_args: list[str]) -> subprocess.CompletedProcess:
    arg_str = ' '.join(script_args).strip()
    task_cmd = f'"{python_exe}" "{SCRIPT}"'.strip()
    if arg_str:
        task_cmd = f'{task_cmd} {arg_str}'

    cmd = [
        'schtasks', '/Create',
        '/TN',  name,
        '/TR',  task_cmd,
        '/SC',  'WEEKLY',
        '/D',   days,
        '/ST',  start_time,
        '/F',
    ]
    return subprocess.run(cmd, capture_output=True, text=True)


def verify_task(name: str) -> str:
    result = subprocess.run(
        ['schtasks', '/Query', '/TN', name, '/FO', 'LIST'],
        capture_output=True, text=True
    )
    return result.stdout


def main():
    print('\n-- QuantLab News Flow Scheduler Setup ------------------')
    print(f'   Script:  {SCRIPT}')
    print('   Master:  Mon-Fri @ 6:30 AM / 7:30 AM / 8:06 AM CT')
    print('   Focus:   Mon-Fri @ 7:15 AM / 10:30 AM / 3:30 PM CT')
    print('   Focus:   Sunday @ 6:00 PM CT')
    print('--------------------------------------------------------\n')

    python_exe = check_python_exe()
    print(f'[1] Python executable: {python_exe}\n')

    # Remove legacy single task if it exists
    if delete_task(LEGACY_TASK):
        print(f'[2] Removed legacy task: {LEGACY_TASK}')
    else:
        print(f'[2] No legacy task found ({LEGACY_TASK}) — skipping')

    print()

    # Create the 3 new tasks
    for i, task in enumerate(TASKS, start=3):
        name  = task['name']
        time_ = task['time']
        days_ = task['days']
        args_ = task['args']

        delete_task(name)  # idempotent — remove if exists before recreating

        result = create_task(name, time_, days_, python_exe, args_)
        if result.returncode == 0:
            print(f'[{i}] Created: {name} @ {time_} CT [{days_}]')
        else:
            print(f'[{i}] ERROR creating {name}:')
            print('     stdout:', result.stdout.strip())
            print('     stderr:', result.stderr.strip())
            print()
            continue

        # Show next-run line from task details
        info = verify_task(name)
        for line in info.splitlines():
            if 'Next Run' in line:
                print(f'     {line.strip()}')
        print()

    print('=' * 56)
    print('  Scheduler configured. Manual run commands:')
    print(f'  python {SCRIPT}')
    print(f'  python {SCRIPT} --feed focus --skip-tavily')
    print('=' * 56 + '\n')


if __name__ == '__main__':
    main()
