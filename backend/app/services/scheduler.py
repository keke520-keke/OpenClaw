"""定时任务调度"""
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.services.data_loader import download_stock_daily, import_kline, download_stock_list, import_to_db
from app.database import SessionLocal
from app.models.db_models import SyncLog

scheduler = BackgroundScheduler(timezone="Asia/Shanghai")


def daily_update():
    """每日增量更新：新K线+新因子"""
    task_id = _start_log("daily_update")
    try:
        db = SessionLocal()
        stocks = db.execute("SELECT code FROM stocks WHERE is_active=1").fetchall()
        db.close()

        total = 0
        today = datetime.now().strftime("%Y%m%d")
        yesterday = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

        for (code,) in stocks[:50]:
            klines = download_stock_daily(code, yesterday)
            n = import_kline(code, klines)
            total += n

        _end_log(task_id, "success", total)
        logger.info(f"每日增量完成: {total} 条")
    except Exception as e:
        _end_log(task_id, "failed", 0, str(e))
        logger.error(f"每日增量失败: {e}")


def weekly_stock_list_update():
    """每周更新股票列表（新股上市等）"""
    task_id = _start_log("weekly_stock_update")
    try:
        stocks = download_stock_list()
        import_to_db(stocks)
        _end_log(task_id, "success", len(stocks))
    except Exception as e:
        _end_log(task_id, "failed", 0, str(e))


def _start_log(task_name: str) -> int:
    db = SessionLocal()
    log = SyncLog(task_name=task_name, status="running")
    db.add(log)
    db.commit()
    log_id = log.id
    db.close()
    return log_id


def _end_log(log_id: int, status: str, total: int, error: str = None):
    db = SessionLocal()
    log = db.query(SyncLog).filter(SyncLog.id == log_id).first()
    if log:
        log.status = status
        log.end_time = datetime.utcnow()
        log.total_records = total
        log.error_msg = error
        db.commit()
    db.close()


def start_scheduler():
    """启动定时任务"""
    # 每个交易日下午4点运行增量更新
    scheduler.add_job(
        daily_update,
        CronTrigger(day_of_week="mon-fri", hour=16, minute=0),
        id="daily_update",
        name="日K线增量更新",
    )
    # 每周一更新股票列表
    scheduler.add_job(
        weekly_stock_list_update,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="weekly_stock_update",
        name="股票列表周更新",
    )
    scheduler.start()
    logger.info("定时任务调度器已启动")


def stop_scheduler():
    scheduler.shutdown(wait=False)
