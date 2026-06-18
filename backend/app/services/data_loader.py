"""历史数据下载器 - 从东方财富下载19年A股历史数据"""
import json
import time
import urllib.request
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
from loguru import logger

from app.database import SessionLocal, init_db
from app.models.db_models import Stock, DailyKline, Factor, IndexDaily, SyncLog

EM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


def _em_fetch(url: str, timeout: int = 15, retries: int = 3) -> Optional[dict]:
    """从东方财富获取JSON数据，带重试"""
    req = urllib.request.Request(url, headers=EM_HEADERS)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"请求失败 ({attempt+1}/{retries}): {url[:100]} - {e}")
                return None
            time.sleep(1)
    return None


def download_stock_list() -> list[dict]:
    """下载全A股股票列表"""
    logger.info("下载全A股股票列表...")
    stocks = []
    for page in range(1, 30):
        # m:0+t:6(深A) m:0+t:80(北A) m:1+t:2(沪A) m:1+t:23(科创)
        url = (f"https://push2.eastmoney.com/api/qt/clist/get"
               f"?pn={page}&pz=500&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
               f"&fltt=2&invt=2&fid=f12&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
               f"&fields=f12,f14")
        data = _em_fetch(url)
        if not data:
            break
        items = data.get("data", {}).get("diff", [])
        if not items:
            break
        for it in items:
            stocks.append({
                "code": str(it.get("f12", "")),
                "name": str(it.get("f14", "")),
                "market": "sh" if str(it.get("f12", "")).startswith("6") else "sz",
            })
    logger.info(f"获取到 {len(stocks)} 只股票")
    return stocks


def download_index_daily(index_code: str, start_date: str = "20050101") -> list[dict]:
    """下载指数日线数据"""
    market_code = "1" if index_code.startswith("000") else "0"
    secid = f"{market_code}.{index_code}"

    result = []
    page = 1
    while True:
        url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={secid}&klt=101&fqt=1"
               f"&beg={start_date}&end={datetime.now().strftime('%Y%m%d')}"
               f"&fields1=f1,f2,f3,f4,f5,f6"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58"
               f"&lmt=200&page={page}&ut=bd1d9ddb04089700cf9c27f6f7426281")
        data = _em_fetch(url, timeout=20)
        if not data:
            break
        klines = data.get("data", {}).get("klines", [])
        if not klines:
            break
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 8:
                result.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": float(parts[5]),
                    "amount": float(parts[6]),
                    "change_pct": float(parts[7]) if len(parts) > 7 else 0,
                })
        page += 1
        if page % 5 == 0:
            time.sleep(0.5)
    logger.info(f"指数 {index_code} 下载 {len(result)} 条日线")
    return result


def download_stock_daily(code: str, start_date: str = "20050101") -> list[dict]:
    """下载个股日线数据（含后复权因子）"""
    market = "1" if code.startswith("6") else "0"
    secid = f"{market}.{code}"

    result = []
    page = 1
    while True:
        url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
               f"?secid={secid}&klt=101&fqt=1"
               f"&beg={start_date}&end={datetime.now().strftime('%Y%m%d')}"
               f"&fields1=f1,f2,f3,f4,f5,f6"
               f"&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61"
               f"&lmt=200&page={page}&ut=bd1d9ddb04089700cf9c27f6f7426281")
        data = _em_fetch(url, timeout=20)
        if not data:
            break
        klines = data.get("data", {}).get("klines", [])
        if not klines:
            break
        for line in klines:
            parts = line.split(",")
            if len(parts) >= 11:
                result.append({
                    "date": parts[0],
                    "open": float(parts[1]),
                    "close": float(parts[2]),
                    "high": float(parts[3]),
                    "low": float(parts[4]),
                    "volume": float(parts[5]),
                    "amount": float(parts[6]),
                    "amplitude": float(parts[7]) if parts[7] != "-" else 0,
                    "change_pct": float(parts[8]) if parts[8] != "-" else 0,
                    "change_amt": float(parts[9]) if parts[9] != "-" else 0,
                    "turnover_rate": float(parts[10]) if parts[10] != "-" else 0,
                })
        page += 1
        time.sleep(0.3)
    return result


def calc_factors(kline_df: pd.DataFrame) -> pd.DataFrame:
    """从K线计算技术因子"""
    df = kline_df.copy()
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    df["ma5"] = close.rolling(5).mean()
    df["ma10"] = close.rolling(10).mean()
    df["ma20"] = close.rolling(20).mean()
    df["ma60"] = close.rolling(60).mean()

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    df["dif"] = ema12 - ema26
    df["dea"] = df["dif"].ewm(span=9, adjust=False).mean()
    df["macd"] = (df["dif"] - df["dea"]) * 2

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))

    low_min = low.rolling(9).min()
    high_max = high.rolling(9).max()
    rsv = ((close - low_min) / (high_max - low_min).replace(0, float("nan"))) * 100
    df["k"] = rsv.ewm(com=2, adjust=False).mean()
    df["d"] = df["k"].ewm(com=2, adjust=False).mean()
    df["j"] = 3 * df["k"] - 2 * df["d"]

    df["boll_mid"] = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    df["boll_upper"] = df["boll_mid"] + 2 * std20
    df["boll_lower"] = df["boll_mid"] - 2 * std20

    df["vol_ma5"] = volume.rolling(5).mean()
    df["vol_ma20"] = volume.rolling(20).mean()
    df["vol_ratio"] = volume / df["vol_ma20"].replace(0, float("nan"))

    return df


def import_to_db(stocks: list[dict]):
    """将股票列表写入数据库"""
    db = SessionLocal()
    try:
        for s in stocks:
            existing = db.query(Stock).filter(Stock.code == s["code"]).first()
            if not existing:
                db.add(Stock(code=s["code"], name=s["name"], market=s["market"]))
        db.commit()
        logger.info(f"股票列表入库: {len(stocks)} 只")
    except Exception as e:
        db.rollback()
        logger.error(f"股票列表入库失败: {e}")
    finally:
        db.close()


def import_kline(code: str, klines: list[dict]):
    """将K线数据写入数据库"""
    if not klines:
        return 0
    db = SessionLocal()
    count = 0
    try:
        for k in klines:
            trade_date = datetime.strptime(k["date"], "%Y-%m-%d").date()
            existing = db.query(DailyKline).filter(
                DailyKline.code == code,
                DailyKline.trade_date == trade_date,
            ).first()
            if not existing:
                db.add(DailyKline(
                    code=code, trade_date=trade_date,
                    open=k.get("open"), high=k.get("high"),
                    low=k.get("low"), close=k.get("close"),
                    volume=int(k.get("volume", 0)),
                    amount=k.get("amount"),
                    amplitude=k.get("amplitude"),
                    change_pct=k.get("change_pct"),
                    change_amt=k.get("change_amt"),
                    turnover_rate=k.get("turnover_rate"),
                ))
                count += 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"K线入库失败 {code}: {e}")
    finally:
        db.close()
    return count


def import_factors(code: str, factor_df: pd.DataFrame):
    """将因子数据写入数据库"""
    if factor_df.empty:
        return 0
    db = SessionLocal()
    count = 0
    try:
        for _, row in factor_df.iterrows():
            if pd.isna(row.get("date")):
                continue
            trade_date = row["date"] if isinstance(row["date"], datetime) else datetime.strptime(str(row["date"]), "%Y-%m-%d")
            if isinstance(trade_date, datetime):
                trade_date = trade_date.date()

            existing = db.query(Factor).filter(
                Factor.code == code, Factor.trade_date == trade_date
            ).first()
            if not existing:
                db.add(Factor(
                    code=code, trade_date=trade_date,
                    ma5=row.get("ma5"), ma10=row.get("ma10"),
                    ma20=row.get("ma20"), ma60=row.get("ma60"),
                    dif=row.get("dif"), dea=row.get("dea"), macd=row.get("macd"),
                    rsi=row.get("rsi"), k=row.get("k"), d=row.get("d"), j=row.get("j"),
                    boll_upper=row.get("boll_upper"),
                    boll_mid=row.get("boll_mid"),
                    boll_lower=row.get("boll_lower"),
                    vol_ratio=row.get("vol_ratio"),
                ))
                count += 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"因子入库失败 {code}: {e}")
    finally:
        db.close()
    return count


def run_full_sync(start_date: str = "20050101"):
    """运行全量数据同步"""
    init_db()
    logger.info("===== 开始全量数据同步 =====")

    # 1. 下载股票列表
    stocks = download_stock_list()
    import_to_db(stocks)

    # 2. 下载指数日线
    logger.info("下载指数日线...")
    for idx_code in ["000001", "399001", "399006", "000688"]:
        index_data = download_index_daily(idx_code, start_date)
        db = SessionLocal()
        count = 0
        for k in index_data:
            td = datetime.strptime(k["date"], "%Y-%m-%d").date()
            existing = db.query(IndexDaily).filter(
                IndexDaily.code == idx_code, IndexDaily.trade_date == td
            ).first()
            if not existing:
                db.add(IndexDaily(
                    code=idx_code, trade_date=td,
                    open=k["open"], high=k["high"], low=k["low"], close=k["close"],
                    volume=int(k.get("volume", 0)), amount=k.get("amount"),
                    change_pct=k.get("change_pct", 0),
                ))
                count += 1
        db.commit()
        db.close()
        logger.info(f"  指数 {idx_code}: {count} 条新增")

    # 3. 下载个股K线 + 计算因子（只下载前20只做演示）
    logger.info("下载个股K线...")
    for i, s in enumerate(stocks[:20]):
        logger.info(f"  [{i+1}/20] {s['code']} {s['name']}")
        klines = download_stock_daily(s["code"], start_date)
        n = import_kline(s["code"], klines)
        if klines:
            df = pd.DataFrame(klines)
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
            factor_df = calc_factors(df)
            factor_df = factor_df.reset_index()
            nf = import_factors(s["code"], factor_df)
            logger.info(f"    K线:{n} 因子:{nf}")
        time.sleep(0.5)

    logger.info("===== 全量数据同步完成 =====")
    return {"status": "done", "stocks": len(stocks)}
