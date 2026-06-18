"""蒙特卡罗模拟 + Walk-forward 验证"""

import numpy as np
import pandas as pd
from typing import Optional


def monte_carlo_simulation(returns: pd.Series, n_simulations: int = 1000,
                           horizon_days: int = 252,
                           initial_capital: float = 1_000_000,
                           method: str = "bootstrap") -> dict:
    """蒙特卡罗模拟

    Args:
        returns: 日收益率序列
        n_simulations: 模拟路径数量
        horizon_days: 预测天数
        method: 'bootstrap'=有放回抽样, 'parametric'=正态拟合
    """
    if len(returns) < 20:
        return {"error": "数据不足"}

    paths = np.zeros((n_simulations, horizon_days + 1))
    paths[:, 0] = initial_capital

    if method == "parametric":
        mu = returns.mean()
        sigma = returns.std()
        for i in range(n_simulations):
            sim_returns = np.random.normal(mu, sigma, horizon_days)
            paths[i, 1:] = initial_capital * np.cumprod(1 + sim_returns)
    else:
        # Bootstrap
        for i in range(n_simulations):
            sim_returns = np.random.choice(returns.dropna().values, horizon_days, replace=True)
            paths[i, 1:] = initial_capital * np.cumprod(1 + sim_returns)

    final_values = paths[:, -1]
    returns_pct = (final_values / initial_capital - 1) * 100

    pct_ranks = [1, 5, 10, 25, 50, 75, 90, 95, 99]
    percentiles = {f"p{p}": round(float(np.percentile(returns_pct, p)), 2) for p in pct_ranks}

    # VaR & CVaR
    var95_mc = np.percentile(returns_pct, 5)
    cvar95_mc = returns_pct[returns_pct <= var95_mc].mean()

    return {
        "n_simulations": n_simulations,
        "horizon_days": horizon_days,
        "initial_capital": initial_capital,
        "mean_return_pct": round(returns_pct.mean(), 2),
        "median_return_pct": round(np.median(returns_pct), 2),
        "std_return_pct": round(returns_pct.std(), 2),
        "min_return_pct": round(returns_pct.min(), 2),
        "max_return_pct": round(returns_pct.max(), 2),
        "var95_pct": round(float(var95_mc), 2),
        "cvar95_pct": round(float(cvar95_mc), 2),
        "prob_positive": round((returns_pct > 0).mean() * 100, 2),
        "percentiles": percentiles,
    }


def walk_forward_validation(signals: pd.DataFrame, prices: pd.DataFrame,
                            train_window: int = 504,   # 2年训练
                            test_window: int = 126,     # 6月测试
                            step_size: int = 63,        # 3个月步进
                            min_train: int = 252) -> dict:
    """Walk-forward 滚动窗口验证

    Returns:
        {folds: [{train_start, train_end, test_start, test_end, metrics}]}
    """
    from app.services.backtester import VectorizedBacktester, BacktestConfig

    dates = sorted(set(signals.index) & set(prices.index))
    if len(dates) < train_window + test_window:
        return {"error": "数据不足"}

    folds = []
    fold_idx = 0

    start = 0
    while start + train_window + test_window <= len(dates):
        train_end = start + train_window
        test_end = min(train_end + test_window, len(dates))
        if test_end - train_end < 21:  # 至少1个月
            break

        train_dates = dates[start:train_end]
        test_dates = dates[train_end:test_end]

        # 在测试集上回测
        test_signals = signals.loc[test_dates]
        test_prices = prices.loc[test_dates]

        bt = VectorizedBacktester()
        result = bt.run(test_signals, test_prices)

        folds.append({
            "fold": fold_idx,
            "train_start": str(train_dates[0]),
            "train_end": str(train_dates[-1]),
            "test_start": str(test_dates[0]),
            "test_end": str(test_dates[-1]),
            "test_days": len(test_dates),
            "metrics": result.metrics if result else {},
        })

        fold_idx += 1
        start += step_size

    if not folds:
        return {"error": "无法创建滚动窗口"}

    # 汇总全部 fold
    sharpe_list = [f["metrics"].get("sharpe_ratio", 0) for f in folds]
    returns_list = [f["metrics"].get("total_return_pct", 0) for f in folds]
    dd_list = [f["metrics"].get("max_drawdown_pct", 0) for f in folds]

    return {
        "n_folds": len(folds),
        "train_window_days": train_window,
        "test_window_days": test_window,
        "step_size_days": step_size,
        "summary": {
            "avg_sharpe": round(np.mean(sharpe_list), 3),
            "std_sharpe": round(np.std(sharpe_list), 3),
            "avg_return_pct": round(np.mean(returns_list), 2),
            "std_return_pct": round(np.std(returns_list), 2),
            "avg_maxdd_pct": round(np.mean(dd_list), 2),
            "sharpe_stability": round(1 - np.std(sharpe_list) / (abs(np.mean(sharpe_list)) + 1e-6), 3),
        },
        "folds": folds,
    }


def stress_test_scenarios(returns: pd.Series, scenarios: dict = None) -> dict:
    """压力测试场景

    Default scenarios:
      - 2008: -50%
      - 2015: -40%
      - 2018: -25%
      - 2020: -30%
      - crash: daily -5% for 5 days
    """
    if scenarios is None:
        scenarios = {
            "2008_crisis": {"shock": -0.50, "days": 60, "desc": "2008年级别"},
            "2015_crash": {"shock": -0.40, "days": 30, "desc": "2015年级别"},
            "2020_covid": {"shock": -0.30, "days": 20, "desc": "2020年级别"},
            "flash_crash": {"daily_shock": -0.05, "days": 5, "desc": "连续暴跌"},
            "rate_hike": {"shock": -0.20, "days": 90, "desc": "加息周期"},
        }

    results = {}
    cum = (1 + returns).cumprod()
    base_return = cum.iloc[-1] - 1

    for name, sc in scenarios.items():
        if "daily_shock" in sc:
            shock_returns = returns.copy()
            shock_returns.iloc[:sc["days"]] += sc["daily_shock"]
        else:
            shock_returns = returns.copy()
            daily_shock = (1 + sc["shock"]) ** (1 / sc["days"]) - 1
            shock_returns.iloc[-sc["days"]:] += daily_shock

        shock_cum = (1 + shock_returns).cumprod()
        shock_return = shock_cum.iloc[-1] - 1

        results[name] = {
            "desc": sc["desc"],
            "base_return_pct": round(base_return * 100, 2),
            "stress_return_pct": round(shock_return * 100, 2),
            "impact_pct": round((shock_return - base_return) * 100, 2),
            "max_drawdown_pct": round((1 - shock_cum / shock_cum.expanding().max()).min() * 100, 2),
        }

    return results
