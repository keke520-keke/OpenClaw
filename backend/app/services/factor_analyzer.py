"""因子分析工具 - IC分析、相关性、分层回测"""
import numpy as np
import pandas as pd
from scipy import stats
from itertools import combinations


def calc_ic(factor: pd.Series, forward_return: pd.Series, method: str = "rank") -> dict:
    """计算单个因子的 IC (Information Coefficient)

    Args:
        factor: 因子值 Series
        forward_return: 未来N期收益率 Series (对齐索引)
        method: 'rank'=RankIC, 'pearson'=PearsonIC
    """
    valid = factor.notna() & forward_return.notna()
    if valid.sum() < 10:
        return {"IC_mean": 0, "IC_std": 0, "IC_IR": 0, "IC_win_rate": 0, "valid_days": 0}

    f, r = factor[valid], forward_return[valid]

    if method == "rank":
        ic = f.rank().corr(r.rank())
    else:
        ic = f.corr(r)

    return {
        "IC": round(ic, 4),
        "valid_days": int(valid.sum()),
    }


def calc_ic_series(factor: pd.Series, forward_return: pd.Series, periods: list = None) -> dict:
    """滚动IC序列 - 用于时序分析"""
    if periods is None:
        periods = [1, 5, 10, 20]

    results = {}
    for p in periods:
        fwd = forward_return.shift(-p)
        results[f"IC_{p}d"] = calc_ic(factor, fwd)

    return results


def calc_factor_correlation(factor_df: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    """计算因子间相关性矩阵"""
    valid = factor_df.dropna(thresh=len(factor_df) * 0.3, axis=1)
    if len(valid.columns) > top_n:
        valid = valid.iloc[:, :top_n]
    return valid.corr(method="spearman")


def find_high_corr_pairs(corr_matrix: pd.DataFrame, threshold: float = 0.7) -> list:
    """找出高相关因子对"""
    pairs = []
    cols = corr_matrix.columns
    for i, j in combinations(range(len(cols)), 2):
        val = abs(corr_matrix.iloc[i, j])
        if val >= threshold:
            pairs.append((cols[i], cols[j], round(val, 3)))
    pairs.sort(key=lambda x: -x[2])
    return pairs


def layer_backtest(factor: pd.Series, forward_return: pd.Series,
                   n_layers: int = 5, period: int = 5) -> dict:
    """分层回测 - 按因子值分组，计算各组未来收益

    Returns:
        {layer_1: {mean_return, win_rate, sharpe}, ...}
    """
    valid = factor.notna() & forward_return.notna()
    if valid.sum() < n_layers * 5:
        return {"error": "Not enough data"}

    f, r = factor[valid], forward_return.shift(-period)[valid]
    valid2 = r.notna()
    f, r = f[valid2], r[valid2]

    # 按因子值分N层
    labels = [f"Q{i+1}" for i in range(n_layers)]
    layer = pd.qcut(f.rank(method="first"), n_layers, labels=labels, duplicates="drop")

    result = {
        "n_layers": n_layers, "period_days": period,
        "total_samples": int(valid2.sum()),
        "layers": {},
    }

    for label in labels:
        if label not in layer.values:
            continue
        lr = r[layer == label]
        if len(lr) < 3:
            continue
        result["layers"][label] = {
            "mean_return": round(lr.mean() * 100, 4),
            "std_return": round(lr.std() * 100, 4),
            "win_rate": round((lr > 0).mean() * 100, 2),
            "sharpe": round(lr.mean() / lr.std() * np.sqrt(252 / period), 3) if lr.std() > 0 else 0,
            "max_drawdown": round((lr.cummin() - lr.cummax()).min() * 100, 3),
            "count": int(len(lr)),
        }

    # 多空收益差
    if "Q1" in result["layers"] and f"Q{n_layers}" in result["layers"]:
        long = result["layers"]["Q1"]["mean_return"]
        short = result["layers"][f"Q{n_layers}"]["mean_return"]
        result["long_short_spread"] = round(long - short, 4)

    return result


def factor_summary(factor: pd.Series, forward_ret: pd.Series) -> dict:
    """单因子综合评估"""
    ic = calc_ic(factor, forward_ret)
    layer = layer_backtest(factor, forward_ret, n_layers=5, period=5)

    return {
        **ic,
        "layer_backtest": layer.get("long_short_spread", 0),
        "coverage": round(factor.notna().mean() * 100, 1),
    }


def rank_factors(factor_df: pd.DataFrame, forward_return: pd.Series,
                 top_n: int = 30) -> list[dict]:
    """对因子按 IC 排序"""
    scores = []
    for col in factor_df.columns:
        try:
            s = factor_summary(factor_df[col], forward_return)
            scores.append({"factor": col, **s})
        except Exception:
            pass
    scores.sort(key=lambda x: abs(x.get("IC", 0)), reverse=True)
    return scores[:top_n]
