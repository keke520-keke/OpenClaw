"""开发环境模拟数据 - 网络通后切换到 akshare_source"""
import random
import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)

STOCKS = [
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

INDICES = [
    {"name": "上证指数", "code": "1.000001", "price": 3350.00, "change_pct": 0.35, "change_amt": 11.73, "amount": 350000000000},
    {"name": "深证成指", "code": "0.399001", "price": 10800.00, "change_pct": -0.22, "change_amt": -23.76, "amount": 420000000000},
    {"name": "创业板指", "code": "0.399006", "price": 2150.00, "change_pct": 0.58, "change_amt": 12.47, "amount": 180000000000},
    {"name": "科创50", "code": "1.000688", "price": 980.00, "change_pct": -0.15, "change_amt": -1.47, "amount": 65000000000},
]


def _gen_stock(idx):
    """给每只股票加上随机波动"""
    code, name, base_price = STOCKS[idx]
    change_pct = round(random.uniform(-8, 8), 2)
    change_amt = round(base_price * change_pct / 100, 2)
    price = round(base_price + change_amt, 2)
    amount = round(random.uniform(5e7, 5e9), 2)
    volume = round(amount / price, 0)
    return {
        "code": code, "name": name, "price": price,
        "change_pct": change_pct, "change_amt": change_amt,
        "volume": volume, "amount": amount,
        "high": round(price * random.uniform(1.0, 1.05), 2),
        "low": round(price * random.uniform(0.95, 1.0), 2),
        "open": round(price * random.uniform(0.98, 1.02), 2),
        "pre_close": base_price,
        "amplitude": round(random.uniform(1, 8), 2),
        "turnover_rate": round(random.uniform(0.5, 15), 2),
        "volume_ratio": round(random.uniform(0.5, 3.5), 2),
        "pe_ratio": round(random.uniform(5, 80), 2),
        "pb_ratio": round(random.uniform(1, 10), 2),
        "total_mv": round(random.uniform(5e9, 5e11), 2),
        "circ_mv": round(random.uniform(3e9, 3e11), 2),
    }


def _gen_kline(code):
    """生成模拟K线"""
    base = next((s[2] for s in STOCKS if s[0] == code), 20.0)
    result = []
    for i in range(60, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        variation = random.uniform(-0.03, 0.03)
        close = round(base * (1 + variation), 2)
        open_p = round(close * random.uniform(0.99, 1.01), 2)
        high = round(max(open_p, close) * random.uniform(1.0, 1.03), 2)
        low = round(min(open_p, close) * random.uniform(0.97, 1.0), 2)
        volume = random.randint(100000, 5000000)
        amount = round(volume * close, 0)
        change_pct = round((close - base) / base * 100, 2)
        result.append({
            "date": date, "open": open_p, "close": close,
            "high": high, "low": low,
            "volume": volume, "amount": amount,
            "change_pct": change_pct,
        })
        base = close
    return result


def _run_sync(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(_executor, lambda: func(*args, **kwargs))


async def get_market_overview() -> list:
    """大盘指数"""
    return INDICES


async def get_realtime_quotes(page: int = 1, page_size: int = 50, sort_by: str = "amount") -> dict:
    """实时行情"""
    def _fetch():
        total = len(STOCKS)
        start = (page - 1) * page_size
        end = start + page_size
        stocks = [_gen_stock(i) for i in range(start, min(end, total))]
        return {"total": total, "page": page, "page_size": page_size, "data": stocks}
    return await _run_sync(_fetch)


async def get_stock_detail(code: str) -> dict | None:
    """个股详情"""
    def _fetch():
        for i, (c, _, _) in enumerate(STOCKS):
            if c == code:
                return _gen_stock(i)
        return None
    return await _run_sync(_fetch)


async def get_stock_kline(code: str, period: str = "daily",
                          start_date: str = None, end_date: str = None) -> list:
    """K线"""
    return await _run_sync(_gen_kline, code)
