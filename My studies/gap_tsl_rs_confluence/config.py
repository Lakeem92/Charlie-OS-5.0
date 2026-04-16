"""
Gap Bias + TSL3 Slope + RS(Z) Confluence Study
Configuration — All parameters locked after design.
"""
from pathlib import Path

# --- TICKER CONFIGURATION ---
# Change TICKER to study any instrument. BENCHMARK is for RS(Z) calculation.
TICKER = "QQQ"                 # Target instrument (change to any ticker)
BENCHMARK = "SPY"              # RS(Z) benchmark (usually SPY)

# --- DATA SOURCES ---
# Daily data: yfinance (free, full history)
# Intraday data: Alpaca API (requires API keys, full 5-min history back to 2016)
# Alpaca keys should be stored in shared/config/keys/live.env

# --- DATA RANGE ---
START_DATE = "2023-01-01"      # 3+ years of intraday context
END_DATE = None                # None = through today

# --- GAP DEFINITIONS ---
# Primary gap band (the specific question being asked)
GAP_DOWN_MIN = -0.90           # Lower bound (more negative = bigger gap)
GAP_DOWN_MAX = -0.70           # Upper bound (less negative = smaller gap)
# Robustness bands (tested separately in variant analysis)
GAP_BANDS = [
    (-0.50, -0.30, "Tiny"),
    (-0.70, -0.50, "Small"),
    (-0.90, -0.70, "Primary"),
    (-1.50, -0.90, "Large"),
    (-3.00, -1.50, "Crash"),
]

# --- TSL3 INDICATOR PARAMETERS ---
# These replicate the ThinkorSwim TrendStrengthNR7 v4.5 indicator in Python.
# DO NOT CHANGE — these match the live indicator exactly.
# NOTE: TSL3 is calculated on BOTH daily and 5-minute charts, but ONLY the
#       5-minute TSL3 slope is used for confluence event detection.
#       Daily TSL3 provides context (prior day's zone) but is not the trigger.
TSL_PC_LOOKBACK = 20           # Price Change lookback
TSL_EMA_LEN = 21              # EMA for slope method
TSL_EMA_SLOPE_SMOOTH = 5      # Smoothing on EMA slope
TSL_MA1_LEN = 20              # Fast MA (EMA)
TSL_MA2_LEN = 50              # Slow MA (SMA)
TSL_ATR_LEN = 14              # ATR normalization period
TSL_NORM_LEN = 100            # Z-score normalization lookback
TSL_Z_CLAMP = 2.5             # Max Z-score before clamping
TSL_Z_TO_UNIT = 2.0           # Divisor to scale Z to [-1, +1]
TSL_SIGNAL_LEN = 9            # Signal line EMA length
TSL_SLOPE_LEN = 5             # Bars for slope calculation
TSL_SLOPE_SMOOTH = 3          # EMA smoothing on slope
TSL_SLOPE_NEUTRAL_THRESHOLD = 0.25  # Threshold for RISING/DROPPING/NEUTRAL

# --- GAP BIAS MODULE PARAMETERS ---
# Replicating the gap bias detection from the indicator
GAP_OPEN_WINDOW_BARS = 4      # How many bars after open to detect gap bias
GAP_MIN_ABS_PCT = 1.0         # Minimum gap % for gap bias module (indicator default)
GAP_VOL_LOOKBACK = 50         # Volume average lookback
GAP_VOL_MULT = 1.5            # Volume impulse multiplier
GAP_TIER_MED = 2.0            # Medium confidence gap threshold
GAP_TIER_HIGH = 4.0           # High confidence gap threshold

# --- RS(Z) PARAMETERS ---
RS_LOOKBACK = 20              # Rolling momentum lookback for RS calculation
RS_ZSCORE_WINDOW = 60         # Z-score normalization window
RS_OVERSOLD_THRESHOLD = -1.0  # Primary filter: RS(Z) ≤ this = "crushed"
# Robustness thresholds
RS_THRESHOLDS = [-0.5, -1.0, -1.5, -2.0]

# --- FORWARD RETURN WINDOWS ---
# What we measure after a confluence event triggers
INTRADAY_RETURNS = ["open_to_close", "open_to_30min", "open_to_60min",
                    "open_to_high", "open_to_low"]
DAILY_RETURNS = [1, 2, 3, 5]  # T+1 through T+5

# --- SLOPE STATE VARIANTS ---
# Primary question: slope RISING at open. But we test all states.
SLOPE_STATES = {
    "RISING": 1,      # Primary hypothesis (reversal setup)
    "NEUTRAL": 0,     # Control — no slope signal
    "DROPPING": -1,   # Counter-hypothesis (continuation)
}

# --- PATHS ---
BASE_DIR = Path(__file__).parent
DATA_RAW = BASE_DIR / "data" / "raw"
DATA_PROC = BASE_DIR / "data" / "processed"
OUTPUTS = BASE_DIR / "outputs"
CHARTS = OUTPUTS / "charts"
TABLES = OUTPUTS / "tables"
REPORTS = OUTPUTS / "reports"

# Create directories on import
for d in [DATA_RAW, DATA_PROC, CHARTS, TABLES, REPORTS]:
    d.mkdir(parents=True, exist_ok=True)
