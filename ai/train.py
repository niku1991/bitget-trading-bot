from typing import List
from .features import build_dataset
from .model import AdaBoostStumps
import os


def train_model(client, symbols: List[str], granularity: str = "15m", window: int = 50, horizon: int = 12, threshold_pct: float = 0.5, model_path: str = "ai_model.json"):
    X_all = []
    y_all = []
    for sym in symbols:
        candles = client.get_candles(sym, granularity=granularity, limit=max(1000, window + horizon + 200))
        X, y, _ = build_dataset(candles, window=window, horizon=horizon, threshold_pct=threshold_pct)
        X_all.extend(X)
        y_all.extend(y)
    if not X_all:
        raise RuntimeError("No training data constructed. Increase lookback or check candles endpoint.")

    model = AdaBoostStumps(n_rounds=60)
    model.fit(X_all, y_all)
    with open(model_path, "w") as f:
        f.write(model.to_json())
    return model_path