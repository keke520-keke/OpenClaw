"""AI 预测 API"""
import numpy as np
import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.ai_engine import get_engine, AIModelEnsemble
from app.services.rebalancer import MonthlyRebalancer, Portfolio, backtest_monthly

router = APIRouter()


@router.get("/status")
async def ai_status():
    """AI引擎状态"""
    engine = get_engine()
    return {
        "code": 0,
        "trained": engine.ensemble.trained,
        "last_trained": str(engine.last_trained) if engine.last_trained else None,
        "models": list(engine.ensemble.models.keys()),
        "features": len(engine.ensemble.feature_names),
    }


class TrainRequest(BaseModel):
    factor_data: list[dict]     # [{date, f1, f2, ...}]
    forward_returns: list[dict]  # [{date, return}]
    lookback: int = 20


@router.post("/train")
async def train_model(req: TrainRequest):
    """训练AI模型"""
    factor_df = pd.DataFrame(req.factor_data)
    if "date" in factor_df.columns:
        factor_df["date"] = pd.to_datetime(factor_df["date"])
        factor_df.set_index("date", inplace=True)

    ret_df = pd.DataFrame(req.forward_returns)
    if "date" in ret_df.columns:
        ret_df["date"] = pd.to_datetime(ret_df["date"])
        ret_df.set_index("date", inplace=True)
    forward_ret = ret_df.iloc[:, 0]

    engine = get_engine()
    engine.train(factor_df, forward_ret)
    imp = engine.ensemble.feature_importance()

    return {
        "code": 0,
        "samples": len(factor_df),
        "features": len(engine.ensemble.feature_names),
        "top_features": imp[:10],
    }


class PredictRequest(BaseModel):
    factor_data: list[dict]


@router.post("/predict")
async def predict(req: PredictRequest):
    """生成交易信号"""
    factor_df = pd.DataFrame(req.factor_data)
    if "date" in factor_df.columns:
        factor_df["date"] = pd.to_datetime(factor_df["date"])
        factor_df.set_index("date", inplace=True)

    engine = get_engine()
    signals, importance = engine.generate_signals(factor_df)

    records = []
    for idx, row in signals.iterrows():
        records.append({
            "date": str(idx),
            "signal": row["signal"],
            "score": round(row["score"], 4),
            "confidence": round(row["confidence"], 4),
            "agreement": round(row["agreement"], 4),
        })

    return {"code": 0, "signals": records, "top_features": importance[:10]}


class BacktestRequest(BaseModel):
    signals: list[dict]        # [{date, code, signal, score, confidence}]
    prices: list[dict]         # [{date, code, price}]
    initial_capital: float = 1_000_000
    max_stocks: int = 8


@router.post("/backtest")
async def run_backtest(req: BacktestRequest):
    """运行月度再平衡回测"""
    # 构造信号矩阵
    sig_records = {}
    for s in req.signals:
        date = s["date"]
        code = s["code"]
        if date not in sig_records:
            sig_records[date] = {}
        sig_records[date][code] = s

    price_records = {}
    for p in req.prices:
        date = p["date"]
        code = p["code"]
        if date not in price_records:
            price_records[date] = {}
        price_records[date][code] = p["price"]

    signals_df = pd.DataFrame(sig_records).T
    price_df = pd.DataFrame(price_records).T
    price_df.index = pd.to_datetime(price_df.index)

    result = backtest_monthly(signals_df, price_df, req.initial_capital, req.max_stocks)
    return {"code": 0, **result}


@router.get("/rebalance-stats")
async def rebalance_stats():
    """再平衡策略参数"""
    return {
        "code": 0,
        "strategy": "月度再平衡",
        "max_stocks": 8,
        "max_single_weight": "20%",
        "turnover_limit": "30%",
        "commission": "0.15%",
        "rebalance_day": "每月第一个交易日",
    }
