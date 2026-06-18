"""NLP舆情分析模块 - 情绪热度因子、关键词频次、情感分析

核心功能：
1. 情绪热度评分 - 基于关键词频次
2. 情感分析 - 正面/负面/中性
3. 行业舆情监控 - 行业热度趋势
4. 催化剂检测 - 热度突增信号
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import re

class SentimentAnalyzer:
    """情感分析器"""
    
    # 正面关键词
    POSITIVE_WORDS = {
        '利好', '上涨', '突破', '新高', '增长', '盈利', '超预期', '强势',
        '涨停', '放量', '资金流入', '主力加仓', '业绩增长', '订单增长',
        '政策支持', '行业景气', '估值修复', '底部反弹', '趋势向上',
    }
    
    # 负面关键词
    NEGATIVE_WORDS = {
        '利空', '下跌', '破位', '新低', '亏损', '下滑', '不及预期', '弱势',
        '跌停', '缩量', '资金流出', '主力减仓', '业绩下滑', '订单减少',
        '政策收紧', '行业低迷', '估值过高', '顶部回落', '趋势向下',
    }
    
    # 行业关键词
    SECTOR_KEYWORDS = {
        '半导体': ['芯片', '半导体', '集成电路', '光刻', '晶圆', '封测'],
        '新能源': ['光伏', '风电', '锂电', '储能', '新能源', '电动车'],
        '医药': ['创新药', '医药', '生物', '疫苗', '医疗', 'CRO'],
        '消费': ['白酒', '食品', '家电', '消费', '零售', '餐饮'],
        '金融': ['银行', '券商', '保险', '金融', '证券', '信托'],
        '科技': ['人工智能', 'AI', '云计算', '大数据', '5G', '物联网'],
        '地产': ['房地产', '地产', '楼市', '房价', '土地'],
    }
    
    @staticmethod
    def calculate_keyword_score(text: str, positive_words: set = None, 
                                 negative_words: set = None) -> Dict:
        """计算关键词情感得分"""
        if positive_words is None:
            positive_words = SentimentAnalyzer.POSITIVE_WORDS
        if negative_words is None:
            negative_words = SentimentAnalyzer.NEGATIVE_WORDS
        
        positive_count = sum(1 for w in positive_words if w in text)
        negative_count = sum(1 for w in negative_words if w in text)
        
        total = positive_count + negative_count
        if total == 0:
            score = 0
            sentiment = 'neutral'
        else:
            score = (positive_count - negative_count) / total
            sentiment = 'positive' if score > 0.2 else 'negative' if score < -0.2 else 'neutral'
        
        return {
            'score': round(score, 3),
            'sentiment': sentiment,
            'positive_count': positive_count,
            'negative_count': negative_count,
        }
    
    @staticmethod
    def calculate_heat_score(texts: List[str], keywords: List[str] = None) -> Dict:
        """计算热度得分
        
        基于关键词在文本中的出现频次
        """
        if not texts:
            return {'heat_score': 0, 'keyword_freq': {}}
        
        if keywords is None:
            # 使用所有行业关键词
            keywords = []
            for sector_keywords in SentimentAnalyzer.SECTOR_KEYWORDS.values():
                keywords.extend(sector_keywords)
            keywords = list(set(keywords))
        
        total_texts = len(texts)
        keyword_freq = {}
        
        for keyword in keywords:
            count = sum(1 for text in texts if keyword in text)
            freq = count / total_texts if total_texts > 0 else 0
            keyword_freq[keyword] = {
                'count': count,
                'frequency': round(freq, 4),
            }
        
        # 热度得分 = 关键词平均频率 * 100
        avg_freq = np.mean([v['frequency'] for v in keyword_freq.values()]) if keyword_freq else 0
        heat_score = round(avg_freq * 100, 2)
        
        return {
            'heat_score': heat_score,
            'keyword_freq': keyword_freq,
            'total_texts': total_texts,
        }
    
    @staticmethod
    def analyze_sector_sentiment(sector: str, texts: List[str]) -> Dict:
        """分析行业舆情"""
        sector_keywords = SentimentAnalyzer.SECTOR_KEYWORDS.get(sector, [])
        
        if not sector_keywords:
            return {'sector': sector, 'error': '未知行业'}
        
        # 过滤包含行业关键词的文本
        relevant_texts = [t for t in texts if any(kw in t for kw in sector_keywords)]
        
        if not relevant_texts:
            return {
                'sector': sector,
                'heat_score': 0,
                'sentiment_score': 0,
                'text_count': 0,
            }
        
        # 计算热度
        heat_result = SentimentAnalyzer.calculate_heat_score(relevant_texts, sector_keywords)
        
        # 计算情感
        sentiment_results = [SentimentAnalyzer.calculate_keyword_score(text) 
                           for text in relevant_texts]
        avg_sentiment = np.mean([r['score'] for r in sentiment_results])
        
        return {
            'sector': sector,
            'heat_score': heat_result['heat_score'],
            'sentiment_score': round(avg_sentiment, 3),
            'sentiment_label': 'positive' if avg_sentiment > 0.2 else 'negative' if avg_sentiment < -0.2 else 'neutral',
            'text_count': len(relevant_texts),
            'top_keywords': list(heat_result['keyword_freq'].keys())[:5],
        }
    
    @staticmethod
    def detect_catalyst(sector: str, current_heat: float, 
                        historical_heat: List[float], 
                        threshold: float = 2.0) -> Dict:
        """检测催化剂信号
        
        当热度突增时触发
        """
        if not historical_heat or len(historical_heat) < 5:
            return {'catalyst': False, 'reason': '历史数据不足'}
        
        avg_heat = np.mean(historical_heat[-10:])  # 近10期平均热度
        std_heat = np.std(historical_heat[-10:])
        
        if std_heat == 0:
            z_score = 0
        else:
            z_score = (current_heat - avg_heat) / std_heat
        
        # 热度突增检测
        heat_increase = (current_heat - avg_heat) / avg_heat * 100 if avg_heat > 0 else 0
        
        catalyst = z_score > threshold or heat_increase > 100
        
        return {
            'catalyst': catalyst,
            'sector': sector,
            'current_heat': current_heat,
            'avg_heat': round(avg_heat, 2),
            'z_score': round(z_score, 2),
            'heat_increase_pct': round(heat_increase, 2),
            'reason': f"热度突增{heat_increase:.1f}%" if catalyst else "正常波动",
        }


# 模拟数据生成（实际应用中从爬虫获取）
def generate_mock_sentiment_data(sector: str) -> Dict:
    """生成模拟舆情数据"""
    np.random.seed(hash(sector) % 2**31)
    
    # 模拟近30天热度
    base_heat = np.random.uniform(20, 80)
    historical_heat = [base_heat + np.random.uniform(-10, 10) for _ in range(30)]
    
    # 模拟当前热度（可能有突增）
    if np.random.random() > 0.8:
        current_heat = base_heat * np.random.uniform(1.5, 2.5)  # 热度突增
    else:
        current_heat = base_heat + np.random.uniform(-5, 5)
    
    # 生成模拟文本
    texts = []
    for _ in range(np.random.randint(10, 50)):
        if np.random.random() > 0.5:
            texts.append(f"{sector}板块利好消息，{np.random.choice(list(SentimentAnalyzer.POSITIVE_WORDS))}")
        else:
            texts.append(f"{sector}板块承压，{np.random.choice(list(SentimentAnalyzer.NEGATIVE_WORDS))}")
    
    return {
        'sector': sector,
        'current_heat': round(current_heat, 2),
        'historical_heat': [round(h, 2) for h in historical_heat],
        'texts': texts,
    }


def get_sector_sentiment(sector: str) -> Dict:
    """获取行业舆情分析"""
    # 生成模拟数据
    mock_data = generate_mock_sentiment_data(sector)
    
    # 分析舆情
    sentiment = SentimentAnalyzer.analyze_sector_sentiment(
        mock_data['sector'], mock_data['texts']
    )
    
    # 检测催化剂
    catalyst = SentimentAnalyzer.detect_catalyst(
        mock_data['sector'], 
        mock_data['current_heat'],
        mock_data['historical_heat']
    )
    
    return {
        **sentiment,
        'catalyst': catalyst,
        'heat_trend': mock_data['historical_heat'][-7:],  # 近7天趋势
    }


def get_all_sectors_sentiment() -> List[Dict]:
    """获取所有行业舆情"""
    sectors = list(SentimentAnalyzer.SECTOR_KEYWORDS.keys())
    results = []
    
    for sector in sectors:
        result = get_sector_sentiment(sector)
        results.append(result)
    
    # 按热度排序
    results.sort(key=lambda x: x.get('heat_score', 0), reverse=True)
    
    return results
