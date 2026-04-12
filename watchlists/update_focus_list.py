import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import argparse
import csv
import io
import re
from pathlib import Path


ROOT = Path(r'C:\QuantLab\Data_Lab')
WATCHLISTS_DIR = ROOT / 'watchlists'
OUTPUT_PATH = WATCHLISTS_DIR / 'focus_list.csv'
DOWNLOADS_DIR = Path.home() / 'Downloads'
DEFAULT_PATTERNS = ('Lakeem-Focus_list*.csv', '*Focus_list*.csv')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Normalize a raw focus list export into watchlists/focus_list.csv')
    parser.add_argument('--input', type=Path, help='Path to the raw focus-list CSV export')
    parser.add_argument('--symbols', help='Pasted ticker text, separated by commas, spaces, or new lines')
    parser.add_argument('--stdin', action='store_true', help='Read pasted ticker text from standard input')
    parser.add_argument('--output', type=Path, default=OUTPUT_PATH, help='Canonical output CSV path')
    return parser.parse_args()


def find_latest_download() -> Path:
    matches = []
    for pattern in DEFAULT_PATTERNS:
        matches.extend(DOWNLOADS_DIR.glob(pattern))

    files = [path for path in matches if path.is_file()]
    if not files:
        raise FileNotFoundError(
            f'No focus-list CSV found in {DOWNLOADS_DIR}. '
            'Pass --input with the raw export path.'
        )

    return max(files, key=lambda path: path.stat().st_mtime)


def read_text(path: Path) -> str:
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252'):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError('focus_list', b'', 0, 1, f'Unable to decode {path}')


def extract_csv_block(raw_text: str) -> str:
    lines = raw_text.splitlines()
    start_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped == 'Symbol' or stripped.startswith('Symbol,'):
            start_idx = idx
            break

    if start_idx is None:
        raise ValueError('Could not find a Symbol header in the raw focus-list export.')

    return '\n'.join(lines[start_idx:])


def is_supported_symbol(symbol: str) -> bool:
    if not symbol:
        return False
    if symbol.startswith('/'):
        return False
    allowed = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-')
    return all(char in allowed for char in symbol)


def normalize_symbols(raw_csv: str) -> tuple[list[str], list[str]]:
    reader = csv.DictReader(io.StringIO(raw_csv))
    if not reader.fieldnames or 'Symbol' not in reader.fieldnames:
        raise ValueError('Raw focus-list CSV must contain a Symbol column.')

    seen = set()
    symbols = []
    dropped = []

    for row in reader:
        symbol = (row.get('Symbol') or '').strip().upper()
        if not is_supported_symbol(symbol):
            if symbol:
                dropped.append(symbol)
            continue
        if symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)

    if not symbols:
        raise ValueError('No supported symbols were found in the raw focus-list export.')

    return symbols, dropped


def normalize_symbol_text(raw_text: str) -> tuple[list[str], list[str]]:
    seen = set()
    symbols = []
    dropped = []

    tokens = re.split(r'[\s,;|]+', raw_text)
    for token in tokens:
        symbol = token.strip().upper().strip('"\'')
        if not symbol or symbol == 'SYMBOL':
            continue
        if not is_supported_symbol(symbol):
            dropped.append(symbol)
            continue
        if symbol in seen:
            continue
        seen.add(symbol)
        symbols.append(symbol)

    if not symbols:
        raise ValueError('No supported symbols were found in the pasted ticker text.')

    return symbols, dropped


def resolve_symbols(args: argparse.Namespace) -> tuple[list[str], list[str], str]:
    if args.symbols:
        symbols, dropped = normalize_symbol_text(args.symbols)
        return symbols, dropped, 'inline --symbols text'

    if args.stdin:
        raw_text = sys.stdin.read()
        symbols, dropped = normalize_symbol_text(raw_text)
        return symbols, dropped, 'stdin'

    input_path = args.input or find_latest_download()
    raw_text = read_text(input_path)
    raw_csv = extract_csv_block(raw_text)
    symbols, dropped = normalize_symbols(raw_csv)
    return symbols, dropped, str(input_path)


def write_output(symbols: list[str], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = ['Symbol', *symbols]
    output_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main() -> None:
    args = parse_args()
    symbols, dropped, source = resolve_symbols(args)
    write_output(symbols, args.output)

    print(f'Focus list updated: {args.output}')
    print(f'  Source: {source}')
    print(f'  Symbols kept: {len(symbols)}')
    if dropped:
        print(f'  Dropped unsupported: {", ".join(dropped)}')


if __name__ == '__main__':
    main()