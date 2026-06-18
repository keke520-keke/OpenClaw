"""行情 API - 优先数据库，兜底模拟数据"""
import os
from fastapi import APIRouter, Query

from app.services.data_query import (
    query_market_overview,
    query_realtime_quotes,
    query_stock_detail,
    query_stock_kline,
)

USE_MOCK = os.getenv("USE_MOCK", "0") == "1"

if USE_MOCK:
    from app.data_source.mock_data import (
        get_market_overview,
        get_realtime_quotes,
        get_stock_detail,
        get_stock_kline,
    )

router = APIRouter()


def _has_db_data():
    try:
        from app.database import SessionLocal
        from sqlalchemy import func
        from app.models.db_models import DailyKline
        db = SessionLocal()
        count = db.query(func.count(DailyKline.id)).scalar()
        db.close()
        return count and count > 0
    except Exception:
        return False


def _get_market_overview():
    if not USE_MOCK and _has_db_data():
        return query_market_overview()
    from app.data_source.mock_data import get_market_overview as _m
    import asyncio
    return asyncio.run(_m())


def _get_quotes(page, page_size, sort_by):
    if not USE_MOCK and _has_db_data():
        return query_realtime_quotes(page, page_size, sort_by)
    import asyncio
    from app.data_source.mock_data import get_realtime_quotes as _m
    return asyncio.run(_m(page, page_size, sort_by))


def _get_detail(code):
    if not USE_MOCK and _has_db_data():
        return query_stock_detail(code)
    import asyncio
    from app.data_source.mock_data import get_stock_detail as _m
    return asyncio.run(_m(code))


def _get_kline(code, period, start_date, end_date):
    import asyncio
    from app.data_source.mock_data import get_stock_kline as _m
    return asyncio.run(_m(code, period, start_date, end_date))


@router.get("/overview")
async def market_overview():
    data = _get_market_overview()
    return {"code": 0, "data": data}


@router.get("/quotes")
async def realtime_quotes(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    sort_by: str = Query("amount"),
):
    data = _get_quotes(page, page_size, sort_by)
    return {"code": 0, **data}


@router.get("/stock/{code}")
async def stock_detail(code: str):
    data = _get_detail(code)
    if not data:
        return {"code": 404, "msg": "股票不存在"}
    return {"code": 0, "data": data}


@router.get("/kline/{code}")
async def stock_kline(
    code: str,
    period: str = Query("daily"),
    start_date: str = None,
    end_date: str = None,
):
    data = _get_kline(code, period, start_date, end_date)
    return {"code": 0, "data": data}
