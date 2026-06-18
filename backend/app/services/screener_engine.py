"""选股引擎"""
import os
import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)

STOCKS_POOL = [
    ("000001", "平安银行", 11.50), ("000002", "万科A", 8.30),
    ("000858", "五粮液", 145.00), ("002415", "海康威视", 32.00),
    ("300750", "宁德时代", 210.00), ("600036", "招商银行", 38.50),
    ("600276", "恒瑞医药", 48.00), ("600519", "贵州茅台", 1680.00),
    ("600900", "长江电力", 28.00), ("601012", "隆基绿能", 18.50),
    ("601318", "中国平安", 45.00), ("601888", "中国中免", 78.00),
    ("688981", "中芯国际", 52.00), ("000333", "美的集团", 65.00),
    ("002594", "比亚迪", 260.00), ("300059", "东方财富", 16.00),
    ("600030", "中信证券", 22.00), ("601166", "兴业银行", 17.50),
    ("002475", "立讯精密", 32.50), ("688111", "金山办公", 310.00),
    ("300124", "汇川技术", 62.00), ("002230", "科大讯飞", 48.00),
    ("600809", "山西汾酒", 210.00), ("300274", "阳光电源", 88.00),
    ("002049", "紫光国微", 68.00), ("603259", "药明康德", 48.00),
    ("601899", "紫金矿业", 18.00), ("600438", "通威股份", 22.00),
    ("002714", "牧原股份", 42.00), ("300498", "温氏股份", 18.00),
    ("601857", "中国石油", 8.80), ("600028", "中国石化", 6.20),
    ("601088", "中国神华", 42.00), ("600941", "中国移动", 108.00),
    ("601728", "中国电信", 6.50), ("600050", "中国联通", 5.20),
    ("002352", "顺丰控股", 38.00), ("000651", "格力电器", 42.00),
    ("600887", "伊利股份", 28.00), ("002304", "洋河股份", 88.00),
    ("000568", "泸州老窖", 178.00), ("002142", "宁波银行", 24.00),
    ("601398", "工商银行", 6.00), ("601939", "建设银行", 7.20),
    ("601288", "农业银行", 4.50), ("601988", "中国银行", 4.80),
    ("600585", "海螺水泥", 24.00), ("601668", "中国建筑", 5.50),
    ("601390", "中国中铁", 6.80), ("601186", "中国铁建", 8.20),
]

PRESETS = {
    "volume_surge": {"name": "放量突破", "desc": "成交量异动+大涨",
                     "filters": {"volume_ratio_min": 2.0, "change_pct_min": 2, "turnover_min": 3}},
    "low_pe": {"name": "低估值蓝筹", "desc": "0<市盈率<20",
               "filters": {"pe_min": 0, "pe_max": 20, "price_min": 5, "amount_min": 5e7}},
    "limit_up": {"name": "涨停板", "desc": "涨幅>=9.5%",
                 "filters": {"change_pct_min": 9.5}},
    "high_turnover": {"name": "高换手活跃", "desc": "高换手+量比>1.5",
                      "filters": {"turnover_min": 10, "volume_ratio_min": 1.5}},
}


def _gen_stock_row(code, name, base):
    change_pct = round(random.uniform(-9.5, 9.5), 2)
    price = round(base * (1 + change_pct / 100), 2)
    amount = round(random.uniform(1e7, 5e9), 0)
    return {
        "code": code, "name": name, "price": price,
        "change_pct": change_pct, "change_amt": round(price - base, 2),
        "amount": amount,
        "turnover_rate": round(random.uniform(0.3, 18), 2),
        "pe_ratio": round(random.uniform(3, 120), 2),
        "volume_ratio": round(random.uniform(0.4, 4.5), 2),
        "total_mv": round(random.uniform(1e9, 5e11), 0),
        "pb_ratio": round(random.uniform(0.8, 12), 2),
    }


def _apply_filters(rows, filters):
    result = []
    for r in rows:
        ok = True
        if filters.get("volume_ratio_min") and r["volume_ratio"] < filters["volume_ratio_min"]:
            ok = False
        if filters.get("change_pct_min") and r["change_pct"] < filters["change_pct_min"]:
            ok = False
        if filters.get("change_pct_max") and r["change_pct"] > filters["change_pct_max"]:
            ok = False
        if filters.get("turnover_min") and r["turnover_rate"] < filters["turnover_min"]:
            ok = False
        if filters.get("turnover_max") and r["turnover_rate"] > filters["turnover_max"]:
            ok = False
        if filters.get("pe_min") is not None and r["pe_ratio"] < filters["pe_min"]:
            ok = False
        if filters.get("pe_max") is not None and r["pe_ratio"] > filters["pe_max"]:
            ok = False
        if filters.get("price_min") is not None and r["price"] < filters["price_min"]:
            ok = False
        if filters.get("price_max") is not None and r["price"] > filters["price_max"]:
            ok = False
        if filters.get("amount_min") and r["amount"] < filters["amount_min"]:
            ok = False
        if ok:
            result.append(r)
    return result


def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, lambda: func(*args, **kwargs))


async def run_screening(preset: str = None, filters: dict = None,
                        page: int = 1, page_size: int = 30) -> dict:
    def _fetch():
        if preset and preset in PRESETS:
            f = PRESETS[preset]["filters"]
        elif filters:
            f = filters
        else:
            f = {}

        all_rows = [_gen_stock_row(c, n, b) for c, n, b in STOCKS_POOL]
        filtered = _apply_filters(all_rows, f)
        filtered.sort(key=lambda x: x["amount"], reverse=True)

        total = len(filtered)
        start = (page - 1) * page_size
        return {
            "total": total, "page": page, "page_size": page_size,
            "data": filtered[start:start + page_size],
        }
    return await _run_sync(_fetch)


async def get_presets() -> list:
    return [{"key": k, "name": v["name"], "desc": v["desc"]} for k, v in PRESETS.items()]
