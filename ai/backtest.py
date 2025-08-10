from typing import List, Dict
from .features import build_dataset
from .model import AdaBoostStumps
import statistics


def _simulate_pnl(preds: List[float], closes: List[float], horizon: int, threshold: float,
                  risk_per_trade: float, leverage: float, starting_balance: float,
                  risk_mode: str = 'usd', fee_bps: float = 2.0, slippage_bps: float = 1.0,
                  dd_stop_pct: float = None, max_trades: int = None) -> Dict:
    equity = starting_balance
    balance = 0.0  # cumulative P&L vs starting balance
    equity_curve = [equity]
    pnl_list = []
    trades = 0
    wins = 0
    best_trade = float('-inf')
    worst_trade = float('inf')
    peak_equity = equity
    max_dd_abs = 0.0
    max_dd_pct = 0.0

    fee_rate = fee_bps / 10000.0
    slip_rate = slippage_bps / 10000.0

    for i, p in enumerate(preds):
        if p < threshold:
            continue
        if max_trades is not None and trades >= max_trades:
            break
        if i + horizon >= len(closes):
            break

        entry = closes[i]
        exitp = closes[i + horizon]
        # Apply slippage: buy worse, sell worse
        entry_eff = entry * (1.0 + slip_rate)
        exit_eff = exitp * (1.0 - slip_rate)
        ret = (exit_eff / entry_eff) - 1.0

        # Determine stake (notional) based on risk mode
        if risk_mode == 'pct':
            risk_usd = equity * (risk_per_trade / 100.0)
        else:
            risk_usd = risk_per_trade
        stake_usd = risk_usd * leverage

        # Fees: charged on notional at entry and exit
        fees = stake_usd * fee_rate * 2.0

        trade_pnl = stake_usd * ret - fees
        equity += trade_pnl
        balance = equity - starting_balance
        equity_curve.append(equity)

        pnl_list.append(trade_pnl)
        trades += 1
        if trade_pnl > 0:
            wins += 1
        best_trade = max(best_trade, trade_pnl)
        worst_trade = min(worst_trade, trade_pnl)

        # Drawdown tracking
        peak_equity = max(peak_equity, equity)
        dd_abs = peak_equity - equity
        dd_pct = (dd_abs / peak_equity) if peak_equity > 0 else 0.0
        max_dd_abs = max(max_dd_abs, dd_abs)
        max_dd_pct = max(max_dd_pct, dd_pct)

        if dd_stop_pct is not None and dd_pct * 100.0 >= dd_stop_pct:
            break

    win_rate = (wins / trades) if trades > 0 else 0.0
    avg = statistics.mean(pnl_list) if pnl_list else 0.0
    std = statistics.pstdev(pnl_list) if len(pnl_list) > 1 else 0.0
    sharpe = (avg / std) * (trades ** 0.5) if std > 0 else 0.0

    return {
        "trades": trades,
        "win_rate": win_rate,
        "total_pnl": balance,
        "final_equity": equity,
        "return_pct": ((equity / starting_balance) - 1.0) * 100.0 if starting_balance > 0 else 0.0,
        "max_drawdown": max_dd_abs,
        "max_drawdown_pct": max_dd_pct * 100.0,
        "best_trade": best_trade if trades > 0 else 0.0,
        "worst_trade": worst_trade if trades > 0 else 0.0,
        "sharpe_like": sharpe,
    }


def backtest_grid(client, symbols: List[str], granularity: str = "15m", window: int = 50, horizon: int = 12,
                  threshold_pct: float = 0.5, score_grid: List[float] = None, risk_grid: List[float] = None,
                  leverage: float = 10.0, starting_balance: float = 1000.0, risk_mode: str = 'usd',
                  fee_bps: float = 2.0, slippage_bps: float = 1.0, dd_stop_pct: float = None,
                  max_trades: int = None) -> Dict:
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
            metrics = _simulate_pnl(proba, closes_test, horizon=horizon, threshold=thr,
                                    risk_per_trade=risk, leverage=leverage, starting_balance=starting_balance,
                                    risk_mode=risk_mode, fee_bps=fee_bps, slippage_bps=slippage_bps,
                                    dd_stop_pct=dd_stop_pct, max_trades=max_trades)
            record = {"threshold": thr, "risk_per_trade": risk, "risk_mode": risk_mode,
                      "fee_bps": fee_bps, "slippage_bps": slippage_bps, **metrics}
            results.append(record)
            if best is None or record["sharpe_like"] > best["sharpe_like"]:
                best = record

    return {"best": best, "results": results}