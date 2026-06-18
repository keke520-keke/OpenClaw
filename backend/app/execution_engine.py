"""算法交易执行引擎 - 智能拆单、TWAP/VWAP、冰山订单

核心功能：
1. TWAP - 时间加权平均价格算法
2. VWAP - 成交量加权平均价格算法
3. 冰山订单 - 隐藏真实订单量
4. 智能拆单 - 大单拆分成小单
5. 执行成本分析 - 滑点和冲击成本估算
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time
import threading

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

@dataclass
class OrderSlice:
    """订单分片"""
    slice_id: int
    quantity: int
    price: float
    side: OrderSide
    status: str = "pending"  # pending, filled, cancelled
    timestamp: float = 0
    fill_price: float = 0
    
    def to_dict(self):
        return {
            'slice_id': self.slice_id,
            'quantity': self.quantity,
            'price': self.price,
            'side': self.side.value,
            'status': self.status,
            'timestamp': self.timestamp,
            'fill_price': self.fill_price,
        }

class ExecutionEngine:
    """算法交易执行引擎"""
    
    def __init__(self):
        self.slices: List[OrderSlice] = []
        self.total_filled = 0
        self.total_cost = 0
        self._lock = threading.Lock()
    
    def twap(self, total_quantity: int, side: OrderSide, 
             duration_seconds: int = 300, n_slices: int = 10,
             current_price: float = 0, price_variance: float = 0.002) -> List[Dict]:
        """TWAP算法 - 时间加权平均价格
        
        将大单均匀拆分成小单，在指定时间内均匀执行
        
        Args:
            total_quantity: 总数量
            side: 买卖方向
            duration_seconds: 执行持续时间（秒）
            n_slices: 拆分数量
            current_price: 当前价格
            price_variance: 价格波动范围（百分比）
            
        Returns:
            订单分片列表
        """
        slice_quantity = total_quantity // n_slices
        remainder = total_quantity % n_slices
        
        interval = duration_seconds / n_slices
        
        slices = []
        for i in range(n_slices):
            qty = slice_quantity + (1 if i < remainder else 0)
            
            # 添加价格波动模拟真实执行
            price_offset = np.random.uniform(-price_variance, price_variance)
            exec_price = current_price * (1 + price_offset)
            
            slice_obj = OrderSlice(
                slice_id=i,
                quantity=qty,
                price=round(exec_price, 2),
                side=side,
                timestamp=time.time() + i * interval,
            )
            slices.append(slice_obj.to_dict())
        
        with self._lock:
            self.slices.extend([OrderSlice(**s) for s in slices])
        
        return slices
    
    def vwap(self, total_quantity: int, side: OrderSide,
             volume_profile: List[float], current_price: float = 0,
             price_variance: float = 0.002) -> List[Dict]:
        """VWAP算法 - 成交量加权平均价格
        
        根据历史成交量分布拆单，成交量大的时段多执行
        
        Args:
            total_quantity: 总数量
            side: 买卖方向
            volume_profile: 成交量分布（归一化）
            current_price: 当前价格
            price_variance: 价格波动范围
            
        Returns:
            订单分片列表
        """
        if not volume_profile:
            volume_profile = [1.0] * 10
        
        # 归一化成交量分布
        total_vol = sum(volume_profile)
        if total_vol == 0:
            volume_profile = [1.0 / len(volume_profile)] * len(volume_profile)
        else:
            volume_profile = [v / total_vol for v in volume_profile]
        
        # 按成交量分配数量
        slices = []
        remaining = total_quantity
        
        for i, vol_weight in enumerate(volume_profile):
            qty = int(total_quantity * vol_weight)
            if i == len(volume_profile) - 1:
                qty = remaining  # 最后一个分片处理余数
            
            if qty <= 0:
                continue
            
            remaining -= qty
            
            # 价格波动
            price_offset = np.random.uniform(-price_variance, price_variance)
            exec_price = current_price * (1 + price_offset)
            
            slice_obj = OrderSlice(
                slice_id=i,
                quantity=qty,
                price=round(exec_price, 2),
                side=side,
                timestamp=time.time() + i * 60,  # 假设每分钟一个分片
            )
            slices.append(slice_obj.to_dict())
        
        with self._lock:
            self.slices.extend([OrderSlice(**s) for s in slices])
        
        return slices
    
    def iceberg(self, total_quantity: int, side: OrderSide,
                visible_quantity: int = 100, current_price: float = 0,
                price_variance: float = 0.001) -> List[Dict]:
        """冰山订单算法
        
        只显示一小部分订单，成交后自动补充
        
        Args:
            total_quantity: 总数量
            side: 买卖方向
            visible_quantity: 每次显示的数量
            current_price: 当前价格
            price_variance: 价格波动范围
            
        Returns:
            订单分片列表
        """
        slices = []
        remaining = total_quantity
        slice_id = 0
        
        while remaining > 0:
            qty = min(visible_quantity, remaining)
            remaining -= qty
            
            price_offset = np.random.uniform(-price_variance, price_variance)
            exec_price = current_price * (1 + price_offset)
            
            slice_obj = OrderSlice(
                slice_id=slice_id,
                quantity=qty,
                price=round(exec_price, 2),
                side=side,
                timestamp=time.time() + slice_id * 5,  # 每5秒一个分片
            )
            slices.append(slice_obj.to_dict())
            slice_id += 1
        
        with self._lock:
            self.slices.extend([OrderSlice(**s) for s in slices])
        
        return slices
    
    def smart_split(self, total_quantity: int, side: OrderSide,
                    current_price: float, max_slice_value: float = 50000,
                    price_variance: float = 0.002) -> List[Dict]:
        """智能拆单
        
        根据金额限制自动拆分订单
        
        Args:
            total_quantity: 总数量
            side: 买卖方向
            current_price: 当前价格
            max_slice_value: 每个分片最大金额
            price_variance: 价格波动范围
            
        Returns:
            订单分片列表
        """
        total_value = total_quantity * current_price
        
        if total_value <= max_slice_value:
            # 不需要拆分
            return [{
                'slice_id': 0,
                'quantity': total_quantity,
                'price': round(current_price, 2),
                'side': side.value,
                'status': 'pending',
                'timestamp': time.time(),
            }]
        
        # 计算需要拆分的数量
        n_slices = int(np.ceil(total_value / max_slice_value))
        slice_quantity = total_quantity // n_slices
        remainder = total_quantity % n_slices
        
        slices = []
        for i in range(n_slices):
            qty = slice_quantity + (1 if i < remainder else 0)
            
            price_offset = np.random.uniform(-price_variance, price_variance)
            exec_price = current_price * (1 + price_offset)
            
            slice_obj = OrderSlice(
                slice_id=i,
                quantity=qty,
                price=round(exec_price, 2),
                side=side,
                timestamp=time.time() + i * 10,  # 每10秒一个分片
            )
            slices.append(slice_obj.to_dict())
        
        with self._lock:
            self.slices.extend([OrderSlice(**s) for s in slices])
        
        return slices
    
    def estimate_execution_cost(self, total_quantity: int, current_price: float,
                                 side: OrderSide, avg_volume: float = 1000000) -> Dict:
        """估算执行成本
        
        Args:
            total_quantity: 总数量
            current_price: 当前价格
            side: 买卖方向
            avg_volume: 平均日成交量
            
        Returns:
            执行成本估算
        """
        total_value = total_quantity * current_price
        
        # 市场冲击成本估算（基于参与率）
        participation_rate = total_quantity / avg_volume if avg_volume > 0 else 0
        market_impact = participation_rate * 0.1 * current_price  # 简化模型
        
        # 滑点估算
        slippage_rate = min(0.001 * (total_value / 100000), 0.01)  # 最大1%
        slippage = slippage_rate * current_price * total_quantity
        
        # 佣金估算
        commission_rate = 0.00025  # 万2.5
        commission = total_value * commission_rate
        
        # 总成本
        total_cost = market_impact + slippage + commission
        
        # 建议执行时间
        if participation_rate > 0.1:
            suggested_duration = "60分钟以上"
            suggested_method = "VWAP"
        elif participation_rate > 0.05:
            suggested_duration = "30-60分钟"
            suggested_method = "TWAP"
        else:
            suggested_duration = "5-10分钟"
            suggested_method = "智能拆单"
        
        return {
            'total_quantity': total_quantity,
            'total_value': round(total_value, 2),
            'market_impact': round(market_impact, 2),
            'slippage': round(slippage, 2),
            'commission': round(commission, 2),
            'total_cost': round(total_cost, 2),
            'cost_ratio': round(total_cost / total_value * 100, 4) if total_value > 0 else 0,
            'participation_rate': round(participation_rate * 100, 2),
            'suggested_method': suggested_method,
            'suggested_duration': suggested_duration,
        }
    
    def get_execution_summary(self) -> Dict:
        """获取执行摘要"""
        with self._lock:
            if not self.slices:
                return {'total_slices': 0, 'status': 'no_orders'}
            
            filled_slices = [s for s in self.slices if s.status == 'filled']
            pending_slices = [s for s in self.slices if s.status == 'pending']
            
            total_quantity = sum(s.quantity for s in self.slices)
            filled_quantity = sum(s.quantity for s in filled_slices)
            
            avg_fill_price = 0
            if filled_slices:
                total_cost = sum(s.fill_price * s.quantity for s in filled_slices)
                avg_fill_price = total_cost / filled_quantity if filled_quantity > 0 else 0
            
            return {
                'total_slices': len(self.slices),
                'filled_slices': len(filled_slices),
                'pending_slices': len(pending_slices),
                'total_quantity': total_quantity,
                'filled_quantity': filled_quantity,
                'fill_rate': round(filled_quantity / total_quantity * 100, 2) if total_quantity > 0 else 0,
                'avg_fill_price': round(avg_fill_price, 2),
            }


# 全局执行引擎实例
execution_engine = ExecutionEngine()


def create_twap_order(quantity: int, side: str, duration: int = 300, 
                      price: float = 0) -> Dict:
    """创建TWAP订单"""
    order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
    slices = execution_engine.twap(quantity, order_side, duration, 10, price)
    return {
        'method': 'TWAP',
        'slices': slices,
        'total_slices': len(slices),
    }


def create_vwap_order(quantity: int, side: str, 
                      volume_profile: List[float] = None,
                      price: float = 0) -> Dict:
    """创建VWAP订单"""
    order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
    if volume_profile is None:
        # 模拟典型成交量分布（开盘和收盘量大）
        volume_profile = [1.5, 1.2, 1.0, 0.9, 0.8, 0.7, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5]
    slices = execution_engine.vwap(quantity, order_side, volume_profile, price)
    return {
        'method': 'VWAP',
        'slices': slices,
        'total_slices': len(slices),
    }


def create_iceberg_order(quantity: int, side: str, 
                         visible: int = 100, price: float = 0) -> Dict:
    """创建冰山订单"""
    order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
    slices = execution_engine.iceberg(quantity, order_side, visible, price)
    return {
        'method': 'Iceberg',
        'slices': slices,
        'total_slices': len(slices),
    }


def estimate_cost(quantity: int, price: float, side: str) -> Dict:
    """估算执行成本"""
    order_side = OrderSide.BUY if side == 'buy' else OrderSide.SELL
    return execution_engine.estimate_execution_cost(quantity, price, order_side)
