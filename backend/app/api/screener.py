"""选股器 API"""
from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Optional
from app.services.screener_engine import run_screening, get_presets

router = APIRouter()


class ScreenFilters(BaseModel):
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    change_pct_min: Optional[float] = None
    change_pct_max: Optional[float] = None
    turnover_min: Optional[float] = None
    turnover_max: Optional[float] = None
    pe_min: Optional[float] = None
    pe_max: Optional[float] = None
    volume_ratio_min: Optional[float] = None
    amount_min: Optional[float] = None


@router.get("/presets")
async def list_presets():
    """预设选股策略列表"""
    data = await get_presets()
    return {"code": 0, "data": data}


@router.get("/run")
async def screen_by_preset(
    preset: str = Query(..., description="预设策略key"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
):
    """使用预设策略选股"""
    result = await run_screening(preset=preset, page=page, page_size=page_size)
    return {"code": 0, "preset": preset, **result}


@router.post("/custom")
async def screen_custom(filters: ScreenFilters, page: int = 1, page_size: int = 30):
    """自定义条件选股"""
    f = filters.model_dump(exclude_none=True)
    result = await run_screening(filters=f, page=page, page_size=page_size)
    return {"code": 0, **result}
