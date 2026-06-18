"""Brinson业绩归因分析 - Alpha/Beta收益拆解

核心功能：
1. Brinson归因模型 - 资产配置效应、选股效应、交互效应
2. 行业轮动分析 - 行业配置贡献
3. 选股能力评估 - Alpha收益来源
4. 风险调整收益 - Sharpe、Sortino、Information Ratio
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class PortfolioHolding:
    """持仓记录"""
    code: str
    name: str
    weight: float  # 组合权重
    return_pct: float  # 个股收益率
    sector: str = "未知"  # 行业分类

@dataclass
class BenchmarkHolding:
    """基准持仓"""
    sector: str
    weight: float  # 基准权重
    return_pct: float  # 行业收益率

class BrinsonAttribution:
    """Brinson归因分析器"""
    
    @staticmethod
    def single_period_attribution(portfolio_holdings: List[PortfolioHolding],
                                   benchmark_holdings: List[BenchmarkHolding]) -> Dict:
        """单期Brinson归因
        
        将组合超额收益分解为：
        1. 资产配置效应 (Allocation Effect)
        2. 选股效应 (Selection Effect)
        3. 交互效应 (Interaction Effect)
        """
        # 按行业分组
        portfolio_sectors = {}
        for h in portfolio_holdings:
            if h.sector not in portfolio_sectors:
                portfolio_sectors[h.sector] = []
            portfolio_sectors[h.sector].append(h)
        
        benchmark_sectors = {}
        for b in benchmark_holdings:
            if b.sector not in benchmark_sectors:
                benchmark_sectors[b.sector] = []
            benchmark_sectors[b.sector].append(b)
        
        # 计算组合和基准的总收益率
        portfolio_return = sum(h.weight * h.return_pct for h in portfolio_holdings)
        benchmark_return = sum(b.weight * b.return_pct for b in benchmark_holdings)
        excess_return = portfolio_return - benchmark_return
        
        # 计算行业级效应
        allocation_effect = 0
        selection_effect = 0
        interaction_effect = 0
        
        sector_contributions = []
        
        all_sectors = set(list(portfolio_sectors.keys()) + list(benchmark_sectors.keys()))
        
        for sector in all_sectors:
            # 组合在该行业的权重和收益
            p_holdings = portfolio_sectors.get(sector, [])
            p_weight = sum(h.weight for h in p_holdings)
            p_return = sum(h.weight * h.return_pct for h in p_holdings) / p_weight if p_weight > 0 else 0
            
            # 基准在该行业的权重和收益
            b_holdings = benchmark_sectors.get(sector, [])
            b_weight = sum(b.weight for b in b_holdings)
            b_return = sum(b.weight * b.return_pct for b in b_holdings) / b_weight if b_weight > 0 else 0
            
            # Brinson公式
            # 资产配置效应 = (p_weight - b_weight) * (b_return - benchmark_return)
            alloc = (p_weight - b_weight) * (b_return - benchmark_return)
            
            # 选股效应 = b_weight * (p_return - b_return)
            select = b_weight * (p_return - b_return)
            
            # 交互效应 = (p_weight - b_weight) * (p_return - b_return)
            interact = (p_weight - b_weight) * (p_return - b_return)
            
            allocation_effect += alloc
            selection_effect += select
            interaction_effect += interact
            
            sector_contributions.append({
                'sector': sector,
                'portfolio_weight': round(p_weight * 100, 2),
                'benchmark_weight': round(b_weight * 100, 2),
                'portfolio_return': round(p_return * 100, 2),
                'benchmark_return': round(b_return * 100, 2),
                'allocation_effect': round(alloc * 100, 4),
                'selection_effect': round(select * 100, 4),
                'interaction_effect': round(interact * 100, 4),
                'total_effect': round((alloc + select + interact) * 100, 4),
            })
        
        return {
            'portfolio_return': round(portfolio_return * 100, 2),
            'benchmark_return': round(benchmark_return * 100, 2),
            'excess_return': round(excess_return * 100, 2),
            'allocation_effect': round(allocation_effect * 100, 4),
            'selection_effect': round(selection_effect * 100, 4),
            'interaction_effect': round(interaction_effect * 100, 4),
            'total_attribution': round((allocation_effect + selection_effect + interaction_effect) * 100, 4),
            'sector_contributions': sorted(sector_contributions, 
                                           key=lambda x: abs(x['total_effect']), 
                                           reverse=True),
        }
    
    @staticmethod
    def multi_period_attribution(period_results: List[Dict]) -> Dict:
        """多期Brinson归因（链式分解）"""
        if not period_results:
            return {}
        
        # 累计各期效应
        total_allocation = sum(r.get('allocation_effect', 0) for r in period_results)
        total_selection = sum(r.get('selection_effect', 0) for r in period_results)
        total_interaction = sum(r.get('interaction_effect', 0) for r in period_results)
        total_excess = sum(r.get('excess_return', 0) for r in period_results)
        
        # 计算各效应占比
        total_effects = abs(total_allocation) + abs(total_selection) + abs(total_interaction)
        
        return {
            'periods': len(period_results),
            'total_allocation_effect': round(total_allocation, 4),
            'total_selection_effect': round(total_selection, 4),
            'total_interaction_effect': round(total_interaction, 4),
            'total_excess_return': round(total_excess, 2),
            'allocation_ratio': round(abs(total_allocation) / total_effects * 100, 2) if total_effects > 0 else 0,
            'selection_ratio': round(abs(total_selection) / total_effects * 100, 2) if total_effects > 0 else 0,
            'interaction_ratio': round(abs(total_interaction) / total_effects * 100, 2) if total_effects > 0 else 0,
        }
    
    @staticmethod
    def risk_adjusted_metrics(returns: List[float], benchmark_returns: List[float] = None,
                               risk_free_rate: float = 0.03) -> Dict:
        """风险调整收益指标"""
        if not returns:
            return {}
        
        returns_arr = np.array(returns)
        
        # 基础统计
        total_return = np.prod(1 + returns_arr) - 1
        avg_return = np.mean(returns_arr)
        volatility = np.std(returns_arr) * np.sqrt(252)  # 年化波动率
        
        # Sharpe Ratio
        excess_return = avg_return * 252 - risk_free_rate
        sharpe = excess_return / volatility if volatility > 0 else 0
        
        # Sortino Ratio（只考虑下行风险）
        downside_returns = returns_arr[returns_arr < 0]
        downside_vol = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino = excess_return / downside_vol if downside_vol > 0 else 0
        
        # 最大回撤
        cumulative = np.cumprod(1 + returns_arr)
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_drawdown = np.min(drawdown) * 100
        
        # Calmar Ratio
        calmar = (total_return * 100) / abs(max_drawdown) if max_drawdown != 0 else 0
        
        result = {
            'total_return': round(total_return * 100, 2),
            'annualized_return': round(avg_return * 252 * 100, 2),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe, 3),
            'sortino_ratio': round(sortino, 3),
            'max_drawdown': round(max_drawdown, 2),
            'calmar_ratio': round(calmar, 3),
        }
        
        # 如果有基准收益，计算Information Ratio
        if benchmark_returns and len(benchmark_returns) == len(returns):
            benchmark_arr = np.array(benchmark_returns)
            active_returns = returns_arr - benchmark_arr
            tracking_error = np.std(active_returns) * np.sqrt(252)
            info_ratio = np.mean(active_returns) * 252 / tracking_error if tracking_error > 0 else 0
            result['information_ratio'] = round(info_ratio, 3)
            result['tracking_error'] = round(tracking_error * 100, 2)
        
        return result


def analyze_portfolio_attribution(holdings: List[Dict], benchmark: List[Dict] = None) -> Dict:
    """分析组合归因
    
    Args:
        holdings: 组合持仓列表 [{code, name, weight, return_pct, sector}]
        benchmark: 基准持仓列表 [{sector, weight, return_pct}]
        
    Returns:
        归因分析结果
    """
    # 转换为数据对象
    portfolio_holdings = [PortfolioHolding(**h) for h in holdings]
    
    if benchmark:
        benchmark_holdings = [BenchmarkHolding(**b) for b in benchmark]
    else:
        # 使用默认基准（全市场等权）
        sectors = list(set(h.sector for h in portfolio_holdings))
        if not sectors:
            sectors = ["未知"]
        n_sectors = len(sectors)
        benchmark_holdings = [
            BenchmarkHolding(sector=s, weight=1.0/n_sectors, return_pct=0.001)
            for s in sectors
        ]
    
    # 执行Brinson归因
    attribution = BrinsonAttribution.single_period_attribution(
        portfolio_holdings, benchmark_holdings
    )
    
    # 计算风险调整收益
    returns = [h.return_pct for h in portfolio_holdings]
    risk_metrics = BrinsonAttribution.risk_adjusted_metrics(returns)
    
    return {
        'attribution': attribution,
        'risk_metrics': risk_metrics,
        'summary': {
            'total_return': attribution['portfolio_return'],
            'benchmark_return': attribution['benchmark_return'],
            'alpha': attribution['excess_return'],
            'main_driver': '选股' if abs(attribution['selection_effect']) > abs(attribution['allocation_effect']) else '配置',
        },
    }


def generate_attribution_radar(attribution: Dict) -> Dict:
    """生成归因雷达图数据"""
    if not attribution:
        return {}
    
    # 提取各效应的绝对值作为雷达图维度
    alloc = abs(attribution.get('allocation_effect', 0))
    select = abs(attribution.get('selection_effect', 0))
    interact = abs(attribution.get('interaction_effect', 0))
    
    total = alloc + select + interact if (alloc + select + interact) > 0 else 1
    
    return {
        'dimensions': [
            {'name': '资产配置', 'value': round(alloc / total * 100, 1)},
            {'name': '选股能力', 'value': round(select / total * 100, 1)},
            {'name': '交互效应', 'value': round(interact / total * 100, 1)},
        ],
        'score': round(max(alloc, select, interact) / total * 100, 1) if total > 0 else 0,
    }
