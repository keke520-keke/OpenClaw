"""特征工程模块 - 因子正交化、PCA降维、去相关性

核心功能：
1. PCA主成分分析 - 降维并消除共线性
2. 施密特正交化 - 手动正交化因子
3. 相关性分析 - 检测因子间相关性
4. 特征选择 - 基于重要性筛选特征
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

class FeatureEngineering:
    """特征工程处理器"""
    
    @staticmethod
    def standardize(data: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """标准化（Z-score）"""
        mean = np.mean(data, axis=0)
        std = np.std(data, axis=0)
        std[std == 0] = 1  # 避免除零
        standardized = (data - mean) / std
        return standardized, mean, std
    
    @staticmethod
    def pca_orthogonalize(features: np.ndarray, n_components: Optional[int] = None, 
                          variance_threshold: float = 0.95) -> Tuple[np.ndarray, Dict]:
        """PCA主成分分析正交化
        
        Args:
            features: 特征矩阵 (n_samples, n_features)
            n_components: 保留的主成分数量（None则自动选择）
            variance_threshold: 方差解释率阈值
            
        Returns:
            正交化后的特征矩阵，PCA信息字典
        """
        n_samples, n_features = features.shape
        
        # 标准化
        standardized, mean, std = FeatureEngineering.standardize(features)
        
        # 计算协方差矩阵
        cov_matrix = np.cov(standardized.T)
        
        # 特征值分解
        eigenvalues, eigenvectors = np.linalg.eig(cov_matrix)
        
        # 按特征值大小排序
        sorted_indices = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[sorted_indices]
        eigenvectors = eigenvectors[:, sorted_indices]
        
        # 计算方差解释率
        total_variance = np.sum(eigenvalues)
        explained_variance_ratio = eigenvalues / total_variance
        cumulative_variance_ratio = np.cumsum(explained_variance_ratio)
        
        # 选择主成分数量
        if n_components is None:
            n_components = np.argmax(cumulative_variance_ratio >= variance_threshold) + 1
            n_components = max(1, min(n_components, n_features))
        
        # 投影到主成分空间
        selected_eigenvectors = eigenvectors[:, :n_components]
        transformed = standardized @ selected_eigenvectors
        
        info = {
            'n_components': n_components,
            'explained_variance_ratio': explained_variance_ratio[:n_components].tolist(),
            'cumulative_variance_ratio': cumulative_variance_ratio[:n_components].tolist(),
            'eigenvalues': eigenvalues[:n_components].tolist(),
            'loadings': selected_eigenvectors.T.tolist(),
        }
        
        return transformed, info
    
    @staticmethod
    def gram_schmidt_orthogonalize(features: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """施密特正交化
        
        将特征向量正交化，保持原始维度
        """
        n_samples, n_features = features.shape
        
        # 标准化
        standardized, mean, std = FeatureEngineering.standardize(features)
        
        # 施密特正交化
        orthogonal = np.zeros_like(standardized, dtype=float)
        orthogonal[:, 0] = standardized[:, 0]
        
        for j in range(1, n_features):
            v = standardized[:, j].copy()
            for i in range(j):
                u = orthogonal[:, i]
                if np.linalg.norm(u) > 0:
                    projection = np.dot(v, u) / np.dot(u, u) * u
                    v = v - projection
            orthogonal[:, j] = v
        
        # 重新标准化每个正交向量
        for j in range(n_features):
            norm = np.linalg.norm(orthogonal[:, j])
            if norm > 0:
                orthogonal[:, j] = orthogonal[:, j] / norm
        
        # 计算正交化前后的相关性变化
        corr_before = np.corrcoef(standardized.T)
        corr_after = np.corrcoef(orthogonal.T)
        
        info = {
            'max_correlation_before': float(np.max(np.abs(corr_before - np.eye(n_features)))),
            'max_correlation_after': float(np.max(np.abs(corr_after - np.eye(n_features)))),
            'orthogonalized': True,
        }
        
        return orthogonal, info
    
    @staticmethod
    def correlation_matrix(features: np.ndarray, feature_names: List[str] = None) -> Dict:
        """计算相关性矩阵"""
        n_features = features.shape[1]
        
        corr_matrix = np.corrcoef(features.T)
        
        # 找出高度相关的因子对
        high_corr_pairs = []
        threshold = 0.7
        for i in range(n_features):
            for j in range(i + 1, n_features):
                if abs(corr_matrix[i, j]) > threshold:
                    name_i = feature_names[i] if feature_names else f'f{i}'
                    name_j = feature_names[j] if feature_names else f'f{j}'
                    high_corr_pairs.append({
                        'feature_i': name_i,
                        'feature_j': name_j,
                        'correlation': float(corr_matrix[i, j]),
                    })
        
        return {
            'matrix': corr_matrix.tolist(),
            'high_correlation_pairs': high_corr_pairs,
            'max_correlation': float(np.max(np.abs(corr_matrix - np.eye(n_features)))),
        }
    
    @staticmethod
    def feature_importance_ranking(features: np.ndarray, target: np.ndarray,
                                    feature_names: List[str] = None) -> List[Dict]:
        """特征重要性排名（基于方差和与目标的相关性）"""
        n_features = features.shape[1]
        
        importances = []
        for i in range(n_features):
            # 方差（信息量）
            variance = np.var(features[:, i])
            
            # 与目标的相关性
            if len(target) == features.shape[0]:
                correlation = abs(np.corrcoef(features[:, i], target)[0, 1])
            else:
                correlation = 0
            
            # 综合重要性
            importance = 0.5 * min(variance, 1) + 0.5 * correlation
            
            name = feature_names[i] if feature_names else f'feature_{i}'
            importances.append({
                'name': name,
                'importance': float(importance),
                'variance': float(variance),
                'correlation_with_target': float(correlation),
            })
        
        # 按重要性排序
        importances.sort(key=lambda x: x['importance'], reverse=True)
        
        return importances
    
    @staticmethod
    def select_features(features: np.ndarray, feature_names: List[str],
                        n_select: int = 10, method: str = 'variance') -> Tuple[np.ndarray, List[str], Dict]:
        """特征选择
        
        Args:
            features: 特征矩阵
            feature_names: 特征名称列表
            n_select: 选择的特征数量
            method: 选择方法 ('variance', 'correlation', 'pca')
            
        Returns:
            选择后的特征矩阵，选中的特征名，选择信息
        """
        n_features = features.shape[1]
        
        if method == 'variance':
            # 基于方差选择
            variances = np.var(features, axis=0)
            selected_indices = np.argsort(variances)[::-1][:n_select]
            
        elif method == 'correlation':
            # 基于与均值的相关性选择（去除冗余）
            mean_feature = np.mean(features, axis=1)
            correlations = [abs(np.corrcoef(features[:, i], mean_feature)[0, 1]) 
                          for i in range(n_features)]
            selected_indices = np.argsort(correlations)[::-1][:n_select]
            
        elif method == 'pca':
            # 使用PCA选择
            transformed, info = FeatureEngineering.pca_orthogonalize(features)
            n_components = min(n_select, transformed.shape[1])
            # 找出每个主成分对应的原始特征（基于载荷）
            loadings = np.array(info['loadings'])
            selected_indices = []
            for comp in range(n_components):
                top_feature = np.argmax(np.abs(loadings[comp]))
                if top_feature not in selected_indices:
                    selected_indices.append(top_feature)
                if len(selected_indices) >= n_select:
                    break
            selected_indices = np.array(selected_indices[:n_select])
        else:
            selected_indices = np.arange(min(n_select, n_features))
        
        selected_features = features[:, selected_indices]
        selected_names = [feature_names[i] for i in selected_indices]
        
        info = {
            'method': method,
            'n_original': n_features,
            'n_selected': len(selected_indices),
            'selected_indices': selected_indices.tolist(),
        }
        
        return selected_features, selected_names, info


def orthogonalize_features(feature_data: List[Dict], method: str = 'pca') -> Dict:
    """正交化特征数据
    
    Args:
        feature_data: 特征数据列表，每个元素是 {feature_name: value}
        method: 正交化方法 ('pca', 'gram_schmidt')
        
    Returns:
        正交化后的特征数据和元信息
    """
    if not feature_data:
        return {'data': [], 'info': {}}
    
    # 提取特征名和值
    feature_names = list(feature_data[0].keys())
    n_samples = len(feature_data)
    n_features = len(feature_names)
    
    # 构建特征矩阵
    features = np.zeros((n_samples, n_features))
    for i, sample in enumerate(feature_data):
        for j, name in enumerate(feature_names):
            features[i, j] = sample.get(name, 0)
    
    # 正交化
    if method == 'pca':
        transformed, info = FeatureEngineering.pca_orthogonalize(features)
    elif method == 'gram_schmidt':
        transformed, info = FeatureEngineering.gram_schmidt_orthogonalize(features)
    else:
        transformed = features
        info = {'method': 'none'}
    
    # 转换回字典格式
    result_data = []
    for i in range(n_samples):
        sample = {}
        for j in range(transformed.shape[1]):
            name = f'pc_{j}' if method == 'pca' else feature_names[j]
            sample[name] = float(transformed[i, j])
        result_data.append(sample)
    
    return {
        'data': result_data,
        'info': info,
        'original_features': feature_names,
        'n_samples': n_samples,
    }


def analyze_feature_correlations(feature_data: List[Dict]) -> Dict:
    """分析特征相关性"""
    if not feature_data or len(feature_data) < 2:
        return {'error': '数据不足'}
    
    feature_names = list(feature_data[0].keys())
    n_features = len(feature_names)
    
    # 构建特征矩阵
    features = np.zeros((len(feature_data), n_features))
    for i, sample in enumerate(feature_data):
        for j, name in enumerate(feature_names):
            features[i, j] = sample.get(name, 0)
    
    # 计算相关性
    corr_info = FeatureEngineering.correlation_matrix(features, feature_names)
    
    # 特征重要性
    target = np.zeros(len(feature_data))  # 无目标变量时用零
    importances = FeatureEngineering.feature_importance_ranking(features, target, feature_names)
    
    return {
        'correlation': corr_info,
        'importance': importances[:10],  # 前10个重要特征
        'recommendation': '建议正交化' if corr_info['max_correlation'] > 0.7 else '相关性正常',
    }
