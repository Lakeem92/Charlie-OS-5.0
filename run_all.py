"""
QuantLab — Run All Collectors
Runs every data collector in sequence, reports pass/fail.
"""
import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

import time
import traceback
import importlib.util
from datetime import datetime

COLLECTORS = [
    ('🌍 Macro',       'data_collectors.macro_collector'),
    ('📊 ETF',         'data_collectors.etf_collector'),
    ('🛢️ Commodities', 'data_collectors.commodity_collector'),
    ('⚡ Catalysts',   'data_collectors.catalyst_collector'),
    ('🎯 Focus List',  'data_collectors.focus_list_collector'),
    ('🧠 AI Cascade',  'data_collectors.ai_cascade_collector'),
    ('📰 News',        'data_collectors.news_collector'),
]


def main():
    print()
    print("═" * 60)
    print(f"  🚀 QuantLab — Run All Collectors")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S CT')}")
    print("═" * 60)

    results = []
    total_start = time.time()

    for name, module_path in COLLECTORS:
        print(f"\n{'─' * 50}")
        print(f"  ▶ {name}")
        print(f"{'─' * 50}")

        start = time.time()
        try:
            if importlib.util.find_spec(module_path) is None:
                elapsed = time.time() - start
                results.append((name, '⏭️', f'module missing ({elapsed:.1f}s)'))
                print(f"  ⏭️ SKIPPED: {module_path} not present in this workspace")
                continue
            mod = __import__(module_path, fromlist=['collect'])
            if hasattr(mod, 'main'):
                mod.main()
            elif hasattr(mod, 'collect'):
                mod.collect()
            else:
                raise AttributeError(f'{module_path} has neither main() nor collect()')
            elapsed = time.time() - start
            results.append((name, '✅', f'{elapsed:.1f}s'))
        except Exception as e:
            elapsed = time.time() - start
            results.append((name, '❌', str(e)[:80]))
            print(f"  ❌ FAILED: {e}")
            traceback.print_exc()

    total_elapsed = time.time() - total_start

    print()
    print("═" * 60)
    print(f"  📋 SUMMARY — {total_elapsed:.1f}s total")
    print("─" * 60)

    for name, status, detail in results:
        print(f"  {status} {name:<22} {detail}")

    passed = sum(1 for _, s, _ in results if s == '✅')
    failed = sum(1 for _, s, _ in results if s == '❌')
    skipped = sum(1 for _, s, _ in results if s == '⏭️')

    print("─" * 60)
    if failed == 0:
        if skipped == 0:
            print(f"  🎯 ALL {passed} COLLECTORS PASSED")
        else:
            print(f"  🎯 {passed} passed, {skipped} skipped, 0 failed")
    else:
        print(f"  ⚠️  {passed} passed, {skipped} skipped, {failed} failed")
    print("═" * 60)
    print()


if __name__ == '__main__':
    main()
