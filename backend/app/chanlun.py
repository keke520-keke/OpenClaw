"""缠论分析模块 - 基于K线数据的缠论技术分析

核心概念：
1. 分型：顶分型和底分型
2. 笔：连接相邻顶底分型的最小单位
3. 线段：至少3笔组成
4. 中枢：至少3个线段/笔的重叠区域
5. 买卖点：一买/二买/三买、一卖/二卖/三卖
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class FxType(Enum):
    """分型类型"""
    TOP = 1      # 顶分型
    BOTTOM = -1  # 底分型

class BiType(Enum):
    """笔类型"""
    UP = 1    # 上升笔
    DOWN = -1 # 下降笔

@dataclass
class Kline:
    """K线数据"""
    date: str
    open: float
    close: float
    high: float
    low: float
    volume: float = 0
    
    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2

@dataclass
class Fx:
    """分型"""
    index: int        # K线位置
    kline: Kline      # 分型K线
    fx_type: FxType   # 分型类型
    price: float      # 分型价格（顶分型取high，底分型取low）
    
@dataclass
class Bi:
    """笔"""
    start: Fx    # 起点分型
    end: Fx      # 终点分型
    bi_type: BiType  # 笔类型
    
    @property
    def high(self) -> float:
        return max(self.start.price, self.end.price)
    
    @property
    def low(self) -> float:
        return min(self.start.price, self.end.price)
    
    @property
    def direction(self) -> int:
        return self.bi_type.value

@dataclass
class XianDuan:
    """线段"""
    start_bi: Bi   # 起始笔
    end_bi: Bi     # 结束笔
    bis: List[Bi]  # 包含的所有笔
    
    @property
    def high(self) -> float:
        return max(b.high for b in self.bis)
    
    @property
    def low(self) -> float:
        return min(b.low for b in self.bis)

@dataclass
class ZhongShu:
    """中枢"""
    bis: List[Bi]      # 构成中枢的笔
    high: float        # 中枢上沿
    low: float         # 中枢下沿
    level: int = 1     # 中枢级别
    
    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2
    
    @property
    def amplitude(self) -> float:
        return self.high - self.low

class ChanLunAnalyzer:
    """缠论分析器"""
    
    def __init__(self, klines: List[Kline] = None):
        self.klines: List[Kline] = klines or []
        self.fx_list: List[Fx] = []   # 分型列表
        self.bi_list: List[Bi] = []   # 笔列表
        self.xd_list: List[XianDuan] = []  # 线段列表
        self.zs_list: List[ZhongShu] = []  # 中枢列表
        
    def set_klines(self, klines: List[Kline]):
        """设置K线数据"""
        self.klines = klines
        self.analyze()
    
    def analyze(self):
        """执行完整缠论分析"""
        if len(self.klines) < 5:
            return
        
        # 1. 包含处理
        processed = self._process_inclusion()
        
        # 2. 识别分型
        self.fx_list = self._find_fenxing(processed)
        
        # 3. 构建笔
        self.bi_list = self._build_bi()
        
        # 4. 构建线段
        self.xd_list = self._build_xianduan()
        
        # 5. 识别中枢
        self.zs_list = self._find_zhongshu()
    
    def _process_inclusion(self) -> List[Kline]:
        """K线包含处理"""
        if len(self.klines) < 2:
            return self.klines.copy()
        
        result = [self.klines[0]]
        
        for i in range(1, len(self.klines)):
            curr = self.klines[i]
            prev = result[-1]
            
            # 判断包含关系
            if (prev.high >= curr.high and prev.low <= curr.low) or \
               (curr.high >= prev.high and curr.low <= prev.low):
                # 包含处理：根据趋势方向决定合并方式
                if i + 1 < len(self.klines):
                    next_k = self.klines[i + 1]
                    trend_up = curr.close > prev.close
                else:
                    trend_up = curr.close > prev.close
                
                if trend_up:
                    # 上升趋势取高点
                    new_high = max(prev.high, curr.high)
                    new_low = max(prev.low, curr.low)
                else:
                    # 下降趋势取低点
                    new_high = min(prev.high, curr.high)
                    new_low = min(prev.low, curr.low)
                
                result[-1] = Kline(
                    date=prev.date, open=prev.open,
                    close=curr.close, high=new_high, low=new_low
                )
            else:
                result.append(curr)
        
        return result
    
    def _find_fenxing(self, klines: List[Kline]) -> List[Fx]:
        """识别顶分型和底分型"""
        fx_list = []
        
        for i in range(1, len(klines) - 1):
            prev, curr, next_k = klines[i-1], klines[i], klines[i+1]
            
            # 顶分型：中间K线高点最高
            if curr.high > prev.high and curr.high > next_k.high:
                fx_list.append(Fx(
                    index=i, kline=curr,
                    fx_type=FxType.TOP, price=curr.high
                ))
            
            # 底分型：中间K线低点最低
            if curr.low < prev.low and curr.low < next_k.low:
                fx_list.append(Fx(
                    index=i, kline=curr,
                    fx_type=FxType.BOTTOM, price=curr.low
                ))
        
        return fx_list
    
    def _build_bi(self) -> List[Bi]:
        """构建笔（连接相邻顶底分型）"""
        if len(self.fx_list) < 2:
            return []
        
        bis = []
        last_fx = self.fx_list[0]
        
        for i in range(1, len(self.fx_list)):
            curr_fx = self.fx_list[i]
            
            # 笔必须连接不同类型的分型
            if curr_fx.fx_type == last_fx.fx_type:
                # 同类型分型，保留更极端的
                if curr_fx.fx_type == FxType.TOP and curr_fx.price > last_fx.price:
                    last_fx = curr_fx
                elif curr_fx.fx_type == FxType.BOTTOM and curr_fx.price < last_fx.price:
                    last_fx = curr_fx
                continue
            
            # 笔至少包含5根K线（包含处理后）
            if curr_fx.index - last_fx.index < 4:
                continue
            
            # 确定笔的方向
            if last_fx.fx_type == FxType.BOTTOM and curr_fx.fx_type == FxType.TOP:
                bi_type = BiType.UP
            elif last_fx.fx_type == FxType.TOP and curr_fx.fx_type == FxType.BOTTOM:
                bi_type = BiType.DOWN
            else:
                last_fx = curr_fx
                continue
            
            bis.append(Bi(start=last_fx, end=curr_fx, bi_type=bi_type))
            last_fx = curr_fx
        
        return bis
    
    def _build_xianduan(self) -> List[XianDuan]:
        """构建线段（至少3笔）"""
        if len(self.bi_list) < 3:
            return []
        
        xianduans = []
        i = 0
        
        while i + 2 < len(self.bi_list):
            # 检查是否形成线段
            bi1, bi2, bi3 = self.bi_list[i], self.bi_list[i+1], self.bi_list[i+2]
            
            # 线段的条件：至少3笔，且方向一致
            if bi1.bi_type == bi3.bi_type:
                xd = XianDuan(
                    start_bi=bi1,
                    end_bi=bi3,
                    bis=[bi1, bi2, bi3]
                )
                xianduans.append(xd)
                i += 3
            else:
                i += 1
        
        return xianduans
    
    def _find_zhongshu(self) -> List[ZhongShu]:
        """识别中枢（至少3笔的重叠区域）"""
        if len(self.bi_list) < 3:
            return []
        
        zhongshus = []
        i = 0
        
        while i + 2 < len(self.bi_list):
            bi1, bi2, bi3 = self.bi_list[i], self.bi_list[i+1], self.bi_list[i+2]
            
            # 计算重叠区域
            overlap_high = min(bi1.high, bi2.high, bi3.high)
            overlap_low = max(bi1.low, bi2.low, bi3.low)
            
            # 存在重叠区域才形成中枢
            if overlap_high > overlap_low:
                zs = ZhongShu(
                    bis=[bi1, bi2, bi3],
                    high=overlap_high,
                    low=overlap_low
                )
                zhongshus.append(zs)
                i += 3
            else:
                i += 1
        
        return zhongshus
    
    def get_support_resistance(self) -> Dict:
        """获取支撑位和压力位"""
        result = {
            'support': [],      # 支撑位列表
            'resistance': [],   # 压力位列表
            'zhongshu': [],     # 中枢信息
        }
        
        # 中枢作为支撑压力
        for zs in self.zs_list:
            result['zhongshu'].append({
                'high': zs.high,
                'low': zs.low,
                'mid': zs.mid,
            })
            result['support'].append(zs.low)
            result['resistance'].append(zs.high)
        
        # 笔的端点作为支撑压力
        for bi in self.bi_list[-5:]:  # 最近5笔
            if bi.bi_type == BiType.UP:
                result['support'].append(bi.low)
            else:
                result['resistance'].append(bi.high)
        
        # 去重并排序
        result['support'] = sorted(set(result['support']))
        result['resistance'] = sorted(set(result['resistance']), reverse=True)
        
        return result
    
    def find买卖点(self, current_price: float) -> Dict:
        """寻找买卖点"""
        signals = {
            'buy': [],   # 买点信号
            'sell': [],  # 卖点信号
        }
        
        if not self.bi_list or not self.zs_list:
            return signals
        
        # 最后一笔的方向
        last_bi = self.bi_list[-1]
        
        # 获取当前中枢
        if self.zs_list:
            current_zs = self.zs_list[-1]
            
            # 一买：下跌趋势背驰后，价格低于中枢下沿
            if last_bi.bi_type == BiType.DOWN:
                if current_price < current_zs.low:
                    # 检查是否背驰（简化判断）
                    if len(self.bi_list) >= 3:
                        prev_down = [b for b in self.bi_list[-4:-1] if b.bi_type == BiType.DOWN]
                        if prev_down:
                            last_range = last_bi.high - last_bi.low
                            prev_range = prev_down[-1].high - prev_down[-1].low
                            if last_range < prev_range:  # 力度减弱
                                signals['buy'].append({
                                    'type': '一买',
                                    'price': current_price,
                                    'reason': '下跌背驰，价格低于中枢下沿'
                                })
            
            # 一卖：上涨趋势背驰后，价格高于中枢上沿
            if last_bi.bi_type == BiType.UP:
                if current_price > current_zs.high:
                    # 检查是否背驰
                    if len(self.bi_list) >= 3:
                        prev_up = [b for b in self.bi_list[-4:-1] if b.bi_type == BiType.UP]
                        if prev_up:
                            last_range = last_bi.high - last_bi.low
                            prev_range = prev_up[-1].high - prev_up[-1].low
                            if last_range < prev_range:  # 力度减弱
                                signals['sell'].append({
                                    'type': '一卖',
                                    'price': current_price,
                                    'reason': '上涨背驰，价格高于中枢上沿'
                                })
            
            # 二买：回调不破中枢低点
            if last_bi.bi_type == BiType.DOWN:
                if current_price > current_zs.low and current_price < current_zs.mid:
                    signals['buy'].append({
                        'type': '二买',
                        'price': current_price,
                        'reason': '回调不破中枢低点'
                    })
            
            # 二卖：反弹不破中枢高点
            if last_bi.bi_type == BiType.UP:
                if current_price < current_zs.high and current_price > current_zs.mid:
                    signals['sell'].append({
                        'type': '二卖',
                        'price': current_price,
                        'reason': '反弹不破中枢高点'
                    })
            
            # 三买：价格突破中枢上沿后回踩不破
            if last_bi.bi_type == BiType.DOWN:
                if len(self.bi_list) >= 2:
                    prev_bi = self.bi_list[-2]
                    if prev_bi.bi_type == BiType.UP and prev_bi.high > current_zs.high:
                        if current_price > current_zs.high:
                            signals['buy'].append({
                                'type': '三买',
                                'price': current_price,
                                'reason': '突破中枢上沿后回踩确认'
                            })
            
            # 三卖：价格跌破中枢下沿后反弹不破
            if last_bi.bi_type == BiType.UP:
                if len(self.bi_list) >= 2:
                    prev_bi = self.bi_list[-2]
                    if prev_bi.bi_type == BiType.DOWN and prev_bi.low < current_zs.low:
                        if current_price < current_zs.low:
                            signals['sell'].append({
                                'type': '三卖',
                                'price': current_price,
                                'reason': '跌破中枢下沿后反弹确认'
                            })
        
        return signals
    
    def get_trend(self) -> str:
        """判断当前趋势"""
        if not self.zs_list:
            return 'unknown'
        
        if len(self.zs_list) < 2:
            return 'consolidation'
        
        # 比较最近两个中枢
        zs1 = self.zs_list[-2]
        zs2 = self.zs_list[-1]
        
        if zs2.low > zs1.high:
            return 'up'  # 上涨趋势
        elif zs2.high < zs1.low:
            return 'down'  # 下跌趋势
        else:
            return 'consolidation'  # 盘整
    
    def get_summary(self) -> Dict:
        """获取缠论分析摘要"""
        trend = self.get_trend()
        sr = self.get_support_resistance()
        
        return {
            'trend': trend,
            'trend_cn': {
                'up': '上涨趋势',
                'down': '下跌趋势',
                'consolidation': '盘整',
                'unknown': '未知'
            }.get(trend, '未知'),
            'bi_count': len(self.bi_list),
            'xd_count': len(self.xd_list),
            'zs_count': len(self.zs_list),
            'support': sr['support'][:3],  # 前3个支撑位
            'resistance': sr['resistance'][:3],  # 前3个压力位
            'current_zs': {
                'high': self.zs_list[-1].high,
                'low': self.zs_list[-1].low,
                'mid': self.zs_list[-1].mid,
            } if self.zs_list else None,
        }


def analyze_klines(kline_data: List[Dict]) -> Dict:
    """分析K线数据，返回缠论结果
    
    Args:
        kline_data: K线数据列表，每项包含 date, open, close, high, low, volume
    
    Returns:
        缠论分析结果
    """
    # 转换K线数据
    klines = [Kline(**k) for k in kline_data]
    
    # 创建分析器并执行分析
    analyzer = ChanLunAnalyzer(klines)
    analyzer.analyze()  # 关键：必须调用analyze方法
    
    # 获取摘要
    summary = analyzer.get_summary()
    
    # 获取当前价格（最后一根K线）
    current_price = klines[-1].close if klines else 0
    
    # 获取买卖点信号
    signals = analyzer.find买卖点(current_price)
    
    return {
        'summary': summary,
        'signals': signals,
        'zhongshu': [{'high': zs.high, 'low': zs.low, 'mid': zs.mid} 
                     for zs in analyzer.zs_list[-3:]],  # 最近3个中枢
        'bi_count': len(analyzer.bi_list),
        'current_price': current_price,
    }
