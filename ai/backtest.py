from typing import List, Dict
from .features import build_dataset
from .model import AdaBoostStumps
import statistics


def _simulate_pnl(preds, closes, horizon: int, threshold: float, risk_per_trade: float, leverage: float) -> Dict:
    balance = 0.0
    pnl_list = []
    trades = 0
    wins = 0
    peak = 0.0
    dd = 0.0
    for i, p in enumerate(preds):
        if p >= threshold:
            if i + horizon >= len(closes):
                break
            ret = (closes[i + horizon] / closes[i]) - 1.0
            trade_pnl = risk_per_trade * leverage * ret
            balance += trade_pnl
            pnl_list.append(trade_pnl)
            trades += 1
            if trade_pnl > 0:
                wins += 1
            peak = max(peak, balance)
            dd = max(dd, peak - balance)
    win_rate = (wins / trades) if trades > 0 else 0.0
    avg = statistics.mean(pnl_list) if pnl_list else 0.0
    std = statistics.pstdev(pnl_list) if len(pnl_list) > 1 else 0.0
    sharpe = (avg / std) * (trades ** 0.5) if std > 0 else 0.0
    return {
        "trades": trades,
        "win_rate": win_rate,
        "total_pnl": balance,
        "max_drawdown": dd,
        "sharpe_like": sharpe,
    }


def backtest_grid(client, symbols: List[str], granularity: str = "15m", window: int = 50, horizon: int = 12, threshold_pct: float = 0.5, score_grid: List[float] = None, risk_grid: List[float] = None, leverage: float = 10.0) -> Dict:
    if score_grid is None:
        score_grid = [0.5, 0.6, 0.7, 0.8]
    if risk_grid is None:
        risk_grid = [2.0, 4.0, 6.0, 8.0, 10.0]

    # Build combined dataset across symbols
    X_all = []
    y_all = []
    closes_all = []
    for sym in symbols:
        candles = client.get_candles(sym, granularity=granularity, limit=max(2000, window + horizon + 200))
        X, y, _ = build_dataset(candles, window=window, horizon=horizon, threshold_pct=threshold_pct)
        closes = [c["close"] for c in candles][window:len(candles) - horizon]
        m = min(len(X), len(closes))
        X_all.extend(X[:m])
        y_all.extend(y[:m])
        closes_all.extend(closes[:m])

    if not X_all:
        raise RuntimeError("No backtest data constructed.")

    # Train a model
    split = int(0.7 * len(X_all))
    X_train, y_train = X_all[:split], y_all[:split]
    X_test, y_test = X_all[split:], y_all[split:]
    closes_test = closes_all[split:]
    model = AdaBoostStumps(n_rounds=60)
    model.fit(X_train, y_train)

    # Predict probabilities on test set
    proba = [model.predict_proba_one(x) for x in X_test]

    # Grid search
    best = None
    results = []
    for thr in score_grid:
        for risk in risk_grid:
            metrics = _simulate_pnl(proba, closes_test, horizon=horizon, threshold=thr, risk_per_trade=risk, leverage=leverage)
            record = {"threshold": thr, "risk_per_trade": risk, **metrics}
            results.append(record)
            if best is None or record["sharpe_like"] > best["sharpe_like"]:
                best = record

    return {"best": best, "results": results}