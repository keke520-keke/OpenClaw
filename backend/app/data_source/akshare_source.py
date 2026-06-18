"""AKShare 数据源 - 零成本实时行情"""
import os

# 彻底禁用代理
for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "ALL_PROXY", "all_proxy"]:
    os.environ.pop(k, None)
os.environ["NO_PROXY"] = "*"

import asyncio
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

import pandas as pd

_executor = ThreadPoolExecutor(max_workers=4)

# ---------- 东方财富 API 直连 ----------

EM_BASE = "https://push2.eastmoney.com/api/qt/clist/get"
EM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://quote.eastmoney.com/",
}


def _em_fetch(url: str, timeout: int = 15) -> dict:
    """绕过 requests，直接使用 urllib 请求东方财富 API"""
    req = urllib.request.Request(url, headers=EM_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise ConnectionError(f"无法连接东方财富 API: {e}")


def _em_spot_a(page: int = 1, page_size: int = 100, sort_field: str = "f12",
               sort_order: int = 1, market_filter: str = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23") -> pd.DataFrame:
    """获取沪深A股实时行情"""
    fields = "f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f62,f115,f128,f136,f152"
    url = (f"{EM_BASE}?pn={page}&pz={page_size}&po={sort_order}&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
           f"&fltt=2&invt=2&fid={sort_field}&fs={market_filter}&fields={fields}")
    data = _em_fetch(url)
    items = data.get("data", {}).get("diff", [])
    if not items:
        return pd.DataFrame()
    rows = []
    for it in items:
        rows.append({
            "code": str(it.get("f12", "")),
            "name": str(it.get("f14", "")),
            "price": float(it.get("f2") or 0),
            "change_pct": float(it.get("f3") or 0),
            "change_amt": float(it.get("f4") or 0),
            "volume": float(it.get("f5") or 0),
            "amount": float(it.get("f6") or 0),
            "amplitude": float(it.get("f7") or 0),
            "turnover_rate": float(it.get("f8") or 0),
            "pe_ratio": float(it.get("f9") or 0),
            "high": float(it.get("f15") or 0),
            "low": float(it.get("f16") or 0),
            "open": float(it.get("f17") or 0),
            "pre_close": float(it.get("f18") or 0),
            "volume_ratio": float(it.get("f10") or 0),
            "pb_ratio": float(it.get("f23") or 0),
            "total_mv": float(it.get("f20") or 0),
            "circ_mv": float(it.get("f21") or 0),
        })
    return pd.DataFrame(rows)


def _em_spot_index() -> pd.DataFrame:
    """获取指数行情"""
    fields = "f2,f3,f4,f6,f12,f14"
    url = (f"{EM_BASE}?pn=1&pz=20&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
           f"&fltt=2&invt=2&fid=f12&fs=m:1+t:2&fields={fields}")
    data = _em_fetch(url)
    items = data.get("data", {}).get("diff", [])
    rows = []
    for it in items:
        rows.append({
            "code": str(it.get("f12", "")),
            "name": str(it.get("f14", "")),
            "price": float(it.get("f2") or 0),
            "change_pct": float(it.get("f3") or 0),
            "change_amt": float(it.get("f4") or 0),
            "amount": float(it.get("f6") or 0),
        })
    return pd.DataFrame(rows)


def _em_kline(code: str, period: str = "daily", start_date: str = None, end_date: str = None) -> list:
    """获取K线数据"""
    market = "1" if code.startswith("6") else "0"
    secid = f"{market}.{code}"

    period_map = {"daily": "101", "weekly": "102", "monthly": "103"}
    klt = period_map.get(period, "101")

    if not start_date:
        start_date = (datetime.now() - timedelta(days=365)).strftime("%Y%m%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")

    fields = "f51,f52,f53,f54,f55,f56,f57,f58"
    url = (f"https://push2his.eastmoney.com/api/qt/stock/kline/get"
           f"?secid={secid}&klt={klt}&fqt=1"
           f"&beg={start_date}&end={end_date}"
           f"&fields1=f1,f2,f3,f4,f5,f6&fields2={fields}&ut=bd1d9ddb04089700cf9c27f6f7426281")

    data = _em_fetch(url)
    klines = data.get("data", {}).get("klines", [])
    result = []
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
                "amplitude": float(parts[7]) if len(parts) > 7 else 0,
            })
    return result


# ---------- Async Wrapper ----------

def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, lambda: func(*args, **kwargs))


async def get_market_overview() -> list:
    """大盘指数概览"""
    def _fetch():
        df = _em_spot_index()
        target_codes = ["1.000001", "0.399001", "0.399006", "1.000688"]
        target_names = {"1.000001": "上证指数", "0.399001": "深证成指",
                        "0.399006": "创业板指", "1.000688": "科创50"}
        result = []
        for _, row in df.iterrows():
            name = target_names.get(row["code"], row["name"])
            if row["code"] in target_codes:
                result.append({
                    "name": name, "code": row["code"],
                    "price": row["price"], "change_pct": row["change_pct"],
                    "change_amt": row["change_amt"], "amount": row["amount"],
                })
        return result
    return await _run_sync(_fetch)


async def get_realtime_quotes(page: int = 1, page_size: int = 50, sort_by: str = "amount") -> dict:
    """实时行情列表"""
    def _fetch():
        sort_map = {"amount": "f6", "change_pct": "f3", "volume": "f5", "turnover_rate": "f8"}
        field = sort_map.get(sort_by, "f6")

        # 获取多页以支持分页
        df = _em_spot_a(page=page, page_size=page_size, sort_field=field, sort_order=0)
        # 获取总数
        total_df = _em_spot_a(page=1, page_size=1, sort_field="f12", sort_order=1)
        total = total_df.get("count", 0) if "count" in (total_df.columns if hasattr(total_df, "columns") else {}) else 5000

        # 更好的方式获取总数
        fields = "f12"
        url = (f"{EM_BASE}?pn=1&pz=1&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281"
               f"&fltt=2&invt=2&fid=f12&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields={fields}")
        try:
            data = _em_fetch(url)
            total = data.get("data", {}).get("total", len(df))
        except Exception:
            total = len(df)

        cols = ["code", "name", "price", "change_pct", "change_amt", "volume",
                "amount", "amplitude", "high", "low", "open", "pre_close",
                "volume_ratio", "turnover_rate", "pe_ratio", "pb_ratio",
                "total_mv", "circ_mv"]
        available = [c for c in cols if c in df.columns]
        records = df[available].fillna(0).to_dict(orient="records")
        return {"total": total, "page": page, "page_size": page_size, "data": records}

    return await _run_sync(_fetch)


async def get_stock_detail(code: str) -> dict | None:
    """个股详情"""
    def _fetch():
        if code.startswith("6"):
            market_filter = f"m:1+t:2,m:0+t:6+f:!2, SecuritiesCode:1:{code}"
        else:
            market_filter = f"m:0+t:6+f:!2, SecuritiesCode:0:{code}"
        df = _em_spot_a(page=1, page_size=1, market_filter=market_filter)
        if df.empty:
            return None
        r = df.iloc[0]
        return {
            "code": r["code"], "name": r["name"],
            "price": float(r["price"]), "change_pct": float(r["change_pct"]),
            "change_amt": float(r["change_amt"]), "volume": float(r["volume"]),
            "amount": float(r["amount"]), "high": float(r["high"]),
            "low": float(r["low"]), "open": float(r["open"]),
            "pre_close": float(r["pre_close"]),
            "turnover_rate": float(r["turnover_rate"]),
            "pe_ratio": float(r["pe_ratio"]), "pb_ratio": float(r["pb_ratio"]),
            "total_mv": float(r["total_mv"]), "circ_mv": float(r["circ_mv"]),
        }
    return await _run_sync(_fetch)


async def get_stock_kline(code: str, period: str = "daily",
                          start_date: str = None, end_date: str = None) -> list:
    """K线数据"""
    return await _run_sync(_em_kline, code, period, start_date, end_date)
