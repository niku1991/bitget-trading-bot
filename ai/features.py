import math
from typing import List, Dict, Tuple

# Candle schema: {"ts": int, "open": float, "high": float, "low": float, "close": float, "volume": float}

def _sma(values: List[float], period: int) -> float:
    if len(values) < period or period <= 0:
        return sum(values) / len(values) if values else 0.0
    return sum(values[-period:]) / period


def _ema(values: List[float], period: int) -> float:
    if not values:
        return 0.0
    if period <= 1:
        return values[-1]
    k = 2.0 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def _rsi(values: List[float], period: int = 14) -> float:
    if len(values) < period + 1:
        return 50.0
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        change = values[i] - values[i - 1]
        if change > 0:
            gains += change
        else:
            losses -= change
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100.0 - (100.0 / (1.0 + rs))


def _volatility(values: List[float], period: int) -> float:
    if len(values) < period:
        period = len(values)
    if period <= 1:
        return 0.0
    window = values[-period:]
    mean = sum(window) / period
    var = sum((x - mean) ** 2 for x in window) / period
    return math.sqrt(var) / mean if mean else 0.0


def compute_feature_vector(candles: List[Dict], window: int = 50) -> Tuple[List[float], List[str]]:
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    volumes = [c["volume"] for c in candles]

    if len(closes) < window:
        window = len(closes)
    recent_closes = closes[-window:]
    recent_highs = highs[-window:]
    recent_lows = lows[-window:]
    recent_vols = volumes[-window:]

    sma_10 = _sma(recent_closes, min(10, window))
    sma_20 = _sma(recent_closes, min(20, window))
    ema_10 = _ema(recent_closes[-min(50, window):], min(10, window))
    ema_20 = _ema(recent_closes[-min(50, window):], min(20, window))
    rsi_14 = _rsi(recent_closes, min(14, window - 1) if window > 1 else 14)
    vol_20 = _volatility(recent_closes, min(20, window))

    # Price position inside recent range
    last_close = recent_closes[-1]
    rng_high = max(recent_highs)
    rng_low = min(recent_lows)
    pos = 0.5 if rng_high == rng_low else (last_close - rng_low) / (rng_high - rng_low)

    # Volume stats
    vol_mean = sum(recent_vols) / len(recent_vols) if recent_vols else 0.0
    vol_last = recent_vols[-1] if recent_vols else 0.0
    vol_ratio = (vol_last / vol_mean) if vol_mean else 1.0

    # Simple momentum
    mom_1 = (recent_closes[-1] / recent_closes[-2] - 1.0) if len(recent_closes) >= 2 else 0.0
    mom_5 = (recent_closes[-1] / recent_closes[-min(6, len(recent_closes))] - 1.0) if len(recent_closes) >= 6 else 0.0

    features = [
        last_close,
        sma_10,
        sma_20,
        ema_10,
        ema_20,
        rsi_14,
        vol_20,
        pos,
        vol_ratio,
        mom_1,
        mom_5,
    ]
    names = [
        "last_close",
        "sma_10",
        "sma_20",
        "ema_10",
        "ema_20",
        "rsi_14",
        "vol_20",
        "pos",
        "vol_ratio",
        "mom_1",
        "mom_5",
    ]
    return features, names


def build_dataset(candles: List[Dict], window: int, horizon: int, threshold_pct: float) -> Tuple[List[List[float]], List[int], List[str]]:
    closes = [c["close"] for c in candles]
    X: List[List[float]] = []
    y: List[int] = []
    names: List[str] = []
    n = len(candles)
    if n < window + horizon + 1:
        return X, y, names

    for i in range(window, n - horizon):
        window_candles = candles[:i]
        feats, names = compute_feature_vector(window_candles, window)
        future_ret = (closes[i + horizon] / closes[i] - 1.0)
        label = 1 if future_ret >= (threshold_pct / 100.0) else 0
        X.append(feats)
        y.append(label)
    return X, y, names