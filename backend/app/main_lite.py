"""OpenClaw 轻量启动 — 绕过SQLAlchemy，Mock数据直连"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import random, math, json, subprocess, threading, time

app = FastAPI(title="OpenClaw API Lite", version="1.0.0-lite")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ---- 扩展股票池（模拟真实A股） ----
STOCKS = [
    ("600519","贵州茅台",1680),("000858","五粮液",145),("300750","宁德时代",210),
    ("002594","比亚迪",260),("600036","招商银行",38.5),("601318","中国平安",45),
    ("600276","恒瑞医药",48),("601012","隆基绿能",18.5),("000333","美的集团",65),
    ("300059","东方财富",16),("600030","中信证券",22),("601888","中国中免",78),
    ("688981","中芯国际",52),("002475","立讯精密",32.5),("600900","长江电力",28),
    ("601899","紫金矿业",18),("600809","山西汾酒",210),("000568","泸州老窖",178),
    ("300274","阳光电源",88),("002230","科大讯飞",48),("601166","兴业银行",17.5),
    ("600887","伊利股份",28),("002714","牧原股份",42),("601857","中国石油",8.8),
    ("600028","中国石化",6.2),("601398","工商银行",6.0),("601939","建设银行",7.2),
    ("601288","农业银行",4.5),("601988","中国银行",4.8),("000001","平安银行",11.5),
    ("000002","万科A",8.3),("002415","海康威视",32),("300498","温氏股份",18),
    ("603259","药明康德",48),("002049","紫光国微",68),("300124","汇川技术",62),
    ("688111","金山办公",310),("600585","海螺水泥",24),("601668","中国建筑",5.5),
    ("601390","中国中铁",6.8),("000651","格力电器",42),("002304","洋河股份",88),
    ("601088","中国神华",42),("600941","中国移动",108),("600438","通威股份",22),
    ("002352","顺丰控股",38),("300760","迈瑞医疗",280),("002142","宁波银行",24),
    ("600809","山西汾酒",210),("688012","中微公司",120),
]

# ---- 真实数据缓存（Node.js子进程抓取） ----
_real_cache: dict = {"data": None, "time": 0, "lock": threading.Lock()}


def _fetch_real_via_node() -> list | None:
    """通过 Node.js 子进程抓取东方财富实时数据"""
    try:
        script = """
const https = require('https');
const url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f2,f3,f5,f8,f12,f14';
https.get(url, {headers:{'User-Agent':'Mozilla/5.0','Referer':'https://quote.eastmoney.com/'},rejectUnauthorized:false,timeout:8000},res=>{
  let d=''; res.on('data',c=>d+=c); res.on('end',()=>{
    try{const j=JSON.parse(d); const items=j.data.diff;
      const out=items.map(i=>({code:i.f12+'',name:i.f14+'',price:+i.f2||0,pct_chg:+i.f3||0,volume:+i.f5||0,turnover:+i.f8||0}));
      console.log(JSON.stringify(out));
    }catch(e){console.log('[]');}
  });
}).on('error',()=>console.log('[]'));
setTimeout(()=>{},10000);
"""
        result = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=12)
        data = json.loads(result.stdout.strip() or "[]")
        if data:
            return data
    except Exception:
        pass
    return None


def _get_real_data() -> list | None:
    """带缓存的真实数据获取（5分钟TTL）"""
    with _real_cache["lock"]:
        if _real_cache["data"] and time.time() - _real_cache["time"] < 300:
            return _real_cache["data"]
    data = _fetch_real_via_node()
    if data:
        with _real_cache["lock"]:
            _real_cache["data"] = data
            _real_cache["time"] = time.time()
    return data


@app.get("/api/stock/list")
def stock_list():
    """获取真实A股列表（网络不通时回退增强Mock）"""
    real = _get_real_data()
    if real:
        return {"code": 0, "msg": "success (live)", "data": real, "total": len(real), "source": "东方财富实时"}

    # 回退：增强Mock（字段与真实API一致）
    data = []
    for code, name, base in STOCKS:
        pct = round(random.uniform(-9.5, 9.5), 2)
        price = round(base * (1 + pct / 100), 2)
        data.append({
            "code": code, "name": name, "price": price,
            "pct_chg": pct, "volume": random.randint(100000, 50000000),
            "turnover": round(random.uniform(0.3, 18), 2),
            "amount": round(random.uniform(5e6, 5e9), 0),
            "high": round(price * random.uniform(1.0, 1.05), 2),
            "low": round(price * random.uniform(0.95, 1.0), 2),
            "open": round(price * random.uniform(0.98, 1.02), 2),
            "pre_close": base,
        })
    return {"code": 0, "msg": "success (mock fallback)", "data": data, "total": len(data), "source": "模拟数据（东方财富API暂不可达）"}

def _gen_quote(code, name, base):
    change_pct = round(random.uniform(-9.5, 9.5), 2)
    price = round(base * (1 + change_pct / 100), 2)
    return {
        "code": code, "name": name, "price": price,
        "change_pct": change_pct, "change_amt": round(price - base, 2),
        "open": round(price * random.uniform(0.98, 1.02), 2),
        "high": round(price * random.uniform(1.0, 1.05), 2),
        "low": round(price * random.uniform(0.95, 1.0), 2),
        "pre_close": base,
        "volume": random.randint(100000, 50000000),
        "amount": round(random.uniform(5e6, 5e9), 0),
        "amplitude": round(random.uniform(1, 8), 2),
        "turnover_rate": round(random.uniform(0.5, 15), 2),
        "volume_ratio": round(random.uniform(0.4, 4.5), 2),
        "pe_ratio": round(random.uniform(5, 80), 2),
        "pb_ratio": round(random.uniform(1, 10), 2),
        "total_mv": round(random.uniform(5e9, 5e11), 0),
        "circ_mv": round(random.uniform(3e9, 3e11), 0),
    }

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0", "mode": "lite"}

@app.get("/api/market/overview")
def overview():
    return {"code": 0, "data": [
        {"name":"上证指数","code":"000001","price":3350+random.uniform(-30,30),"change_pct":round(random.uniform(-1,1),2)},
        {"name":"深证成指","code":"399001","price":10800+random.uniform(-100,100),"change_pct":round(random.uniform(-1,1),2)},
        {"name":"创业板指","code":"399006","price":2150+random.uniform(-20,20),"change_pct":round(random.uniform(-1,1),2)},
        {"name":"科创50","code":"000688","price":980+random.uniform(-10,10),"change_pct":round(random.uniform(-1,1),2)},
    ]}

@app.get("/api/market/quotes")
def quotes(page: int = 1, page_size: int = 30):
    all_stocks = [_gen_quote(c, n, b) for c, n, b in STOCKS]
    all_stocks.sort(key=lambda x: x["amount"], reverse=True)
    total = len(all_stocks)
    start = (page - 1) * page_size
    return {"code": 0, "total": total, "page": page, "page_size": page_size,
            "data": all_stocks[start:start+page_size]}

@app.get("/api/market/stock/{code}")
def stock_detail(code: str):
    for c, n, b in STOCKS:
        if c == code:
            return {"code": 0, "data": _gen_quote(c, n, b)}
    return {"code": 404, "msg": "未找到"}

@app.get("/api/market/kline/{code}")
def kline(code: str):
    base = next((b for c, n, b in STOCKS if c == code), 50)
    from datetime import datetime, timedelta
    result = []
    price = base * 0.7
    for i in range(60, 0, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        change = random.uniform(-0.03, 0.03)
        close = round(price * (1 + change), 2)
        result.append({"date": date, "open": round(price, 2), "close": close,
                       "high": round(max(price, close) * 1.02, 2),
                       "low": round(min(price, close) * 0.98, 2),
                       "volume": random.randint(100000, 5000000),
                       "amount": round(random.uniform(1e7, 5e9), 0),
                       "change_pct": round(change * 100, 2)})
        price = close
    return {"code": 0, "data": result}

PRESETS = {
    "volume_surge": {"name": "放量突破", "desc": "量比>2 + 涨>2%"},
    "low_pe": {"name": "低估值蓝筹", "desc": "0<PE<20"},
    "limit_up": {"name": "涨停板", "desc": "涨幅>=9.5%"},
    "high_turnover": {"name": "高换手活跃", "desc": "换手>10%"},
}

@app.get("/api/screener/presets")
def screener_presets():
    return {"code": 0, "data": [{"key": k, "name": v["name"], "desc": v["desc"]} for k, v in PRESETS.items()]}

@app.get("/api/screener/run")
def screener_run(preset: str = "volume_surge"):
    all_q = [_gen_quote(c, n, b) for c, n, b in STOCKS]
    random.shuffle(all_q)
    n = random.randint(3, 8)
    return {"code": 0, "preset": preset, "total": n, "data": all_q[:n]}

@app.get("/api/paper/account")
def paper_account():
    return {"code": 0, "data": {"account_id": "PAPER_DEMO", "name": "演示账户",
            "cash": 1000000, "total_equity": 1000000, "total_market_value": 0,
            "total_unrealized_pnl": 0, "total_realized_pnl": 0, "total_return_pct": 0,
            "position_count": 0, "pending_orders": 0}}

@app.get("/api/paper/positions")
def paper_positions():
    return {"code": 0, "data": [], "count": 0}

@app.get("/api/paper/orders")
def paper_orders():
    return {"code": 0, "data": [], "count": 0}

@app.get("/api/paper/stats")
def paper_stats():
    return {"code": 0, "data": {"total_trades": 0, "buy_trades": 0, "sell_trades": 0,
            "total_commission": 0, "total_realized_pnl": 0}}

@app.get("/api/backtest/config-defaults")
def bt_config():
    return {"code": 0, "config": {"initial_capital": 1e6, "commission_rate": 0.0003,
            "stamp_duty": 0.001, "slippage": 0.001, "max_position_pct": 0.2,
            "max_positions": 10, "stop_loss": 0.08, "take_profit": 0.3,
            "max_drawdown_limit": 0.25, "rebalance_freq": "M"}}

@app.get("/api/ai/status")
def ai_status():
    return {"code": 0, "trained": False, "models": ["rf", "gbm", "lr"], "features": 0}

@app.get("/api/ai/rebalance-stats")
def ai_rebalance():
    return {"code": 0, "strategy": "月度再平衡", "max_stocks": 8,
            "max_single_weight": "20%", "turnover_limit": "30%"}

@app.get("/api/factors/categories")
def factor_cats():
    return {"code": 0, "data": {"技术": 101, "财务": 24, "另类": 8}, "total": 133}

@app.get("/api/factors/list")
def factor_list():
    cats = {"技术": ["T_MA5","T_MA10","T_MA20","T_MA60","T_MACD_DIF","T_RSI14","T_K","T_D","T_J","T_BOLL_WIDTH"],
            "财务": ["F_PE","F_PB","F_ROE","F_ROA","F_GPM"],
            "另类": ["A_LIQUIDITY_SCORE","A_MOMENTUM_CRASH","A_REVERSAL_RISK"]}
    data = []
    for cat, names in cats.items():
        for n in names:
            data.append({"name": n, "category": cat, "desc": f"{n}因子"})
    return {"code": 0, "total": len(data), "data": data}

@app.get("/api/autotrade/status")
def autotrade_status():
    return {"code": 0, "data": {"enabled": False, "trade_count_today": 0, "max_daily_trades": 20}}

@app.get("/api/auth/tiers")
def auth_tiers():
    return {"code": 0, "data": [
        {"tier": "free", "name": "免费版", "price": "0元/月", "features": ["实时行情", "1个选股策略"]},
        {"tier": "basic", "name": "基础版", "price": "29.9元/月", "features": ["全部选股", "基础因子", "纸盘交易"]},
        {"tier": "pro", "name": "专业版", "price": "99.9元/月", "features": ["全部因子", "AI信号", "回测系统", "自动交易"]},
    ]}
