"""
Regime Composite Score — Run Study
Orchestrates data collection and analysis in sequence.
"""

import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from pathlib import Path
import importlib

STUDY_DIR = Path(__file__).resolve().parent

def main():
    print('╔' + '═' * 58 + '╗')
    print('║   REGIME COMPOSITE SCORE — FULL STUDY RUN              ║')
    print('╚' + '═' * 58 + '╝')
    print()

    # Phase 1: Data collection
    print('── PHASE 1: DATA COLLECTION ──')
    collect = importlib.import_module('collect_data')
    collect.main()
    print()

    # Phase 2: Analysis
    print('── PHASE 2: ANALYSIS ──')
    analyze = importlib.import_module('analyze')
    analyze.main()

    print()
    print('╔' + '═' * 58 + '╗')
    print('║   STUDY COMPLETE                                       ║')
    print('╚' + '═' * 58 + '╝')


if __name__ == '__main__':
    # Ensure cwd is study dir for relative imports
    import os
    os.chdir(STUDY_DIR)
    sys.path.insert(0, str(STUDY_DIR))
    main()
