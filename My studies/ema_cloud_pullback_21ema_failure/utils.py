#!/usr/bin/env python3
"""
Template: Shared utility helpers for a study.
Override or extend per study requirements.
"""
from __future__ import annotations

import pandas as pd
import numpy as np


def safe_divide(a, b, default=0.0):
    """Safe division returning default when divisor is zero or NaN."""
    if b is None or (isinstance(b, float) and np.isnan(b)) or b == 0:
        return default
    return a / b
