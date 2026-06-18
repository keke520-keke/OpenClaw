"""
AI模型真实训练管道
- 基于真实历史K线数据
- sklearn模型训练+保存
- 模型预测+信号生成
"""
import os
import json
import math
import time
import subprocess
from datetime import datetime, timedelta
import numpy as np

# sklearn
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import joblib

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "models")
os.makedirs(MODEL_DIR, exist_ok=True)


def fetch_kline_tencent(code: str, days: int = 500):
    """从本地K线文件获取历史数据（腾讯API格式）"""
    kline_file = os.path.join(MODEL_DIR, "..", "kline", f"{code}.json")
    if not os.path.isfile(kline_file):
        return []
    try:
        with open(kline_file, "r", encoding="utf-8") as f:
            j = json.load(f)
        market = "1" if code.startswith("6") else "0"
        days_data = j.get("data", {}).get(f"{market}.{code}", {}).get("qfqday", []) or \
                    j.get("data", {}).get(f"{market}.{code}", {}).get("day", [])
        result = []
        for d in days_data:
            if len(d) >= 6:
                result.append({
                    "date": d[0], "open": float(d[1]), "close": float(d[2]),
                    "high": float(d[3]), "low": float(d[4]),
                    "volume": float(d[5]) if d[5] else 0,
                })
        return result[-days:] if days else result
    except Exception:
        return []


def calc_features(data: list) -> list:
    """从K线计算技术特征"""
    if len(data) < 30:
        return []

    closes = [d["close"] for d in data]
    volumes = [d["volume"] for d in data]
    highs = [d["high"] for d in data]
    lows = [d["low"] for d in data]
    opens = [d["open"] for d in data]

    features = []
    for i in range(30, len(data)):
        row = {}

        # 价格
        close = closes[i]
        prev = closes[i-1] if i > 0 else close

        # 收益率
        row["ret_1d"] = (close / closes[i-1] - 1) if i > 0 else 0
        row["ret_5d"] = (close / closes[i-5] - 1) if i >= 5 else 0
        row["ret_10d"] = (close / closes[i-10] - 1) if i >= 10 else 0
        row["ret_20d"] = (close / closes[i-20] - 1) if i >= 20 else 0

        # 均线偏离
        ma5 = np.mean(closes[i-5:i])
        ma10 = np.mean(closes[i-10:i])
        ma20 = np.mean(closes[i-20:i])
        row["ma5_dev"] = (close / ma5 - 1) * 100 if ma5 else 0
        row["ma10_dev"] = (close / ma10 - 1) * 100 if ma10 else 0
        row["ma20_dev"] = (close / ma20 - 1) * 100 if ma20 else 0
        row["ma5_10_diff"] = (ma5 / ma10 - 1) * 100 if ma10 else 0

        # RSI(14)
        if i >= 14:
            gains = [max(0, closes[j] - closes[j-1]) for j in range(i-13, i+1)]
            losses = [max(0, closes[j-1] - closes[j]) for j in range(i-13, i+1)]
            avg_gain = np.mean(gains) if gains else 0
            avg_loss = np.mean(losses) if losses else 0.001
            row["rsi14"] = 100 - (100 / (1 + avg_gain / avg_loss)) if avg_loss > 0 else 50
        else:
            row["rsi14"] = 50

        # MACD (简化)
        if i >= 26:
            ema12 = np.mean(closes[i-12:i])
            ema26 = np.mean(closes[i-26:i])
            row["macd_diff"] = ema12 - ema26
            row["macd_ratio"] = (ema12 / ema26 - 1) * 100 if ema26 else 0
        else:
            row["macd_diff"] = 0
            row["macd_ratio"] = 0

        # 成交量特征
        avg_vol = np.mean(volumes[i-5:i]) if i >= 5 else volumes[i]
        row["vol_ratio"] = volumes[i] / avg_vol if avg_vol > 0 else 1
        row["vol_5d_avg"] = avg_vol / 1e6 if avg_vol else 0

        # 振幅
        row["amplitude"] = (highs[i] - lows[i]) / closes[i] * 100 if closes[i] else 0

        # 开盘价偏离
        row["open_dev"] = (opens[i] / closes[i-1] - 1) * 100 if i > 0 else 0

        # K线形态
        row["body_ratio"] = (closes[i] - opens[i]) / (highs[i] - lows[i]) if (highs[i] - lows[i]) > 0 else 0
        row["upper_shadow"] = (highs[i] - max(closes[i], opens[i])) / (highs[i] - lows[i]) if (highs[i] - lows[i]) > 0 else 0
        row["lower_shadow"] = (min(closes[i], opens[i]) - lows[i]) / (highs[i] - lows[i]) if (highs[i] - lows[i]) > 0 else 0

        # 连涨连跌
        streak = 0
        for j in range(i, max(0, i-10), -1):
            if closes[j] > closes[j-1]:
                streak += 1
            else:
                break
        row["up_streak"] = streak

        # 高低点位置
        high_20 = max(highs[max(0,i-20):i+1])
        low_20 = min(lows[max(0,i-20):i+1])
        range_20 = high_20 - low_20
        row["price_position"] = (close - low_20) / range_20 * 100 if range_20 > 0 else 50

        features.append(row)

    return features


def calc_labels(data: list, forward_days: int = 5, threshold: float = 0.02) -> list:
    """计算标签：forward_days天后涨超threshold=买入，跌超threshold=卖出，否则持有"""
    labels = []
    closes = [d["close"] for d in data]
    for i in range(30, len(data) - forward_days):
        future_return = (closes[i + forward_days] / closes[i] - 1)
        if future_return > threshold:
            labels.append(1)  # BUY
        elif future_return < -threshold:
            labels.append(-1)  # SELL
        else:
            labels.append(0)  # HOLD
    return labels


def build_dataset(codes: list, log_fn=print):
    """从多只股票构建训练数据集"""
    all_features = []
    all_labels = []
    stock_count = 0

    for code in codes:
        try:
            data = fetch_kline_tencent(code)
            if len(data) < 60:
                continue
            features = calc_features(data)
            labels = calc_labels(data)
            min_len = min(len(features), len(labels))
            if min_len < 10:
                continue
            all_features.extend(features[:min_len])
            all_labels.extend(labels[:min_len])
            stock_count += 1
        except Exception as e:
            continue

    log_fn(f"  数据构建: {stock_count}只股票 {len(all_features)}条样本")

    if len(all_features) < 100:
        return None, None, []

    # 转为numpy
    feature_names = list(all_features[0].keys())
    X = np.array([[row[f] for f in feature_names] for row in all_features])
    y = np.array(all_labels)

    # 处理NaN/Inf
    X = np.nan_to_num(X, nan=0, posinf=0, neginf=0)

    return X, y, feature_names


def train_model(X, y, feature_names, log_fn=print):
    """训练模型"""
    if X is None or len(X) < 100:
        return None, None, None

    # 标准化
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 划分（80%训练/20%测试）
    split = int(len(X) * 0.8)
    X_train, X_test = X_scaled[:split], X_scaled[split:]
    y_train, y_test = y[:split], y[split:]

    models = {}

    # Random Forest
    log_fn("  训练 Random Forest...")
    rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    rf_score = rf.score(X_test, y_test)
    log_fn(f"    RF准确率: {rf_score:.3f}")
    models["rf"] = rf

    # Gradient Boosting
    log_fn("  训练 Gradient Boosting...")
    gb = GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
    gb.fit(X_train, y_train)
    gb_score = gb.score(X_test, y_test)
    log_fn(f"    GB准确率: {gb_score:.3f}")
    models["gbm"] = gb

    # Logistic Regression
    log_fn("  训练 Logistic Regression...")
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    lr_score = lr.score(X_test, y_test)
    log_fn(f"    LR准确率: {lr_score:.3f}")
    models["lr"] = lr

    # 特征重要性
    importance = sorted(zip(feature_names, rf.feature_importances_), key=lambda x: -x[1])

    return models, scaler, {"rf": rf_score, "gbm": gb_score, "lr": lr_score}


def save_models(models, scaler, feature_names, version, log_fn=print):
    """保存模型到磁盘"""
    try:
        model_path = os.path.join(MODEL_DIR, f"model_{version}.pkl")
        joblib.dump({"models": models, "scaler": scaler, "feature_names": feature_names}, model_path)
        log_fn(f"  模型已保存: {model_path}")
        return model_path
    except Exception as e:
        log_fn(f"  保存失败: {e}")
        return None


def load_models(version):
    """从磁盘加载模型"""
    model_path = os.path.join(MODEL_DIR, f"model_{version}.pkl")
    if not os.path.isfile(model_path):
        return None
    try:
        data = joblib.load(model_path)
        return data
    except Exception:
        return None


def predict_signals(model_data, X_new):
    """使用模型预测信号"""
    if not model_data:
        return []
    try:
        models = model_data["models"]
        scaler = model_data["scaler"]
        X_scaled = scaler.transform(X_new)
        signals = []
        for i in range(len(X_scaled)):
            votes = []
            confidences = []
            for name, model in models.items():
                try:
                    proba = model.predict_proba(X_scaled[i:i+1])[0]
                    pred = model.predict(X_scaled[i:i+1])[0]
                    votes.append(pred)
                    confidences.append(max(proba))
                except Exception:
                    continue
            if not votes:
                signals.append({"signal": "HOLD", "score": 0.5, "confidence": 0})
                continue
            # 多数投票
            final = max(set(votes), key=list(votes).count)
            avg_conf = np.mean(confidences) if confidences else 0
            signal_map = {1: "BUY", 0: "HOLD", -1: "SELL"}
            signals.append({
                "signal": signal_map.get(final, "HOLD"),
                "score": round(float(avg_conf), 3),
                "confidence": round(float(avg_conf), 3),
            })
        return signals
    except Exception:
        return []


def run_full_training(stocks: list, log_fn=print):
    """完整训练流程"""
    start_time = time.time()
    log_fn(f"[{datetime.now().strftime('%H:%M:%S')}] 训练开始: {len(stocks)}只股票")

    # Step 1: 构建数据集
    X, y, feature_names = build_dataset(stocks, log_fn)
    if X is None:
        log_fn("训练失败: 数据不足")
        return None

    # Step 2: 训练模型
    models, scaler, scores = train_model(X, y, feature_names, log_fn)
    if models is None:
        log_fn("训练失败: 模型训练失败")
        return None

    # Step 3: 保存模型
    version = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = save_models(models, scaler, feature_names, version, log_fn)

    elapsed = time.time() - start_time
    log_fn(f"[{datetime.now().strftime('%H:%M:%S')}] 训练完成 耗时{elapsed:.1f}s")

    # 返回结果
    return {
        "version": version,
        "scores": scores,
        "feature_names": feature_names,
        "samples": len(X),
        "stocks": len(stocks),
        "model_path": model_path,
        "elapsed": elapsed,
    }
