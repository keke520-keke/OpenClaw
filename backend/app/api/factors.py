"""因子 API"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional

from app.services.factor_engine import (
    FACTOR_REGISTRY, get_factor_list, calc_all_technical, calc_factor_batch,
)

router = APIRouter()


@router.get("/list")
async def list_factors(category: str = Query(None, description="分类筛选: 技术/财务/另类")):
    """获取所有因子列表"""
    data = get_factor_list(category)
    return {"code": 0, "total": len(data), "data": data}


@router.get("/categories")
async def list_categories():
    """因子分类统计"""
    cats = {}
    for v in FACTOR_REGISTRY.values():
        c = v["category"]
        cats[c] = cats.get(c, 0) + 1
    return {"code": 0, "data": cats, "total": len(FACTOR_REGISTRY)}


class CalcRequest(BaseModel):
    factors: list[str]  # 需要的因子名列表
    data: list[dict]    # K线数据 [{date, open, high, low, close, volume, amount, amplitude, change_pct, turnover_rate}]


@router.post("/compute")
async def compute_factors(req: CalcRequest):
    """计算指定因子"""
    import pandas as pd
    df = pd.DataFrame(req.data)
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

    result = calc_factor_batch(df, req.factors)
    result = result.fillna(0)

    # 转换为可序列化格式
    records = []
    for idx, row in result.iterrows():
        r = {"date": str(idx)}
        for col in result.columns:
            r[col] = round(float(row[col]), 6) if row[col] != 0 else 0
        records.append(r)
    return {"code": 0, "factors": req.factors, "count": len(records), "data": records}


@router.get("/top")
async def top_factors(category: str = Query("技术"), limit: int = Query(20)):
    """获取最重要的因子（按分类）"""
    data = get_factor_list(category)
    return {"code": 0, "data": data[:limit]}
