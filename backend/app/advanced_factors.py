"""高级因子模块 - Level 2数据因子、资金流因子、订单流因子

基于日线数据估算L2级别的高阶因子：
1. 主买/主卖净差（订单不平衡）
2. 挂单撤单比（取消比例）
3. 大单紧随因子
4. 资金流向因子
5. 市场微观结构因子
"""
import numpy as np
from typing import List, Dict, Optional
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
    amount: float = 0

class AdvancedFactors:
    """高级因子计算器"""
    
    @staticmethod
    def order_imbalance_factor(high: List[float], low: List[float], close: List[float], 
                               volume: List[float], period: int = 5) -> List[float]:
        """订单不平衡因子（估算主买/主卖净差）
        
        基于K线位置估算：
        - 收盘价在高位 → 主买力量强
        - 收盘价在低位 → 主卖力量强
        - 成交量放大 → 订单活跃度高
        """
        if len(close) < period:
            return [0] * len(close)
        
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(0)
                continue
            
            # 计算K线位置（0-1之间）
            hl_range = high[i] - low[i]
            if hl_range == 0:
                position = 0.5
            else:
                position = (close[i] - low[i]) / hl_range
            
            # 计算相对成交量
            avg_vol = np.mean(volume[max(0, i-period):i]) if i > 0 else volume[i]
            vol_ratio = volume[i] / avg_vol if avg_vol > 0 else 1
            
            # 订单不平衡 = K线位置 * 成交量比率
            # 正值表示主买，负值表示主卖
            imbalance = (position - 0.5) * 2 * vol_ratio
            result.append(round(imbalance, 4))
        
        return result
    
    @staticmethod
    def big_order_ratio(high: List[float], low: List[float], close: List[float],
                        volume: List[float], amount: List[float], 
                        period: int = 10) -> List[float]:
        """大单占比因子（估算机构大单动向）
        
        基于成交额/成交量推算平均单笔金额：
        - 平均单笔金额高 → 大单占比高 → 机构参与
        - 价格波动大 + 高单笔金额 → 可能是机构调仓
        """
        if len(amount) < period or len(volume) < period:
            return [0] * len(amount)
        
        result = []
        for i in range(len(amount)):
            if i < period - 1:
                result.append(0)
                continue
            
            # 计算平均单笔金额
            avg_trade_value = amount[i] / volume[i] if volume[i] > 0 else 0
            
            # 计算历史平均单笔金额
            hist_values = []
            for j in range(max(0, i-period), i):
                if volume[j] > 0:
                    hist_values.append(amount[j] / volume[j])
            
            if not hist_values:
                result.append(0)
                continue
            
            hist_avg = np.mean(hist_values)
            
            # 大单占比 = 当前单笔金额 / 历史平均
            # >1 表示大单增加，<1 表示散户增加
            ratio = avg_trade_value / hist_avg if hist_avg > 0 else 1
            
            # 归一化到 -1 到 1
            normalized = np.clip((ratio - 1) * 2, -1, 1)
            result.append(round(normalized, 4))
        
        return result
    
    @staticmethod
    def cancellation_ratio_proxy(high: List[float], low: List[float], close: List[float],
                                 volume: List[float], period: int = 5) -> List[float]:
        """挂单撤单比代理因子（基于价格波动估算）
        
        价格剧烈波动但成交量低 → 可能是挂单撤单频繁
        价格稳定但成交量高 → 实际成交多，撤单少
        """
        if len(close) < period:
            return [0] * len(close)
        
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(0)
                continue
            
            # 计算价格波动率
            prices = close[max(0, i-period):i+1]
            returns = [(prices[j] - prices[j-1]) / prices[j-1] for j in range(1, len(prices))]
            volatility = np.std(returns) if returns else 0
            
            # 计算成交量变化
            vols = volume[max(0, i-period):i+1]
            vol_change = (vols[-1] - np.mean(vols[:-1])) / np.mean(vols[:-1]) if np.mean(vols[:-1]) > 0 else 0
            
            # 撤单比 = 波动率高 + 成交量变化大 → 撤单频繁
            # 正值表示撤单多，负值表示实际成交多
            cancel_ratio = volatility * 100 - abs(vol_change)
            result.append(round(np.clip(cancel_ratio, -1, 1), 4))
        
        return result
    
    @staticmethod
    def smart_money_flow(high: List[float], low: List[float], close: List[float],
                         volume: List[float], period: int = 14) -> List[float]:
        """聪明资金流向因子
        
        基于Chaikin Money Flow改进：
        - 价格在高位收盘且成交量大 → 聪明钱流入
        - 价格在低位收盘且成交量大 → 聪明钱流出
        """
        if len(close) < period:
            return [0] * len(close)
        
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(0)
                continue
            
            mfm_values = []
            for j in range(i - period + 1, i + 1):
                hl_range = high[j] - low[j]
                if hl_range == 0:
                    mfm = 0
                else:
                    mfm = ((close[j] - low[j]) - (high[j] - close[j])) / hl_range
                mfm_values.append(mfm * volume[j])
            
            total_volume = sum(volume[i-period+1:i+1])
            if total_volume == 0:
                result.append(0)
            else:
                cmf = sum(mfm_values) / total_volume
                result.append(round(cmf, 4))
        
        return result
    
    @staticmethod
    def institutional_activity_score(open_price: List[float], high: List[float], 
                                     low: List[float], close: List[float],
                                     volume: List[float], period: int = 20) -> List[float]:
        """机构活跃度评分
        
        综合多个指标评估机构参与程度：
        - 大阳线/大阴线比例
        - 成交量集中度
        - 价格波动模式
        """
        if len(close) < period:
            return [0] * len(close)
        
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(0)
                continue
            
            scores = []
            for j in range(i - period + 1, i + 1):
                score = 0
                
                # 1. 实体大小（大阳/大阴 = 机构行为）
                body = abs(close[j] - open_price[j])
                hl_range = high[j] - low[j]
                if hl_range > 0:
                    body_ratio = body / hl_range
                    score += body_ratio * 0.3
                
                # 2. 成交量异常
                avg_vol = np.mean(volume[max(0, j-5):j]) if j > 0 else volume[j]
                if avg_vol > 0:
                    vol_ratio = volume[j] / avg_vol
                    if vol_ratio > 1.5:  # 放量
                        score += 0.3
                    elif vol_ratio < 0.5:  # 缩量
                        score -= 0.1
                
                # 3. 价格位置
                if hl_range > 0:
                    position = (close[j] - low[j]) / hl_range
                    score += (position - 0.5) * 0.2
                
                # 4. 跳空缺口
                if j > 0:
                    gap = open_price[j] - close[j-1]
                    if abs(gap) > high[j] * 0.01:  # 1%以上缺口
                        score += 0.2 * np.sign(gap)
                
                scores.append(score)
            
            avg_score = np.mean(scores) if scores else 0
            result.append(round(avg_score, 4))
        
        return result
    
    @staticmethod
    def market_microstructure噪音因子(open_price: List[float], high: List[float], low: List[float], close: List[float],
                                      volume: List[float], period: int = 10) -> List[float]:
        """市场微观结构噪音因子
        
        衡量市场噪音水平：
        - 高噪音 = 散户主导，假信号多
        - 低噪音 = 机构主导，趋势可靠
        """
        if len(close) < period:
            return [0] * len(close)
        
        result = []
        for i in range(len(close)):
            if i < period - 1:
                result.append(0)
                continue
            
            # 计算价格噪音（影线比例）
            noise_scores = []
            for j in range(i - period + 1, i + 1):
                body = abs(close[j] - open_price[j])
                upper_shadow = high[j] - max(close[j], open_price[j])
                lower_shadow = min(close[j], open_price[j]) - low[j]
                total_range = high[j] - low[j]
                
                if total_range > 0:
                    noise_ratio = (upper_shadow + lower_shadow) / total_range
                    noise_scores.append(noise_ratio)
            
            # 平均噪音水平
            avg_noise = np.mean(noise_scores) if noise_scores else 0
            
            # 归一化：高噪音 → 正值，低噪音 → 负值
            result.append(round(avg_noise * 2 - 1, 4))
        
        return result
    
    @staticmethod
    def calculate_all_advanced(klines: List[Kline]) -> Dict:
        """计算所有高级因子"""
        if not klines:
            return {}
        
        open_price = [k.open for k in klines]
        close = [k.close for k in klines]
        high = [k.high for k in klines]
        low = [k.low for k in klines]
        volume = [k.volume for k in klines]
        amount = [k.amount if k.amount else k.close * k.volume for k in klines]
        
        return {
            'order_imbalance': AdvancedFactors.order_imbalance_factor(high, low, close, volume),
            'big_order_ratio': AdvancedFactors.big_order_ratio(high, low, close, volume, amount),
            'cancellation_ratio': AdvancedFactors.cancellation_ratio_proxy(high, low, close, volume),
            'smart_money_flow': AdvancedFactors.smart_money_flow(high, low, close, volume),
            'institutional_activity': AdvancedFactors.institutional_activity_score(
                open_price, high, low, close, volume),
            'noise_factor': AdvancedFactors.market_microstructure噪音因子(open_price, high, low, close, volume),
        }


def calculate_advanced_factors(kline_data: List[Dict]) -> Dict:
    """计算高级因子"""
    klines = [Kline(**k) for k in kline_data]
    return AdvancedFactors.calculate_all_advanced(klines)
