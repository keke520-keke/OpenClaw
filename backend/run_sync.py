"""数据同步入口"""
import sys
import time
from app.database import SessionLocal, init_db
from app.models.db_models import Stock, DailyKline, Factor, SyncLog
from app.services.data_loader import (
    download_stock_list, import_to_db, download_stock_daily,
    import_kline, calc_factors,
)
import pandas as pd


def cmd_stocks():
    """下载全A股列表"""
    stocks = download_stock_list()
    import_to_db(stocks)
    print(f"DONE: {len(stocks)} stocks imported")


def cmd_kline(code: str, start: str = "20050101"):
    """下载单只股票K线"""
    klines = download_stock_daily(code, start)
    n = import_kline(code, klines)
    if klines:
        df = pd.DataFrame(klines)
        df["date"] = pd.to_datetime(df["date"])
        df = calc_factors(df)
        from app.services.data_loader import import_factors
        nf = import_factors(code, df)
        print(f"DONE: {code} K线={n} 因子={nf}")
    else:
        print(f"DONE: {code} K线=0 (无数据)")


def cmd_batch(start: str = "20200101", limit: int = 50):
    """批量下载核心股票历史数据"""
    init_db()
    db = SessionLocal()
    stocks = db.query(Stock.code, Stock.name).filter(Stock.is_active == True).limit(limit).all()
    db.close()

    print(f"批量下载 {len(stocks)} 只股票，起始 {start}")
    for i, (code, name) in enumerate(stocks):
        print(f"[{i+1}/{len(stocks)}] {code} {name} ...", end=" ")
        try:
            klines = download_stock_daily(code, start)
            n = import_kline(code, klines)
            if klines:
                df = pd.DataFrame(klines)
                df["date"] = pd.to_datetime(df["date"])
                df = calc_factors(df)
                from app.services.data_loader import import_factors
                nf = import_factors(code, df)
                print(f"K={n} F={nf}")
            else:
                print(f"0 records")
        except Exception as e:
            print(f"ERR: {e}")
        time.sleep(0.5)

    print("批量下载完成")


def cmd_dedup():
    """清理重复的K线和因子数据"""
    init_db()
    db = SessionLocal()

    # K线去重：保留每个(code, trade_date)的min(id)
    from sqlalchemy import func
    dup_k = db.query(
        DailyKline.code, DailyKline.trade_date,
        func.min(DailyKline.id).label("keep_id"),
        func.count(DailyKline.id).label("cnt"),
    ).group_by(DailyKline.code, DailyKline.trade_date).having(
        func.count(DailyKline.id) > 1
    ).all()

    k_del = 0
    for code, date, keep_id, cnt in dup_k:
        db.query(DailyKline).filter(
            DailyKline.code == code,
            DailyKline.trade_date == date,
            DailyKline.id != keep_id,
        ).delete(synchronize_session=False)
        k_del += cnt - 1

    # 因子去重
    dup_f = db.query(
        Factor.code, Factor.trade_date,
        func.min(Factor.id).label("keep_id"),
        func.count(Factor.id).label("cnt"),
    ).group_by(Factor.code, Factor.trade_date).having(
        func.count(Factor.id) > 1
    ).all()

    f_del = 0
    for code, date, keep_id, cnt in dup_f:
        db.query(Factor).filter(
            Factor.code == code,
            Factor.trade_date == date,
            Factor.id != keep_id,
        ).delete(synchronize_session=False)
        f_del += cnt - 1

    db.commit()
    db.close()
    print(f"去重完成: K线删除{k_del}条, 因子删除{f_del}条")


def cmd_stats():
    """查看数据库统计"""
    init_db()
    db = SessionLocal()
    from sqlalchemy import func
    stocks = db.query(func.count(Stock.id)).scalar()
    klines = db.query(func.count(DailyKline.id)).scalar()
    factors = db.query(func.count(Factor.id)).scalar()
    kline_stocks = db.query(func.count(func.distinct(DailyKline.code))).scalar()
    latest = db.query(func.max(DailyKline.trade_date)).scalar()
    db.close()
    print(f"""数据库统计:
  股票: {stocks} 只
  K线: {klines} 条 ({kline_stocks} 只有数据)
  因子: {factors} 条
  最新: {latest}
""")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "--help"
    start = "20200101"
    for a in sys.argv:
        if a.startswith("--start="):
            start = a.split("=")[1]

    if cmd == "--stocks":
        cmd_stocks()
    elif cmd == "--kline":
        code = sys.argv[2] if len(sys.argv) > 2 else "600519"
        cmd_kline(code, start)
    elif cmd == "--batch":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 50
        cmd_batch(start, limit)
    elif cmd == "--dedup":
        cmd_dedup()
    elif cmd == "--stats":
        cmd_stats()
    else:
        print("""OpenClaw 数据管理:
  python run_sync.py --stocks              # 更新股票列表
  python run_sync.py --kline 600519        # 下载单只K线
  python run_sync.py --batch 50            # 批量下载50只
  python run_sync.py --batch 50 --start=20050101  # 19年全量
  python run_sync.py --dedup               # 清理重复数据
  python run_sync.py --stats               # 数据库统计
""")

if __name__ == "__main__":
    main()
