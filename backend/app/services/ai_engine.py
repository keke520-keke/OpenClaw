"""AI引擎 - ML模型训练/预测/信号生成

多模型集成 + 月度再平衡 + 置信度评分
"""
import numpy as np
import pandas as pd
from typing import Optional
from datetime import datetime, timedelta
from loguru import logger

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score

try:
    import xgboost as xgb
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

try:
    import lightgbm as lgb
    HAS_LGB = True
except ImportError:
    HAS_LGB = False


class AIModelEnsemble:
    """多模型投票集成"""

    def __init__(self):
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        self.trained = False
        self._init_models()

    def _init_models(self):
        """初始化基础模型"""
        self.models["rf"] = RandomForestClassifier(
            n_estimators=200, max_depth=8, min_samples_leaf=20,
            random_state=42, n_jobs=-1,
        )
        self.models["gbm"] = GradientBoostingClassifier(
            n_estimators=100, max_depth=5, learning_rate=0.05,
            random_state=42,
        )
        self.models["lr"] = LogisticRegression(
            C=0.5, max_iter=1000, random_state=42,
        )
        if HAS_XGB:
            self.models["xgb"] = xgb.XGBClassifier(
                n_estimators=100, max_depth=5, learning_rate=0.05,
                reg_alpha=1, reg_lambda=1, random_state=42,
                verbosity=0,
            )
        if HAS_LGB:
            self.models["lgb"] = lgb.LGBMClassifier(
                n_estimators=100, max_depth=6, learning_rate=0.05,
                num_leaves=31, random_state=42, verbose=-1,
            )

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str] = None):
        """训练所有模型"""
        self.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
        X_scaled = self.scaler.fit_transform(X)

        # 处理 NaN
        X_scaled = np.nan_to_num(X_scaled, 0)

        for name, model in self.models.items():
            try:
                model.fit(X_scaled, y)
                logger.info(f"  {name}: trained")
            except Exception as e:
                logger.warning(f"  {name}: failed - {e}")

        self.trained = True
        return self

    def predict_proba(self, X: np.ndarray) -> dict[str, np.ndarray]:
        """各模型预测概率"""
        X_scaled = self.scaler.transform(X)
        X_scaled = np.nan_to_num(X_scaled, 0)

        probas = {}
        for name, model in self.models.items():
            try:
                probas[name] = model.predict_proba(X_scaled)[:, 1]
            except Exception:
                probas[name] = np.full(X.shape[0], 0.5)
        return probas

    def predict_ensemble(self, X: np.ndarray, weights: dict = None) -> dict:
        """集成预测 - 加权投票"""
        probas = self.predict_proba(X)

        if weights is None:
            weights = {name: 1.0 / len(probas) for name in probas}

        # 加权平均
        ensemble_score = np.zeros(X.shape[0])
        weight_sum = sum(weights.get(name, 0) for name in probas)
        for name, proba in probas.items():
            ensemble_score += proba * weights.get(name, 0) / weight_sum

        # 信号分类
        signals = np.select(
            [ensemble_score >= 0.65, ensemble_score >= 0.5,
             ensemble_score <= 0.35, ensemble_score < 0.5],
            ["STRONG_BUY", "BUY", "STRONG_SELL", "SELL"],
            default="HOLD"
        )

        # 置信度
        confidence = np.abs(ensemble_score - 0.5) * 2

        # 模型一致性
        buy_votes = np.zeros(X.shape[0])
        for proba in probas.values():
            buy_votes += (proba >= 0.5).astype(int)
        agreement = buy_votes / len(probas)

        return {
            "score": ensemble_score.tolist(),
            "signal": signals.tolist(),
            "confidence": confidence.tolist(),
            "agreement": agreement.tolist(),
            "model_scores": {name: p.tolist() for name, p in probas.items()},
        }

    def feature_importance(self) -> list[dict]:
        """特征重要性（RF → 基尼重要性）"""
        if "rf" not in self.models:
            return []
        imp = self.models["rf"].feature_importances_
        result = [{"feature": self.feature_names[i], "importance": float(imp[i])}
                  for i in np.argsort(-imp)[:30] if imp[i] > 0]
        return result


def prepare_training_data(factor_df: pd.DataFrame,
                          forward_returns: pd.Series,
                          lookback: int = 20) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """从因子数据准备训练集

    Args:
        factor_df: 因子DataFrame (index=date, columns=factors)
        forward_returns: 未来N期收益率
        lookback: 回溯期

    Returns:
        X (特征矩阵), y (标签: 1=涨, 0=跌), feature_names
    """
    # 删除高NaN率的列
    valid_cols = factor_df.columns[factor_df.isna().mean() < 0.3]
    df = factor_df[valid_cols].copy()

    # 前向填充缺失值
    df = df.ffill().bfill().fillna(0)

    # 对齐索引
    common_idx = df.index.intersection(forward_returns.index)
    X = df.loc[common_idx].values
    y = (forward_returns.loc[common_idx] > 0).astype(int).values

    # 删除 y 中的 NaN
    valid = ~np.isnan(y)
    X, y = X[valid], y[valid]

    return X, y, list(valid_cols)


class SignalGenerator:
    """交易信号生成器"""

    def __init__(self, ensemble: AIModelEnsemble = None):
        self.ensemble = ensemble or AIModelEnsemble()
        self.last_trained: Optional[datetime] = None

    def train(self, factor_df: pd.DataFrame, forward_returns: pd.Series):
        """训练模型"""
        X, y, features = prepare_training_data(factor_df, forward_returns)
        if len(X) < 50:
            logger.warning("训练数据不足")
            return self

        logger.info(f"训练数据: {X.shape[0]} 样本 × {X.shape[1]} 特征")
        self.ensemble.fit(X, y, features)
        self.last_trained = datetime.now()
        return self

    def generate_signals(self, factor_df: pd.DataFrame) -> pd.DataFrame:
        """生成交易信号"""
        if not self.ensemble.trained:
            raise ValueError("模型未训练，请先调用 train()")

        # 对齐特征
        common_cols = [c for c in self.ensemble.feature_names if c in factor_df.columns]
        X = factor_df[common_cols].fillna(0).values
        X = np.nan_to_num(X, 0)

        pred = self.ensemble.predict_ensemble(X)
        imp = self.ensemble.feature_importance()

        result = pd.DataFrame({
            "signal": pred["signal"],
            "score": pred["score"],
            "confidence": pred["confidence"],
            "agreement": pred["agreement"],
        }, index=factor_df.index)

        return result, imp

    def get_top_picks(self, factor_df: pd.DataFrame, top_n: int = 10) -> list[dict]:
        """获取最优股票"""
        signals, _ = self.generate_signals(factor_df)
        buy = signals[signals["signal"].isin(["STRONG_BUY", "BUY"])]
        buy = buy.sort_values("confidence", ascending=False)
        return buy.head(top_n).to_dict(orient="records")


# ===== 全局单例 =====
_engine: Optional[SignalGenerator] = None


def get_engine() -> SignalGenerator:
    global _engine
    if _engine is None:
        _engine = SignalGenerator()
    return _engine
