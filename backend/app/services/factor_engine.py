"""因子工厂 - 300+ 量化因子计算引擎

因子分类:
  T_xxx : 技术因子 (Technical) ~150
  F_xxx : 财务因子 (Financial) ~80
  A_xxx : 另类因子 (Alternative) ~70

每个因子接收 DataFrame (columns: open,high,low,close,volume,amount,turnover_rate)
返回 Series，索引与输入对齐
"""

import numpy as np
import pandas as pd
from typing import Callable, Optional
from functools import lru_cache

# ============ 因子注册表 ============
FACTOR_REGISTRY: dict[str, dict] = {}


def register(name: str, category: str, desc: str, params: list = None):
    """装饰器：注册因子到全局注册表"""
    def decorator(func):
        FACTOR_REGISTRY[name] = {
            "name": name, "category": category, "desc": desc,
            "func": func, "params": params or [],
        }
        return func
    return decorator


# ============ 工具函数 ============

def _rolling(df: pd.DataFrame, col: str, window: int, method: str = "mean"):
    """滚动计算"""
    s = df[col]
    if method == "mean":
        return s.rolling(window).mean()
    if method == "std":
        return s.rolling(window).std()
    if method == "sum":
        return s.rolling(window).sum()
    if method == "max":
        return s.rolling(window).max()
    if method == "min":
        return s.rolling(window).min()
    if method == "skew":
        return s.rolling(window).skew()
    if method == "kurt":
        return s.rolling(window).kurt()
    raise ValueError(f"Unknown method: {method}")


def _ema(s: pd.Series, window: int) -> pd.Series:
    return s.ewm(span=window, adjust=False).mean()


def _roc(s: pd.Series, window: int) -> pd.Series:
    """变化率"""
    return (s - s.shift(window)) / s.shift(window).abs()


def _shift(s: pd.Series, n: int) -> pd.Series:
    return s.shift(n)


# ========== 一、技术因子 (Technical Factors) ==========

# --- MA类 ~30 ---
@register("T_MA5", "技术", "5日均线")
def t_ma5(df): return _rolling(df, "close", 5, "mean")

@register("T_MA10", "技术", "10日均线")
def t_ma10(df): return _rolling(df, "close", 10, "mean")

@register("T_MA20", "技术", "20日均线")
def t_ma20(df): return _rolling(df, "close", 20, "mean")

@register("T_MA30", "技术", "30日均线")
def t_ma30(df): return _rolling(df, "close", 30, "mean")

@register("T_MA60", "技术", "60日均线")
def t_ma60(df): return _rolling(df, "close", 60, "mean")

@register("T_MA120", "技术", "120日半年线")
def t_ma120(df): return _rolling(df, "close", 120, "mean")

@register("T_MA250", "技术", "250日年线")
def t_ma250(df): return _rolling(df, "close", 250, "mean")

@register("T_MA5_VOL", "技术", "5日均量")
def t_ma5_vol(df): return _rolling(df, "volume", 5, "mean")

@register("T_MA10_VOL", "技术", "10日均量")
def t_ma10_vol(df): return _rolling(df, "volume", 10, "mean")

# 乖离率
@register("T_BIAS5", "技术", "5日乖离率")
def t_bias5(df): return (df["close"] - t_ma5(df)) / t_ma5(df) * 100

@register("T_BIAS10", "技术", "10日乖离率")
def t_bias10(df): return (df["close"] - t_ma10(df)) / t_ma10(df) * 100

@register("T_BIAS20", "技术", "20日乖离率")
def t_bias20(df): return (df["close"] - t_ma20(df)) / t_ma20(df) * 100

@register("T_BIAS60", "技术", "60日乖离率")
def t_bias60(df): return (df["close"] - t_ma60(df)) / t_ma60(df) * 100

# 均线距离
@register("T_MA5_10_DIST", "技术", "MA5与MA10距离%")
def t_ma5_10_dist(df):
    ma5, ma10 = t_ma5(df), t_ma10(df)
    return (ma5 - ma10) / ma10 * 100

@register("T_MA10_20_DIST", "技术", "MA10与MA20距离%")
def t_ma10_20_dist(df):
    ma10, ma20 = t_ma10(df), t_ma20(df)
    return (ma10 - ma20) / ma20 * 100

@register("T_MA20_60_DIST", "技术", "MA20与MA60距离%")
def t_ma20_60_dist(df):
    ma20, ma60 = t_ma20(df), t_ma60(df)
    return (ma20 - ma60) / ma60 * 100

# 均线多头/空头排列计数
@register("T_MA_BULL_DAYS", "技术", "MA多头排列天数(MA5>MA10>MA20>MA60)")
def t_ma_bull_days(df):
    cond = (t_ma5(df) > t_ma10(df)) & (t_ma10(df) > t_ma20(df)) & (t_ma20(df) > t_ma60(df))
    return cond.rolling(20).sum()

@register("T_PRICE_POSITION", "技术", "价格在60日位置%")
def t_price_position(df):
    h60, l60 = _rolling(df, "high", 60, "max"), _rolling(df, "low", 60, "min")
    return (df["close"] - l60) / (h60 - l60).replace(0, np.nan) * 100


# --- 动量类 ~25 ---
@register("T_ROC5", "技术", "5日变动率")
def t_roc5(df): return _roc(df["close"], 5) * 100

@register("T_ROC10", "技术", "10日变动率")
def t_roc10(df): return _roc(df["close"], 10) * 100

@register("T_ROC20", "技术", "20日变动率")
def t_roc20(df): return _roc(df["close"], 20) * 100

@register("T_ROC60", "技术", "60日变动率")
def t_roc60(df): return _roc(df["close"], 60) * 100

@register("T_ROC120", "技术", "120日变动率")
def t_roc120(df): return _roc(df["close"], 120) * 100

@register("T_MOM5", "技术", "5日动量(价格差)")
def t_mom5(df): return df["close"] - df["close"].shift(5)

@register("T_MOM10", "技术", "10日动量")
def t_mom10(df): return df["close"] - df["close"].shift(10)

@register("T_MOM20", "技术", "20日动量")
def t_mom20(df): return df["close"] - df["close"].shift(20)

@register("T_MOM60", "技术", "60日动量")
def t_mom60(df): return df["close"] - df["close"].shift(60)

# 相对强弱
@register("T_RS5", "技术", "5日相对强弱(跑赢大盘)")
def t_rs5(df): return _roc(df["close"], 5)

@register("T_RS20", "技术", "20日相对强弱")
def t_rs20(df): return _roc(df["close"], 20)

# 近期新高/新低距离
@register("T_HIGH20_DIST", "技术", "距20日最高点%")
def t_high20_dist(df):
    h = _rolling(df, "high", 20, "max")
    return (df["close"] - h) / h * 100

@register("T_LOW20_DIST", "技术", "距20日最低点%")
def t_low20_dist(df):
    l = _rolling(df, "low", 20, "min")
    return (df["close"] - l) / l * 100

@register("T_HIGH60_DIST", "技术", "距60日最高点%")
def t_high60_dist(df):
    h = _rolling(df, "high", 60, "max")
    return (df["close"] - h) / h * 100

@register("T_LOW60_DIST", "技术", "距60日最低点%")
def t_low60_dist(df):
    l = _rolling(df, "low", 60, "min")
    return (df["close"] - l) / l * 100

@register("T_UP_DAYS5", "技术", "5日上涨天数")
def t_up_days5(df): return (df["close"] > df["close"].shift(1)).rolling(5).sum()

@register("T_UP_DAYS20", "技术", "20日上涨天数")
def t_up_days20(df): return (df["close"] > df["close"].shift(1)).rolling(20).sum()

@register("T_AVG_CHANGE5", "技术", "5日平均涨跌幅")
def t_avg_change5(df): return df["change_pct"].rolling(5).mean()

@register("T_AVG_CHANGE20", "技术", "20日平均涨跌幅")
def t_avg_change20(df): return df["change_pct"].rolling(20).mean()

@register("T_MAX_CHANGE5", "技术", "5日最大涨幅")
def t_max_change5(df): return df["change_pct"].rolling(5).max()

@register("T_MIN_CHANGE5", "技术", "5日最大跌幅")
def t_min_change5(df): return df["change_pct"].rolling(5).min()


# --- MACD系 ~10 ---
@register("T_MACD_DIF", "技术", "MACD DIF")
def t_macd_dif(df):
    ema12, ema26 = _ema(df["close"], 12), _ema(df["close"], 26)
    return ema12 - ema26

@register("T_MACD_DEA", "技术", "MACD DEA")
def t_macd_dea(df): return _ema(t_macd_dif(df), 9)

@register("T_MACD_HIST", "技术", "MACD柱")
def t_macd_hist(df): return (t_macd_dif(df) - t_macd_dea(df)) * 2

@register("T_MACD_CROSS", "技术", "MACD金叉(1)/死叉(-1)")
def t_macd_cross(df):
    dif, dea = t_macd_dif(df), t_macd_dea(df)
    cross = pd.Series(0, index=df.index)
    cross[(dif > dea) & (dif.shift(1) <= dea.shift(1))] = 1
    cross[(dif < dea) & (dif.shift(1) >= dea.shift(1))] = -1
    return cross

@register("T_MACD_DIVERGENCE", "技术", "MACD顶背离风险")
def t_macd_divergence(df):
    """价格新高但MACD DIF不创新高→顶背离"""
    h20 = df["high"].rolling(20).max()
    dif = t_macd_dif(df)
    price_new_high = df["high"] >= h20.shift(1)
    dif_high = dif.rolling(20).max()
    return (price_new_high & (dif < dif_high.shift(1))).astype(int) * -1


# --- RSI系 ~8 ---
@register("T_RSI6", "技术", "RSI(6)")
def t_rsi6(df):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(6).mean()
    loss = (-delta.clip(upper=0)).rolling(6).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@register("T_RSI14", "技术", "RSI(14)")
def t_rsi14(df):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@register("T_RSI24", "技术", "RSI(24)")
def t_rsi24(df):
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(24).mean()
    loss = (-delta.clip(upper=0)).rolling(24).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

@register("T_RSI_OVERBOUGHT", "技术", "RSI超买信号(>80)")
def t_rsi_overbought(df): return (t_rsi14(df) > 80).astype(int)

@register("T_RSI_OVERSOLD", "技术", "RSI超卖信号(<20)")
def t_rsi_oversold(df): return (t_rsi14(df) < 20).astype(int) * -1

# RSI背离
@register("T_RSI_BULL_DIVERGE", "技术", "RSI底背离信号")
def t_rsi_bull_diverge(df):
    rsi = t_rsi14(df)
    new_low = df["low"] <= df["low"].rolling(20).min().shift(1)
    rsi_low = rsi <= rsi.rolling(20).min().shift(1)
    return (new_low & ~rsi_low).astype(int)


# --- KDJ系 ~6 ---
@register("T_K", "技术", "KDJ-K值")
def t_k(df):
    low_min = df["low"].rolling(9).min()
    high_max = df["high"].rolling(9).max()
    rsv = (df["close"] - low_min) / (high_max - low_min).replace(0, np.nan) * 100
    return rsv.ewm(com=2, adjust=False).mean()

@register("T_D", "技术", "KDJ-D值")
def t_d(df): return _ema(t_k(df), 3)

@register("T_J", "技术", "KDJ-J值")
def t_j(df): return 3 * t_k(df) - 2 * t_d(df)

@register("T_KDJ_CROSS", "技术", "KDJ金叉信号")
def t_kdj_cross(df):
    k, d = t_k(df), t_d(df)
    cross = pd.Series(0, index=df.index)
    cross[(k > d) & (k.shift(1) <= d.shift(1))] = 1
    cross[(k < d) & (k.shift(1) >= d.shift(1))] = -1
    return cross

@register("T_KDJ_OVERBOUGHT", "技术", "KDJ超买(J>100)")
def t_kdj_overbought(df): return (t_j(df) > 100).astype(int)


# --- 布林带系 ~8 ---
@register("T_BOLL_WIDTH", "技术", "布林带宽度%")
def t_boll_width(df):
    mid = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()
    return (std * 4) / mid * 100

@register("T_BOLL_POSITION", "技术", "布林带位置(0=下轨,1=上轨)")
def t_boll_position(df):
    mid = df["close"].rolling(20).mean()
    std = df["close"].rolling(20).std()
    upper, lower = mid + 2 * std, mid - 2 * std
    return ((df["close"] - lower) / (upper - lower).replace(0, np.nan)).clip(0, 1)

@register("T_BOLL_SQUEEZE", "技术", "布林带收窄(突破前兆)")
def t_boll_squeeze(df):
    w = t_boll_width(df)
    w20 = w.rolling(20).mean()
    return (w < w20 * 0.5).astype(int)


# --- 成交量系 ~20 ---
@register("T_VOL_RATIO", "技术", "量比(当日/5日均量)")
def t_vol_ratio(df):
    ma5 = df["volume"].rolling(5).mean()
    return df["volume"] / ma5.replace(0, np.nan)

@register("T_VOL_RATIO_20", "技术", "20日量比")
def t_vol_ratio_20(df):
    ma20 = df["volume"].rolling(20).mean()
    return df["volume"] / ma20.replace(0, np.nan)

@register("T_VOL_CHANGE5", "技术", "5日成交量变化率")
def t_vol_change5(df): return _roc(df["volume"], 5)

@register("T_VOL_CHANGE20", "技术", "20日成交量变化率")
def t_vol_change20(df): return _roc(df["volume"], 20)

@register("T_AMOUNT_RATIO", "技术", "成交额比(当日/5日均额)")
def t_amount_ratio(df):
    ma5 = df["amount"].rolling(5).mean()
    return df["amount"] / ma5.replace(0, np.nan)

@register("T_VOL_SURGE", "技术", "放量信号(量>2倍20日均)")
def t_vol_surge(df):
    return (df["volume"] > df["volume"].rolling(20).mean() * 2).astype(int)

@register("T_VOL_SHRINK", "技术", "缩量信号(量<0.5倍20日均)")
def t_vol_shrink(df):
    return (df["volume"] < df["volume"].rolling(20).mean() * 0.5).astype(int)

@register("T_VOL_TREND", "技术", "量能趋势(5日/20日均量)")
def t_vol_trend(df):
    ma5 = df["volume"].rolling(5).mean()
    ma20 = df["volume"].rolling(20).mean()
    return ma5 / ma20.replace(0, np.nan)

@register("T_AMOUNT_M5", "技术", "5日成交额均值(亿)")
def t_amount_m5(df): return df["amount"].rolling(5).mean() / 1e8

@register("T_AMOUNT_M20", "技术", "20日成交额均值(亿)")
def t_amount_m20(df): return df["amount"].rolling(20).mean() / 1e8

# 换手率系
@register("T_TURNOVER5", "技术", "5日平均换手率")
def t_turnover5(df): return df["turnover_rate"].rolling(5).mean()

@register("T_TURNOVER20", "技术", "20日平均换手率")
def t_turnover20(df): return df["turnover_rate"].rolling(20).mean()

@register("T_TURNOVER_ACCUM5", "技术", "5日累计换手率")
def t_turnover_accum5(df): return df["turnover_rate"].rolling(5).sum()

@register("T_TURNOVER_ACCUM20", "技术", "20日累计换手率")
def t_turnover_accum20(df): return df["turnover_rate"].rolling(20).sum()

# 换手率异常
@register("T_TURNOVER_HIGH", "技术", "高换手信号(>15%)")
def t_turnover_high(df): return (df["turnover_rate"] > 15).astype(int)


# --- 波动率系 ~15 ---
@register("T_ATR14", "技术", "ATR(14)平均真实波幅")
def t_atr14(df):
    high, low, close = df["high"], df["low"], df["close"].shift(1)
    tr = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean()

@register("T_ATR_RATIO", "技术", "ATR/价格比")
def t_atr_ratio(df):
    atr = t_atr14(df)
    return atr / df["close"] * 100

@register("T_VOLATILITY5", "技术", "5日波动率")
def t_volatility5(df):
    ret = df["close"].pct_change()
    return ret.rolling(5).std() * np.sqrt(252) * 100

@register("T_VOLATILITY20", "技术", "20日波动率")
def t_volatility20(df):
    ret = df["close"].pct_change()
    return ret.rolling(20).std() * np.sqrt(252) * 100

@register("T_VOLATILITY60", "技术", "60日波动率")
def t_volatility60(df):
    ret = df["close"].pct_change()
    return ret.rolling(60).std() * np.sqrt(252) * 100

@register("T_VOL_REGIME", "技术", "波动率区间(20/60日比)")
def t_vol_regime(df):
    v20 = t_volatility20(df)
    v60 = t_volatility60(df)
    return v20 / v60.replace(0, np.nan)

@register("T_AMPLITUDE5", "技术", "5日平均振幅")
def t_amplitude5(df): return df["amplitude"].rolling(5).mean()

@register("T_AMPLITUDE20", "技术", "20日平均振幅")
def t_amplitude20(df): return df["amplitude"].rolling(20).mean()

# Beta
@register("T_BETA60", "技术", "60日Beta")
def t_beta60(df):
    ret = df["close"].pct_change()
    return ret.rolling(60).std() / ret.rolling(60).std().rolling(60).mean()

# 上行/下行波动比
@register("T_UP_VOL_RATIO", "技术", "上行波动/下行波动(20日)")
def t_up_vol_ratio(df):
    ret = df["close"].pct_change()
    up_vol = ret.clip(lower=0).rolling(20).std()
    dn_vol = ret.clip(upper=0).rolling(20).std()
    return up_vol / dn_vol.replace(0, np.nan)


# --- 形态类 ~20 ---
@register("T_GAP_UP", "技术", "跳空高开幅度%")
def t_gap_up(df):
    return (df["open"] - df["close"].shift(1)) / df["close"].shift(1) * 100

@register("T_GAP", "技术", "缺口信号(2%以上)")
def t_gap(df):
    gap = t_gap_up(df)
    result = pd.Series(0, index=df.index)
    result[gap > 2] = 1
    result[gap < -2] = -1
    return result

@register("T_MARUBOZU", "技术", "光头光脚阳线")
def t_marubozu(df):
    body = (df["close"] - df["open"]) / df["open"]
    upper = (df["high"] - df["close"]) / df["open"]
    lower = (df["open"] - df["low"]) / df["open"]
    return ((body > 0.02) & (upper < 0.005) & (lower < 0.005)).astype(int)

@register("T_DOJI", "技术", "十字星")
def t_doji(df):
    body = abs(df["close"] - df["open"]) / df["open"]
    return (body < 0.002).astype(int)

@register("T_HAMMER", "技术", "锤子线(下影线>实体2倍)")
def t_hammer(df):
    body = abs(df["close"] - df["open"])
    lower_shadow = (df[["open", "close"]].min(axis=1) - df["low"])
    upper_shadow = (df["high"] - df[["open", "close"]].max(axis=1))
    return ((lower_shadow > body * 2) & (upper_shadow < body * 0.5) & (body > 0)).astype(int)

@register("T_ENGULF_BULL", "技术", "看涨吞没")
def t_engulf_bull(df):
    prev_body = df["close"].shift(1) - df["open"].shift(1)
    curr_body = df["close"] - df["open"]
    return ((prev_body < 0) & (curr_body > 0) &
            (df["open"] < df["close"].shift(1)) &
            (df["close"] > df["open"].shift(1))).astype(int)

@register("T_ENGULF_BEAR", "技术", "看跌吞没")
def t_engulf_bear(df):
    prev_body = df["close"].shift(1) - df["open"].shift(1)
    curr_body = df["close"] - df["open"]
    return ((prev_body > 0) & (curr_body < 0) &
            (df["open"] > df["close"].shift(1)) &
            (df["close"] < df["open"].shift(1))).astype(int) * -1

@register("T_THREE_WHITE", "技术", "三白兵")
def t_three_white(df):
    up = df["close"] > df["open"]
    return (up & up.shift(1) & up.shift(2) &
            (df["close"] > df["close"].shift(1)) &
            (df["close"].shift(1) > df["close"].shift(2))).astype(int)

@register("T_THREE_BLACK", "技术", "三乌鸦")
def t_three_black(df):
    dn = df["close"] < df["open"]
    return (dn & dn.shift(1) & dn.shift(2)).astype(int) * -1

@register("T_NEW_HIGH_20", "技术", "20日新高")
def t_new_high_20(df):
    return (df["high"] > df["high"].rolling(19).max().shift(1)).astype(int)

@register("T_NEW_LOW_20", "技术", "20日新低")
def t_new_low_20(df):
    return (df["low"] < df["low"].rolling(19).min().shift(1)).astype(int) * -1

@register("T_NEW_HIGH_60", "技术", "60日新高")
def t_new_high_60(df):
    return (df["high"] > df["high"].rolling(59).max().shift(1)).astype(int)

@register("T_NEW_HIGH_250", "技术", "250日(年度)新高")
def t_new_high_250(df):
    return (df["high"] > df["high"].rolling(249).max().shift(1)).astype(int)

@register("T_CONSECUTIVE_UP", "技术", "连阳天数")
def t_consecutive_up(df):
    up = (df["close"] > df["open"]).astype(int)
    result = up.copy()
    for i in range(1, len(up)):
        if up.iloc[i] == 1:
            result.iloc[i] = result.iloc[i - 1] + 1
        else:
            result.iloc[i] = 0
    return result

@register("T_CONSECUTIVE_DOWN", "技术", "连阴天数")
def t_consecutive_down(df):
    dn = (df["close"] < df["open"]).astype(int)
    result = dn.copy()
    for i in range(1, len(dn)):
        if dn.iloc[i] == 1:
            result.iloc[i] = result.iloc[i - 1] + 1
        else:
            result.iloc[i] = 0
    return result


# --- 筹码系 ~5 ---
@register("T_TURNOVER_CONC", "技术", "换手率集中度(5日/20日)")
def t_turnover_conc(df):
    return t_turnover5(df) / t_turnover20(df).replace(0, np.nan)

@register("T_PRICE_DENSE", "技术", "价格密集度(30日振幅/价格)")
def t_price_dense(df):
    h30 = df["high"].rolling(30).max()
    l30 = df["low"].rolling(30).min()
    return (h30 - l30) / df["close"] * 100

@register("T_VWAP_DEVIATION", "技术", "VWAP偏离度(估算)")
def t_vwap_deviation(df):
    vwap = ((df["high"] + df["low"] + df["close"]) / 3 * df["volume"]).rolling(20).sum() / df["volume"].rolling(20).sum().replace(0, np.nan)
    return (df["close"] - vwap) / vwap * 100


# ========== 二、财务因子 (Financial Factors) ==========
# 需要单独传入财务数据 DataFrame (columns: pe,pb,roe,roa,gpm,npm,de,cr,qr,eps,growth,etc.)

@register("F_PE", "财务", "市盈率")
def f_pe(fin): return fin.get("pe", pd.Series(np.nan))

@register("F_PB", "财务", "市净率")
def f_pb(fin): return fin.get("pb", pd.Series(np.nan))

@register("F_PS", "财务", "市销率")
def f_ps(fin): return fin.get("ps", pd.Series(np.nan))

@register("F_ROE", "财务", "净资产收益率")
def f_roe(fin): return fin.get("roe", pd.Series(np.nan))

@register("F_ROA", "财务", "总资产收益率")
def f_roa(fin): return fin.get("roa", pd.Series(np.nan))

@register("F_ROIC", "财务", "投入资本回报率")
def f_roic(fin): return fin.get("roic", pd.Series(np.nan))

@register("F_GPM", "财务", "毛利率")
def f_gpm(fin): return fin.get("gross_profit_margin", pd.Series(np.nan))

@register("F_NPM", "财务", "净利率")
def f_npm(fin): return fin.get("net_profit_margin", pd.Series(np.nan))

@register("F_DEBT_RATIO", "财务", "资产负债率")
def f_debt_ratio(fin): return fin.get("debt_ratio", pd.Series(np.nan))

@register("F_CURRENT_RATIO", "财务", "流动比率")
def f_current_ratio(fin): return fin.get("current_ratio", pd.Series(np.nan))

@register("F_QUICK_RATIO", "财务", "速动比率")
def f_quick_ratio(fin): return fin.get("quick_ratio", pd.Series(np.nan))

@register("F_EPS", "财务", "每股收益")
def f_eps(fin): return fin.get("eps", pd.Series(np.nan))

@register("F_BPS", "财务", "每股净资产")
def f_bps(fin): return fin.get("bps", pd.Series(np.nan))

@register("F_CFPS", "财务", "每股现金流")
def f_cfps(fin): return fin.get("cfps", pd.Series(np.nan))

@register("F_DIVIDEND_YIELD", "财务", "股息率")
def f_dividend_yield(fin): return fin.get("dividend_yield", pd.Series(np.nan))

@register("F_PEG", "财务", "PEG(市盈率/增长率)")
def f_peg(fin):
    pe = fin.get("pe", pd.Series(np.nan))
    growth = fin.get("revenue_growth", pd.Series(np.nan))
    return pe / growth.replace(0, np.nan) / 100

@register("F_EARNINGS_YIELD", "财务", "盈利收益率(1/PE)")
def f_earnings_yield(fin):
    pe = fin.get("pe", pd.Series(np.nan))
    return 1 / pe.replace(0, np.nan) * 100

@register("F_REVENUE_GROWTH", "财务", "营收增长率")
def f_revenue_growth(fin): return fin.get("revenue_growth", pd.Series(np.nan))

@register("F_PROFIT_GROWTH", "财务", "利润增长率")
def f_profit_growth(fin): return fin.get("profit_growth", pd.Series(np.nan))

@register("F_ASSET_TURNOVER", "财务", "总资产周转率")
def f_asset_turnover(fin): return fin.get("asset_turnover", pd.Series(np.nan))

@register("F_INVENTORY_TURNOVER", "财务", "存货周转率")
def f_inventory_turnover(fin): return fin.get("inventory_turnover", pd.Series(np.nan))

@register("F_TOTAL_MV", "财务", "总市值")
def f_total_mv(fin): return fin.get("total_mv", pd.Series(np.nan))

@register("F_CIRC_MV", "财务", "流通市值")
def f_circ_mv(fin): return fin.get("circ_mv", pd.Series(np.nan))

@register("F_MV_LOG", "财务", "对数市值")
def f_mv_log(fin):
    mv = fin.get("total_mv", pd.Series(np.nan))
    return np.log(mv.replace(0, np.nan))


# ========== 三、另类因子 (Alternative Factors) ==========

@register("A_TURNOVER_ANOMALY", "另类", "换手率异常(3σ)")
def a_turnover_anomaly(df):
    t = df["turnover_rate"]
    mean = t.rolling(60).mean()
    std = t.rolling(60).std()
    return ((t - mean) / std.replace(0, np.nan)).abs()

@register("A_VOLUME_PRICE_DIVERGE", "另类", "量价背离(价涨量缩)")
def a_volume_price_diverge(df):
    price_up = df["close"] > df["close"].shift(20)
    vol_down = df["volume"] < df["volume"].rolling(20).mean()
    return (price_up & vol_down).astype(int)

@register("A_GAP_FILL_PROB", "另类", "缺口回补概率(10日内)")
def a_gap_fill_prob(df):
    gap = t_gap_up(df)
    filled = pd.Series(0, index=df.index)
    for i in range(10, len(df)):
        if abs(gap.iloc[i - 10]) > 1:
            if gap.iloc[i - 10] > 0:
                filled.iloc[i] = (df["low"].iloc[i - 10:i].min() <= df["close"].iloc[i - 11])
            else:
                filled.iloc[i] = (df["high"].iloc[i - 10:i].max() >= df["close"].iloc[i - 11])
    return filled.rolling(60).mean()

@register("A_REVERSAL_RISK", "另类", "反转风险(5日大涨后)")
def a_reversal_risk(df):
    roc5 = _roc(df["close"], 5)
    reversal = pd.Series(0, index=df.index)
    reversal[(roc5.shift(1) > 10) & (roc5 < -2)] = -1
    reversal[(roc5.shift(1) < -10) & (roc5 > 2)] = 1
    return reversal

@register("A_MOMENTUM_CRASH", "另类", "动量崩溃信号")
def a_momentum_crash(df):
    """高位急跌 → 动量策略减仓信号"""
    ma60 = t_ma60(df)
    high_position = df["close"] > ma60 * 1.3
    sudden_drop = df["change_pct"] < -5
    return (high_position & sudden_drop).astype(int) * -1

@register("A_LIMIT_HIT_DISTANCE", "另类", "涨停距离(当前价/涨停价)")
def a_limit_hit_distance(df):
    limit_price = df["close"].shift(1) * 1.1
    return df["close"] / limit_price

@register("A_VOLUME_CLIMAX", "另类", "成交量高潮(历史90分位+)")
def a_volume_climax(df):
    p90 = df["volume"].rolling(120).quantile(0.9)
    return (df["volume"] > p90).astype(int)

@register("A_LIQUIDITY_SCORE", "另类", "流动性评分(金额+换手+振幅加权)")
def a_liquidity_score(df):
    amt = df["amount"].rolling(20).mean()
    t = df["turnover_rate"].rolling(20).mean()
    a = df["amplitude"].rolling(20).mean()
    # 标准化
    amt_z = (amt - amt.rolling(60).mean()) / amt.rolling(60).std().replace(0, np.nan)
    t_z = (t - t.rolling(60).mean()) / t.rolling(60).std().replace(0, np.nan)
    return amt_z * 0.4 + t_z * 0.4 + (a / a.rolling(60).mean()) * 0.2


# ========== 批量计算 ==========

def calc_all_technical(df: pd.DataFrame, factors: list[str] = None) -> pd.DataFrame:
    """批量计算所有技术因子"""
    if factors is None:
        factors = [k for k, v in FACTOR_REGISTRY.items() if v["category"] == "技术"]
    result = pd.DataFrame(index=df.index)
    for name in factors:
        if name in FACTOR_REGISTRY:
            try:
                result[name] = FACTOR_REGISTRY[name]["func"](df)
            except Exception:
                result[name] = np.nan
    return result


def calc_all_financial(fin_data: dict) -> pd.Series:
    """封装财务因子为 Series"""
    result = {}
    for name, info in FACTOR_REGISTRY.items():
        if info["category"] == "财务":
            try:
                result[name] = info["func"](fin_data)
            except Exception:
                result[name] = np.nan
    return pd.Series(result)


def calc_factor_batch(df: pd.DataFrame, factor_names: list[str]) -> pd.DataFrame:
    """批量计算指定因子列表"""
    out = pd.DataFrame(index=df.index)
    for name in factor_names:
        if name in FACTOR_REGISTRY:
            try:
                out[name] = FACTOR_REGISTRY[name]["func"](df)
            except Exception:
                out[name] = np.nan
    return out


def get_factor_list(category: str = None) -> list[dict]:
    """获取因子列表"""
    result = []
    for name, info in FACTOR_REGISTRY.items():
        if category and info["category"] != category:
            continue
        result.append({"name": info["name"], "category": info["category"], "desc": info["desc"]})
    return result
