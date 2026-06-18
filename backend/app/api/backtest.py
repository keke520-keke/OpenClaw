"""回测 API"""
import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.backtester import VectorizedBacktester, BacktestConfig, compare_strategies
from app.services.monte_carlo import monte_carlo_simulation, walk_forward_validation, stress_test_scenarios

router = APIRouter()


class BacktestRequest(BaseModel):
    signals: list[dict]         # [{date, code, weight}]
    prices: list[dict]          # [{date, code, price}]
    benchmark: Optional[list[dict]] = None  # [{date, value}]
    config: Optional[dict] = None  # BacktestConfig overrides


@router.post("/run")
async def run_backtest(req: BacktestRequest):
    """运行回测"""
    # 构建信号矩阵
    sig_data = {}
    for s in req.signals:
        date = s["date"]
        if date not in sig_data:
            sig_data[date] = {}
        sig_data[date][s["code"]] = s.get("weight", s.get("score", 0))

    signals = pd.DataFrame(sig_data).T.sort_index()
    signals.index = pd.to_datetime(signals.index)

    # 构建价格矩阵
    price_data = {}
    for p in req.prices:
        date = p["date"]
        if date not in price_data:
            price_data[date] = {}
        price_data[date][p["code"]] = p["price"]
    prices = pd.DataFrame(price_data).T.sort_index()
    prices.index = pd.to_datetime(prices.index)

    # 基准
    benchmark = None
    if req.benchmark:
        bm = pd.DataFrame(req.benchmark)
        bm["date"] = pd.to_datetime(bm["date"])
        bm.set_index("date", inplace=True)
        benchmark = bm.iloc[:, 0]

    # 配置
    config = BacktestConfig()
    if req.config:
        for k, v in req.config.items():
            if hasattr(config, k):
                setattr(config, k, v)

    bt = VectorizedBacktester(config)
    result = bt.run(signals, prices, benchmark)

    if not result:
        return {"code": 500, "msg": "回测数据不足"}

    return {"code": 0, **result.summary(), "metrics_detail": result.metrics}


class MCRequest(BaseModel):
    returns: list[float]
    n_simulations: int = 1000
    horizon_days: int = 252
    method: str = "bootstrap"


@router.post("/monte-carlo")
async def run_monte_carlo(req: MCRequest):
    """蒙特卡罗模拟"""
    ret = pd.Series(req.returns)
    result = monte_carlo_simulation(
        ret, req.n_simulations, req.horizon_days, method=req.method
    )
    return {"code": 0, **result}


class WalkForwardRequest(BaseModel):
    signals: list[dict]
    prices: list[dict]
    train_window: int = 504
    test_window: int = 126
    step_size: int = 63


@router.post("/walk-forward")
async def run_walk_forward(req: WalkForwardRequest):
    """Walk-forward 滚动验证"""
    sig_data = {s["date"]: {} for s in req.signals}
    for s in req.signals:
        if s["date"] not in sig_data:
            sig_data[s["date"]] = {}
        sig_data[s["date"]][s["code"]] = s.get("weight", s.get("score", 0))

    signals = pd.DataFrame(sig_data).T.sort_index()
    signals.index = pd.to_datetime(signals.index)

    price_data = {p["date"]: {} for p in req.prices}
    for p in req.prices:
        if p["date"] not in price_data:
            price_data[p["date"]] = {}
        price_data[p["date"]][p["code"]] = p["price"]
    prices = pd.DataFrame(price_data).T.sort_index()
    prices.index = pd.to_datetime(prices.index)

    result = walk_forward_validation(signals, prices, req.train_window, req.test_window, req.step_size)
    return {"code": 0, **result}


class StressRequest(BaseModel):
    returns: list[float]
    scenarios: Optional[dict] = None


@router.post("/stress-test")
async def run_stress_test(req: StressRequest):
    """压力测试"""
    ret = pd.Series(req.returns)
    result = stress_test_scenarios(ret, req.scenarios)
    return {"code": 0, "scenarios": result}


@router.get("/config-defaults")
async def default_config():
    """回测默认配置"""
    c = BacktestConfig()
    return {
        "code": 0,
        "config": {
            "initial_capital": c.initial_capital,
            "commission_rate": c.commission_rate,
            "stamp_duty": c.stamp_duty,
            "slippage": c.slippage,
            "max_position_pct": c.max_position_pct,
            "max_positions": c.max_positions,
            "stop_loss": c.stop_loss,
            "take_profit": c.take_profit,
            "max_drawdown_limit": c.max_drawdown_limit,
            "rebalance_freq": c.rebalance_freq,
        },
    }
