"""多因子打分引擎 - 综合评分系统

核心功能：
1. 多维度因子打分（0-100分）
2. 技术面因子：MACD、OBV、VWAP、RSI、量比
3. 基本面因子：市值、PE、行业
4. 资金面因子：主力资金流向、大单占比
5. 综合排序与筛选
"""
import numpy as np
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class StockData:
    """股票数据"""
    code: str
    name: str
    price: float
    change_pct: float
    volume: float
    amount: float
    turnover: float = 0
    pe_ratio: float = 0
    market_cap: float = 0

class ScoringEngine:
    """多因子打分引擎"""
    
    # 因子权重配置
    DEFAULT_WEIGHTS = {
        'macd_hist_slope': 15,     # MACD柱状图斜率
        'obv_trend': 15,           # OBV能量潮趋势
        'vwap_deviation': 10,      # VWAP资金成本偏离度
        'rsi_position': 15,        # RSI位置
        'volume_ratio': 15,        # 量比
        'price_position': 10,      # 价格位置（布林带）
        'market_cap': 10,          # 市值（小盘加分）
        'turnover_quality': 10,    # 换手质量
        'sector_momentum': 5,      # 行业动量
    }
    
    @staticmethod
    def score_macd_hist_slope(closes: List[float]) -> float:
        """MACD柱状图斜率评分（0-100）
        
        正斜率且加速 → 高分
        负斜率 → 低分
        """
        if len(closes) < 30:
            return 50
        
        # 计算MACD
        ema12 = np.mean(closes[-12:])
        ema26 = np.mean(closes[-26:])
        dif = ema12 - ema26
        
        # 简化MACD柱状图（使用价格变化率代替）
        recent_changes = [(closes[i] - closes[i-1]) / closes[i-1] * 100 
                         for i in range(-10, 0)]
        
        # 计算斜率
        if len(recent_changes) >= 2:
            slope = np.polyfit(range(len(recent_changes)), recent_changes, 1)[0]
        else:
            slope = 0
        
        # 评分：正斜率且加速得分高
        if slope > 0.5:
            score = min(90, 70 + slope * 20)
        elif slope > 0:
            score = 50 + slope * 40
        elif slope > -0.5:
            score = 50 + slope * 40
        else:
            score = max(10, 30 + slope * 20)
        
        return round(score, 1)
    
    @staticmethod
    def score_obv_trend(volumes: List[float], closes: List[float]) -> float:
        """OBV能量潮趋势评分（0-100）
        
        OBV上升趋势 → 高分（资金流入）
        OBV下降趋势 → 低分（资金流出）
        """
        if len(closes) < 20:
            return 50
        
        # 计算OBV
        obv = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        
        # 计算OBV趋势（近10日斜率）
        recent_obv = obv[-10:]
        if len(recent_obv) >= 2:
            slope = np.polyfit(range(len(recent_obv)), recent_obv, 1)[0]
        else:
            slope = 0
        
        # 归一化评分
        avg_obv = np.mean(np.abs(recent_obv)) if recent_obv else 1
        normalized_slope = slope / avg_obv * 100 if avg_obv > 0 else 0
        
        score = 50 + np.clip(normalized_slope * 2, -40, 40)
        return round(score, 1)
    
    @staticmethod
    def score_vwap_deviation(close: float, high: float, low: float, 
                              volume: float, avg_volume: float) -> float:
        """VWAP资金成本偏离度评分（0-100）
        
        价格在VWAP上方 → 高分（强势）
        价格在VWAP下方 → 低分（弱势）
        """
        # 估算VWAP（典型价格 * 成交量）
        typical_price = (high + low + close) / 3
        
        # 与当前价格比较
        if close > typical_price:
            deviation = (close - typical_price) / typical_price * 100
            score = min(90, 60 + deviation * 5)
        else:
            deviation = (typical_price - close) / typical_price * 100
            score = max(10, 40 - deviation * 5)
        
        return round(score, 1)
    
    @staticmethod
    def score_rsi_position(closes: List[float]) -> float:
        """RSI位置评分（0-100）
        
        RSI在30-70之间 → 高分（健康）
        RSI超买(>70)或超卖(<30) → 低分
        """
        if len(closes) < 15:
            return 50
        
        # 计算RSI(14)
        gains = []
        losses = []
        for i in range(-14, 0):
            change = closes[i] - closes[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - 100 / (1 + rs)
        
        # 评分：30-70区间得分最高
        if 30 <= rsi <= 70:
            # 中间区域得分高
            score = 70 + (50 - abs(rsi - 50)) * 0.6
        elif rsi < 30:
            # 超卖区（可能反弹，给中等分）
            score = 40 + (30 - rsi) * 0.5
        else:
            # 超买区（风险高，低分）
            score = max(20, 50 - (rsi - 70) * 2)
        
        return round(score, 1)
    
    @staticmethod
    def score_volume_ratio(volume: float, avg_volume: float) -> float:
        """量比评分（0-100）
        
        量比2-5 → 高分（温和放量）
        量比>10 → 低分（过度放量，可能是出货）
        """
        if avg_volume == 0:
            return 50
        
        ratio = volume / avg_volume
        
        if 2 <= ratio <= 5:
            # 温和放量，最佳
            score = 80 + (ratio - 2) * 4
        elif 1.5 <= ratio < 2:
            # 轻度放量
            score = 60 + (ratio - 1.5) * 40
        elif 5 < ratio <= 10:
            # 较大放量
            score = 80 - (ratio - 5) * 4
        elif ratio > 10:
            # 过度放量，可能是出货
            score = max(30, 40 - (ratio - 10) * 2)
        elif ratio < 1.5:
            # 缩量
            score = 40 + ratio * 13
        
        return round(np.clip(score, 0, 100), 1)
    
    @staticmethod
    def score_price_position(close: float, high: float, low: float, 
                              ma20: float = None) -> float:
        """价格位置评分（0-100）
        
        价格在布林带中轨上方 → 高分
        接近上轨 → 中等（可能回调）
        接近下轨 → 低分
        """
        hl_range = high - low
        if hl_range == 0:
            return 50
        
        position = (close - low) / hl_range
        
        if ma20 and ma20 > 0:
            # 有20日均线，判断趋势
            if close > ma20:
                # 在均线上方，趋势向上
                score = 60 + position * 30
            else:
                # 在均线下方，趋势向下
                score = 40 - (1 - position) * 30
        else:
            # 无均线，纯位置评分
            score = 50 + (position - 0.5) * 60
        
        return round(np.clip(score, 10, 90), 1)
    
    @staticmethod
    def score_market_cap(market_cap: float) -> float:
        """市值评分（0-100）
        
        小盘股（<50亿）→ 高分（弹性大）
        大盘股（>500亿）→ 低分（弹性小）
        """
        if market_cap <= 0:
            return 50
        
        cap_billion = market_cap / 1e8  # 转换为亿
        
        if cap_billion < 50:
            # 小盘股
            score = 80 + (50 - cap_billion) * 0.4
        elif cap_billion < 100:
            # 中小盘
            score = 70
        elif cap_billion < 300:
            # 中盘
            score = 55
        elif cap_billion < 500:
            # 中大盘
            score = 40
        else:
            # 大盘
            score = max(20, 35 - (cap_billion - 500) * 0.01)
        
        return round(np.clip(score, 20, 90), 1)
    
    @staticmethod
    def score_turnover_quality(turnover: float) -> float:
        """换手质量评分（0-100）
        
        换手率3-8% → 高分（活跃但不过度）
        换手率>15% → 低分（过度投机）
        """
        if 3 <= turnover <= 8:
            # 最佳区间
            score = 80 + (turnover - 3) * 4
        elif 1 <= turnover < 3:
            # 低换手
            score = 50 + turnover * 10
        elif 8 < turnover <= 15:
            # 高换手
            score = 80 - (turnover - 8) * 5
        elif turnover > 15:
            # 过度投机
            score = max(20, 45 - (turnover - 15) * 3)
        else:
            # 极低换手
            score = 30
        
        return round(np.clip(score, 20, 90), 1)
    
    @staticmethod
    def calculate_composite_score(stock_data: Dict, 
                                   closes: List[float] = None,
                                   volumes: List[float] = None,
                                   weights: Dict = None) -> Dict:
        """计算综合评分
        
        Args:
            stock_data: 股票基础数据
            closes: 收盘价序列
            volumes: 成交量序列
            weights: 因子权重
            
        Returns:
            综合评分和各因子得分
        """
        if weights is None:
            weights = ScoringEngine.DEFAULT_WEIGHTS
        
        # 准备数据
        if closes is None:
            closes = [stock_data.get('price', 100)]
        if volumes is None:
            volumes = [stock_data.get('volume', 10000)]
        
        # 计算各因子得分
        scores = {}
        
        # 1. MACD柱状图斜率
        scores['macd_hist_slope'] = ScoringEngine.score_macd_hist_slope(closes)
        
        # 2. OBV能量潮趋势
        scores['obv_trend'] = ScoringEngine.score_obv_trend(volumes, closes)
        
        # 3. VWAP偏离度
        scores['vwap_deviation'] = ScoringEngine.score_vwap_deviation(
            stock_data.get('price', 0),
            stock_data.get('high', stock_data.get('price', 0)),
            stock_data.get('low', stock_data.get('price', 0)),
            stock_data.get('volume', 0),
            np.mean(volumes) if volumes else 1
        )
        
        # 4. RSI位置
        scores['rsi_position'] = ScoringEngine.score_rsi_position(closes)
        
        # 5. 量比
        avg_vol = np.mean(volumes) if len(volumes) > 1 else volumes[0]
        scores['volume_ratio'] = ScoringEngine.score_volume_ratio(
            stock_data.get('volume', 0), avg_vol
        )
        
        # 6. 价格位置
        scores['price_position'] = ScoringEngine.score_price_position(
            stock_data.get('price', 0),
            stock_data.get('high', stock_data.get('price', 0)),
            stock_data.get('low', stock_data.get('price', 0))
        )
        
        # 7. 市值
        scores['market_cap'] = ScoringEngine.score_market_cap(
            stock_data.get('market_cap', 0)
        )
        
        # 8. 换手质量
        scores['turnover_quality'] = ScoringEngine.score_turnover_quality(
            stock_data.get('turnover', 0)
        )
        
        # 9. 行业动量（简化版，基于涨跌幅）
        change_pct = stock_data.get('change_pct', 0)
        scores['sector_momentum'] = min(80, max(20, 50 + change_pct * 5))
        
        # 计算加权总分
        total_score = 0
        total_weight = 0
        for factor, score in scores.items():
            weight = weights.get(factor, 10)
            total_score += score * weight
            total_weight += weight
        
        composite_score = total_score / total_weight if total_weight > 0 else 50
        
        # 确保返回Python原生类型，避免numpy序列化问题
        return {
            'code': str(stock_data.get('code', '')),
            'name': str(stock_data.get('name', '')),
            'price': float(stock_data.get('price', 0)),
            'pct_chg': float(stock_data.get('change_pct', 0) or stock_data.get('pct_chg', 0)),
            'amount': float(stock_data.get('amount', 0)),
            'turnover': float(stock_data.get('turnover', 0) or stock_data.get('turnover_rate', 0)),
            'volume': float(stock_data.get('volume', 0)),
            'composite_score': float(round(composite_score, 1)),
            'factor_scores': {k: float(v) for k, v in scores.items()},
            'weights': {k: int(v) for k, v in weights.items()},
            'grade': 'A' if composite_score >= 75 else 'B' if composite_score >= 60 else 'C' if composite_score >= 45 else 'D',
        }


def score_stocks(stocks: List[Dict], kline_data: Dict = None) -> List[Dict]:
    """批量打分并排序
    
    Args:
        stocks: 股票列表
        kline_data: {code: {"closes": [...], "volumes": [...]}}
        
    Returns:
        按综合评分排序的股票列表
    """
    results = []
    
    for stock in stocks:
        code = stock.get('code', '')
        
        # 获取K线数据
        closes = None
        volumes = None
        if kline_data and code in kline_data:
            closes = kline_data[code].get('closes')
            volumes = kline_data[code].get('volumes')
        
        # 计算评分
        score_result = ScoringEngine.calculate_composite_score(stock, closes, volumes)
        results.append(score_result)
    
    # 按综合评分排序
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return results


def get_top_stocks(stocks: List[Dict], top_n: int = 3, 
                   min_score: float = 60) -> List[Dict]:
    """获取评分最高的股票
    
    Args:
        stocks: 已评分的股票列表
        top_n: 返回前N只
        min_score: 最低分数门槛
        
    Returns:
        排名前N的股票
    """
    filtered = [s for s in stocks if s.get('composite_score', 0) >= min_score]
    return filtered[:top_n]
