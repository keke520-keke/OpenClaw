"""技术指标计算模块 - 完整的技术因子库

包含：
1. 趋势指标：MA、EMA、MACD、SAR
2. 震荡指标：KDJ、RSI、CCI、WR
3. 波动指标：ATR、布林带、标准差
4. 成交量指标：OBV、VWAP、资金流量
5. 形态指标：K线形态识别
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Kline:
    """K线数据"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float = 0

class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def ma(data: List[float], period: int) -> List[float]:
        """简单移动平均线"""
        if len(data) < period:
            return [None] * len(data)
        
        result = [None] * (period - 1)
        for i in range(period - 1, len(data)):
            result.append(sum(data[i-period+1:i+1]) / period)
        return result
    
    @staticmethod
    def ema(data: List[float], period: int) -> List[float]:
        """指数移动平均线"""
        if not data:
            return []
        
        result = [data[0]]
        multiplier = 2 / (period + 1)
        
        for i in range(1, len(data)):
            ema_value = (data[i] - result[-1]) * multiplier + result[-1]
            result.append(ema_value)
        return result
    
    @staticmethod
    def macd(data: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        """MACD指标"""
        ema_fast = TechnicalIndicators.ema(data, fast)
        ema_slow = TechnicalIndicators.ema(data, slow)
        
        dif = [f - s for f, s in zip(ema_fast, ema_slow)]
        dea = TechnicalIndicators.ema(dif, signal)
        histogram = [2 * (d - e) for d, e in zip(dif, dea)]
        
        return {
            'dif': dif,
            'dea': dea,
            'histogram': histogram
        }
    
    @staticmethod
    def kdj(high: List[float], low: List[float], close: List[float], 
            n: int = 9, m1: int = 3, m2: int = 3) -> Dict:
        """KDJ指标"""
        if len(close) < n:
            return {'k': [50] * len(close), 'd': [50] * len(close), 'j': [50] * len(close)}
        
        k_values = [50]
        d_values = [50]
        
        for i in range(n - 1, len(close)):
            high_n = max(high[i-n+1:i+1])
            low_n = min(low[i-n+1:i+1])
            
            if high_n == low_n:
                rsv = 50
            else:
                rsv = (close[i] - low_n) / (high_n - low_n) * 100
            
            k = (m1 - 1) / m1 * k_values[-1] + 1 / m1 * rsv
            d = (m2 - 1) / m2 * d_values[-1] + 1 / m2 * k
            
            k_values.append(k)
            d_values.append(d)
        
        k_values = [50] * (n - 1) + k_values[1:]
        d_values = [50] * (n - 1) + d_values[1:]
        j_values = [3 * k - 2 * d for k, d in zip(k_values, d_values)]
        
        return {'k': k_values, 'd': d_values, 'j': j_values}
    
    @staticmethod
    def rsi(data: List[float], period: int = 14) -> List[float]:
        """RSI相对强弱指标"""
        if len(data) < period + 1:
            return [50] * len(data)
        
        gains = []
        losses = []
        
        for i in range(1, len(data)):
            change = data[i] - data[i-1]
            gains.append(max(change, 0))
            losses.append(max(-change, 0))
        
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period
        
        result = [50] * period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - 100 / (1 + rs)
            
            result.append(rsi)
        
        return result
    
    @staticmethod
    def atr(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
        """ATR平均真实波幅"""
        if len(high) < 2:
            return [0] * len(high)
        
        tr = [high[0] - low[0]]
        for i in range(1, len(high)):
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        atr_values = TechnicalIndicators.ema(tr, period)
        return atr_values
    
    @staticmethod
    def bollinger_bands(data: List[float], period: int = 20, std_dev: int = 2) -> Dict:
        """布林带"""
        if len(data) < period:
            mid = data[-1] if data else 0
            return {
                'upper': [mid + 0.1] * len(data),
                'mid': [mid] * len(data),
                'lower': [mid - 0.1] * len(data),
                'width': [0.2] * len(data)
            }
        
        mid = TechnicalIndicators.ma(data, period)
        upper = []
        lower = []
        width = []
        
        for i in range(len(data)):
            if mid[i] is None:
                upper.append(None)
                lower.append(None)
                width.append(None)
            else:
                std = np.std(data[max(0, i-period+1):i+1])
                upper.append(mid[i] + std_dev * std)
                lower.append(mid[i] - std_dev * std)
                width.append(2 * std_dev * std / mid[i] * 100 if mid[i] else 0)
        
        return {'upper': upper, 'mid': mid, 'lower': lower, 'width': width}
    
    @staticmethod
    def cci(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
        """CCI顺势指标"""
        if len(close) < period:
            return [0] * len(close)
        
        tp = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]
        result = [0] * (period - 1)
        
        for i in range(period - 1, len(tp)):
            tp_slice = tp[i-period+1:i+1]
            mean_tp = sum(tp_slice) / period
            mean_dev = sum(abs(x - mean_tp) for x in tp_slice) / period
            
            if mean_dev == 0:
                cci = 0
            else:
                cci = (tp[i] - mean_tp) / (0.015 * mean_dev)
            
            result.append(cci)
        
        return result
    
    @staticmethod
    def williams_r(high: List[float], low: List[float], close: List[float], period: int = 14) -> List[float]:
        """威廉指标"""
        if len(close) < period:
            return [50] * len(close)
        
        result = [50] * (period - 1)
        
        for i in range(period - 1, len(close)):
            high_n = max(high[i-period+1:i+1])
            low_n = min(low[i-period+1:i+1])
            
            if high_n == low_n:
                wr = 50
            else:
                wr = (high_n - close[i]) / (high_n - low_n) * -100
            
            result.append(wr)
        
        return result
    
    @staticmethod
    def obv(close: List[float], volume: List[float]) -> List[float]:
        """OBV能量潮"""
        if not close:
            return []
        
        obv_values = [0]
        for i in range(1, len(close)):
            if close[i] > close[i-1]:
                obv_values.append(obv_values[-1] + volume[i])
            elif close[i] < close[i-1]:
                obv_values.append(obv_values[-1] - volume[i])
            else:
                obv_values.append(obv_values[-1])
        
        return obv_values
    
    @staticmethod
    def vwap(high: List[float], low: List[float], close: List[float], volume: List[float]) -> List[float]:
        """VWAP成交量加权平均价"""
        if not close:
            return []
        
        cumulative_tpv = 0
        cumulative_volume = 0
        result = []
        
        for i in range(len(close)):
            tp = (high[i] + low[i] + close[i]) / 3
            cumulative_tpv += tp * volume[i]
            cumulative_volume += volume[i]
            
            if cumulative_volume > 0:
                result.append(cumulative_tpv / cumulative_volume)
            else:
                result.append(close[i])
        
        return result
    
    @staticmethod
    def money_flow_index(high: List[float], low: List[float], close: List[float], 
                         volume: List[float], period: int = 14) -> List[float]:
        """资金流量指标MFI"""
        if len(close) < period:
            return [50] * len(close)
        
        tp = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]
        mf = [t * v for t, v in zip(tp, volume)]
        
        result = [50] * (period - 1)
        
        for i in range(period - 1, len(tp)):
            pos_mf = 0
            neg_mf = 0
            
            for j in range(i - period + 1, i + 1):
                if j > 0 and tp[j] > tp[j-1]:
                    pos_mf += mf[j]
                elif j > 0 and tp[j] < tp[j-1]:
                    neg_mf += mf[j]
            
            if neg_mf == 0:
                mfi = 100
            else:
                mf_ratio = pos_mf / neg_mf
                mfi = 100 - 100 / (1 + mf_ratio)
            
            result.append(mfi)
        
        return result
    
    @staticmethod
    def adx(high: List[float], low: List[float], close: List[float], period: int = 14) -> Dict:
        """ADX平均趋向指标"""
        if len(close) < period + 1:
            return {'adx': [25] * len(close), 'plus_di': [25] * len(close), 'minus_di': [25] * len(close)}
        
        plus_dm = []
        minus_dm = []
        tr = []
        
        for i in range(1, len(high)):
            up_move = high[i] - high[i-1]
            down_move = low[i-1] - low[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
            
            tr1 = high[i] - low[i]
            tr2 = abs(high[i] - close[i-1])
            tr3 = abs(low[i] - close[i-1])
            tr.append(max(tr1, tr2, tr3))
        
        # 平滑
        smoothed_plus_dm = TechnicalIndicators.ema(plus_dm, period)
        smoothed_minus_dm = TechnicalIndicators.ema(minus_dm, period)
        smoothed_tr = TechnicalIndicators.ema(tr, period)
        
        plus_di = [100 * p / t if t > 0 else 0 for p, t in zip(smoothed_plus_dm, smoothed_tr)]
        minus_di = [100 * m / t if t > 0 else 0 for m, t in zip(smoothed_minus_dm, smoothed_tr)]
        
        dx = [100 * abs(p - m) / (p + m) if (p + m) > 0 else 0 for p, m in zip(plus_di, minus_di)]
        adx = TechnicalIndicators.ema(dx, period)
        
        # 补齐长度
        adx = [25] + adx
        plus_di = [25] + plus_di
        minus_di = [25] + minus_di
        
        return {'adx': adx, 'plus_di': plus_di, 'minus_di': minus_di}
    
    @staticmethod
    def ichimoku(high: List[float], low: List[float], close: List[float]) -> Dict:
        """一目均衡表"""
        def period_high(data, period, i):
            start = max(0, i - period + 1)
            return max(data[start:i+1])
        
        def period_low(data, period, i):
            start = max(0, i - period + 1)
            return min(data[start:i+1])
        
        tenkan = []
        kijun = []
        senkou_a = []
        senkou_b = []
        
        for i in range(len(close)):
            # 转换线（9期）
            if i >= 8:
                tenkan.append((period_high(high, 9, i) + period_low(low, 9, i)) / 2)
            else:
                tenkan.append(close[i])
            
            # 基准线（26期）
            if i >= 25:
                kijun.append((period_high(high, 26, i) + period_low(low, 26, i)) / 2)
            else:
                kijun.append(close[i])
            
            # 先行带A
            senkou_a.append((tenkan[-1] + kijun[-1]) / 2)
            
            # 先行带B（52期）
            if i >= 51:
                senkou_b.append((period_high(high, 52, i) + period_low(low, 52, i)) / 2)
            else:
                senkou_b.append(close[i])
        
        return {
            'tenkan': tenkan,
            'kijun': kijun,
            'senkou_a': senkou_a,
            'senkou_b': senkou_b
        }
    
    @staticmethod
    def calculate_all(klines: List[Kline]) -> Dict:
        """计算所有技术指标"""
        if not klines:
            return {}
        
        close = [k.close for k in klines]
        high = [k.high for k in klines]
        low = [k.low for k in klines]
        volume = [k.volume for k in klines]
        open_price = [k.open for k in klines]
        
        return {
            # 趋势指标
            'ma5': TechnicalIndicators.ma(close, 5),
            'ma10': TechnicalIndicators.ma(close, 10),
            'ma20': TechnicalIndicators.ma(close, 20),
            'ma60': TechnicalIndicators.ma(close, 60),
            'ema12': TechnicalIndicators.ema(close, 12),
            'ema26': TechnicalIndicators.ema(close, 26),
            'macd': TechnicalIndicators.macd(close),
            'sar': TechnicalIndicators.sar(high, low, close),
            
            # 震荡指标
            'kdj': TechnicalIndicators.kdj(high, low, close),
            'rsi6': TechnicalIndicators.rsi(close, 6),
            'rsi14': TechnicalIndicators.rsi(close, 14),
            'cci': TechnicalIndicators.cci(high, low, close),
            'wr': TechnicalIndicators.williams_r(high, low, close),
            
            # 波动指标
            'atr': TechnicalIndicators.atr(high, low, close),
            'boll': TechnicalIndicators.bollinger_bands(close),
            
            # 成交量指标
            'obv': TechnicalIndicators.obv(close, volume),
            'vwap': TechnicalIndicators.vwap(high, low, close, volume),
            'mfi': TechnicalIndicators.money_flow_index(high, low, close, volume),
            
            # 趋势强度
            'adx': TechnicalIndicators.adx(high, low, close),
            'ichimoku': TechnicalIndicators.ichimoku(high, low, close),
            
            # 原始数据
            'close': close,
            'high': high,
            'low': low,
            'volume': volume,
            'open': open_price,
        }
    
    @staticmethod
    def sar(high: List[float], low: List[float], close: List[float], 
            af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> List[float]:
        """SAR抛物线指标"""
        if len(close) < 2:
            return close.copy()
        
        sar_values = [low[0]]
        trend = 1  # 1上涨, -1下跌
        af = af_start
        ep = high[0]
        
        for i in range(1, len(close)):
            prev_sar = sar_values[-1]
            
            if trend == 1:
                sar = prev_sar + af * (ep - prev_sar)
                sar = min(sar, low[i-1])
                if i >= 2:
                    sar = min(sar, low[i-2])
                
                if low[i] < sar:
                    trend = -1
                    sar = ep
                    ep = low[i]
                    af = af_start
                else:
                    if high[i] > ep:
                        ep = high[i]
                        af = min(af + af_step, af_max)
            else:
                sar = prev_sar + af * (ep - prev_sar)
                sar = max(sar, high[i-1])
                if i >= 2:
                    sar = max(sar, high[i-2])
                
                if high[i] > sar:
                    trend = 1
                    sar = ep
                    ep = high[i]
                    af = af_start
                else:
                    if low[i] < ep:
                        ep = low[i]
                        af = min(af + af_step, af_max)
            
            sar_values.append(sar)
        
        return sar_values


def calculate_indicators(kline_data: List[Dict]) -> Dict:
    """计算技术指标"""
    klines = [Kline(**k) for k in kline_data]
    return TechnicalIndicators.calculate_all(klines)


def get_signal_summary(indicators: Dict) -> Dict:
    """根据技术指标生成信号摘要"""
    signals = {
        'buy': [],
        'sell': [],
        'strength': 0,
    }
    
    if not indicators:
        return signals
    
    # MACD信号
    macd = indicators.get('macd', {})
    if macd.get('dif') and macd.get('dea'):
        dif = macd['dif'][-1]
        dea = macd['dea'][-1]
        prev_dif = macd['dif'][-2] if len(macd['dif']) > 1 else dif
        prev_dea = macd['dea'][-2] if len(macd['dea']) > 1 else dea
        
        if prev_dif <= prev_dea and dif > dea:
            signals['buy'].append('MACD金叉')
            signals['strength'] += 1
        elif prev_dif >= prev_dea and dif < dea:
            signals['sell'].append('MACD死叉')
            signals['strength'] -= 1
    
    # KDJ信号
    kdj = indicators.get('kdj', {})
    if kdj.get('k') and kdj.get('d') and kdj.get('j'):
        k = kdj['k'][-1]
        d = kdj['d'][-1]
        j = kdj['j'][-1]
        
        if k < 20 and d < 20:
            signals['buy'].append('KDJ超卖')
            signals['strength'] += 1
        elif k > 80 and d > 80:
            signals['sell'].append('KDJ超买')
            signals['strength'] -= 1
    
    # RSI信号
    rsi14 = indicators.get('rsi14', [])
    if rsi14:
        rsi = rsi14[-1]
        if rsi < 30:
            signals['buy'].append('RSI超卖')
            signals['strength'] += 1
        elif rsi > 70:
            signals['sell'].append('RSI超买')
            signals['strength'] -= 1
    
    # 布林带信号
    boll = indicators.get('boll', {})
    close = indicators.get('close', [])
    if boll.get('lower') and close:
        if close[-1] < boll['lower'][-1]:
            signals['buy'].append('价格跌破布林下轨')
            signals['strength'] += 1
        elif close[-1] > boll['upper'][-1]:
            signals['sell'].append('价格突破布林上轨')
            signals['strength'] -= 1
    
    # CCI信号
    cci = indicators.get('cci', [])
    if cci:
        if cci[-1] < -100:
            signals['buy'].append('CCI超卖')
            signals['strength'] += 1
        elif cci[-1] > 100:
            signals['sell'].append('CCI超买')
            signals['strength'] -= 1
    
    return signals
