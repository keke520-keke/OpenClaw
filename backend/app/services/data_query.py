"""数据库查询服务"""
from datetime import datetime, timedelta
from sqlalchemy import func, desc, text
from app.database import SessionLocal
from app.models.db_models import Stock, DailyKline, Factor, IndexDaily


def query_stocks(page: int = 1, page_size: int = 50):
    """分页查询股票列表"""
    db = SessionLocal()
    try:
        total = db.query(Stock).filter(Stock.is_active == True).count()
        rows = db.query(Stock).filter(Stock.is_active == True).offset(
            (page - 1) * page_size).limit(page_size).all()
        return {
            "total": total, "page": page, "page_size": page_size,
            "data": [{"code": r.code, "name": r.name, "market": r.market} for r in rows],
        }
    finally:
        db.close()


def query_market_overview():
    """大盘指数概览（取最近一天）"""
    db = SessionLocal()
    try:
        indices = ["1.000001", "0.399001", "0.399006", "1.000688"]
        names = {"1.000001": "上证指数", "0.399001": "深证成指",
                 "0.399006": "创业板指", "1.000688": "科创50"}
        result = []
        for code in indices:
            row = db.query(IndexDaily).filter(
                IndexDaily.code == code
            ).order_by(desc(IndexDaily.trade_date)).first()
            if row:
                result.append({
                    "name": names.get(code, code), "code": code,
                    "price": row.close, "change_pct": row.change_pct,
                    "change_amt": row.close - row.open,
                    "amount": row.amount,
                })
        return result
    finally:
        db.close()


def query_realtime_quotes(page: int = 1, page_size: int = 50, sort_by: str = "amount") -> dict:
    """从K线表取最新日数据作为实时行情"""
    db = SessionLocal()
    try:
        latest_date = db.query(func.max(DailyKline.trade_date)).scalar()
        if not latest_date:
            return {"total": 0, "page": page, "page_size": page_size, "data": []}

        sort_col = {
            "amount": DailyKline.amount,
            "change_pct": DailyKline.change_pct,
            "volume": DailyKline.volume,
            "turnover_rate": DailyKline.turnover_rate,
        }.get(sort_by, DailyKline.amount)

        sub = db.query(DailyKline.code, DailyKline.trade_date).filter(
            DailyKline.trade_date == latest_date
        ).subquery()

        base_q = db.query(DailyKline, Stock.name).join(
            Stock, DailyKline.code == Stock.code
        ).filter(DailyKline.trade_date == latest_date)

        total = base_q.count()

        rows = base_q.order_by(desc(sort_col)).offset(
            (page - 1) * page_size).limit(page_size).all()

        data = []
        for k, name in rows:
            data.append({
                "code": k.code, "name": name,
                "price": k.close, "open": k.open,
                "high": k.high, "low": k.low,
                "change_pct": k.change_pct, "change_amt": k.change_amt,
                "volume": k.volume, "amount": k.amount,
                "amplitude": k.amplitude, "turnover_rate": k.turnover_rate,
                "pre_close": k.close - k.change_amt if k.change_amt else k.close,
            })
        return {"total": total, "page": page, "page_size": page_size, "data": data}
    finally:
        db.close()


def query_stock_detail(code: str):
    """个股详情（最近日K线 + 最新因子）"""
    db = SessionLocal()
    try:
        k = db.query(DailyKline).filter(DailyKline.code == code).order_by(
            desc(DailyKline.trade_date)).first()
        s = db.query(Stock).filter(Stock.code == code).first()
        f = db.query(Factor).filter(Factor.code == code).order_by(
            desc(Factor.trade_date)).first()

        if not k or not s:
            return None

        result = {
            "code": code, "name": s.name,
            "price": k.close, "open": k.open,
            "high": k.high, "low": k.low,
            "change_pct": k.change_pct, "change_amt": k.change_amt,
            "volume": k.volume, "amount": k.amount,
            "amplitude": k.amplitude, "turnover_rate": k.turnover_rate,
            "pre_close": k.close - (k.change_amt or 0),
        }
        if f:
            result.update({
                "pe_ratio": f.pe_ratio, "pb_ratio": f.pb_ratio,
                "total_mv": f.total_mv, "circ_mv": f.circ_mv,
                "ma5": f.ma5, "ma10": f.ma10, "ma20": f.ma20,
                "rsi": f.rsi, "kdj_k": f.k, "kdj_d": f.d, "kdj_j": f.j,
            })
        return result
    finally:
        db.close()


def query_stock_kline(code: str, days: int = 60):
    """个股近期K线"""
    db = SessionLocal()
    try:
        rows = db.query(DailyKline).filter(
            DailyKline.code == code
        ).order_by(desc(DailyKline.trade_date)).limit(days).all()
        return [{
            "date": str(r.trade_date),
            "open": r.open, "close": r.close,
            "high": r.high, "low": r.low,
            "volume": r.volume, "amount": r.amount,
            "change_pct": r.change_pct, "amplitude": r.amplitude,
            "turnover_rate": r.turnover_rate,
        } for r in reversed(rows)]
    finally:
        db.close()
