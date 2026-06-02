"""
予測精度検証モジュール
過去の予測と実結果を比較して精度を計算する。
"""

import pandas as pd
import numpy as np
import streamlit as st


def calculate_accuracy_metrics(predictions: pd.DataFrame, actual_returns: pd.DataFrame) -> dict:
    """
    予測スコアと実際のリターンを比較して精度を計算。

    Parameters
    ----------
    predictions : pd.DataFrame
        予測スコア（予測モデルの出力）
    actual_returns : pd.DataFrame
        実際の日中リターン

    Returns
    -------
    dict with metrics:
        "directional_accuracy"  : 方向性的中率（上昇予測が当たった率）
        "mean_absolute_error"   : 平均絶対誤差
        "correlation"           : 予測と実結果の相関
        "hit_rate_top3"         : トップ3銘柄の中に実際の上昇銘柄がある率
    """
    common_idx = predictions.index.intersection(actual_returns.index)
    preds = predictions.loc[common_idx]
    actuals = actual_returns.loc[common_idx]

    # 1. 方向性的中率：予測上昇 かつ 実際に上昇した率
    pred_direction = (preds > preds.median()).astype(int)
    actual_direction = (actuals > actuals.median()).astype(int)
    directional_accuracy = (pred_direction == actual_direction).astype(float).mean().mean() * 100

    # 2. 平均絶対誤差（スコア vs リターン）
    # ノーマライズして比較
    preds_norm = (preds - preds.mean()) / (preds.std() + 1e-8)
    actuals_norm = (actuals - actuals.mean()) / (actuals.std() + 1e-8)
    mae = np.abs(preds_norm - actuals_norm).mean().mean()

    # 3. 相関係数
    corr_list = []
    for col in preds.columns:
        if col in actuals.columns:
            valid_mask = (~preds[col].isna()) & (~actuals[col].isna())
            if valid_mask.sum() > 1:
                c = np.corrcoef(preds[col][valid_mask], actuals[col][valid_mask])[0, 1]
                if not np.isnan(c):
                    corr_list.append(c)
    correlation = np.mean(corr_list) if corr_list else 0.0

    # 4. トップ3銘柄の的中率
    top3_hit_rate = _calculate_top3_hit_rate(preds, actuals)

    return {
        "directional_accuracy": round(directional_accuracy, 1),
        "mean_absolute_error": round(mae, 3),
        "correlation": round(correlation, 3),
        "hit_rate_top3": round(top3_hit_rate, 1),
    }


def _calculate_top3_hit_rate(predictions: pd.DataFrame, actual_returns: pd.DataFrame) -> float:
    """
    予測トップ3銘柄が実際に上昇した率を計算。
    """
    hit_count = 0
    total_count = 0

    for date in predictions.index:
        pred_row = predictions.loc[date]
        actual_row = actual_returns.loc[date]

        # 予測トップ3を取得
        pred_top3 = pred_row.nlargest(3).index

        # 実際に上昇した銘柄を取得
        positive_actual = actual_row[actual_row > 0].index

        # トップ3と上昇銘柄の交差
        hits = len(set(pred_top3) & set(positive_actual))
        hit_count += hits
        total_count += 3

    return (hit_count / total_count * 100) if total_count > 0 else 0.0


def get_recent_accuracy(predictions: pd.DataFrame, actual_returns: pd.DataFrame, days: int = 20) -> pd.DataFrame:
    """
    最近N日間の精度を日付ごとに表示。
    """
    common_idx = predictions.index.intersection(actual_returns.index)
    preds = predictions.loc[common_idx].tail(days)
    actuals = actual_returns.loc[common_idx].tail(days)

    result_rows = []
    for date in preds.index:
        pred_row = preds.loc[date]
        actual_row = actuals.loc[date]

        # 予測トップ3
        pred_top3 = pred_row.nlargest(3).index.tolist()
        # 実際トップ3
        actual_top3 = actual_row.nlargest(3).index.tolist()

        # 的中数
        hits = len(set(pred_top3) & set(actual_top3))

        # 平均予測スコア vs 平均リターン
        avg_pred = pred_row.mean()
        avg_actual = actual_row.mean()

        result_rows.append({
            "日付": date.strftime("%Y-%m-%d"),
            "的中数": f"{hits}/3",
            "平均予測": f"{avg_pred:.4f}",
            "平均リターン": f"{avg_actual:.4f}%",
            "一致度": "✓" if hits >= 2 else "△" if hits == 1 else "✗",
        })

    return pd.DataFrame(result_rows)


def get_sector_accuracy(predictions: pd.DataFrame, actual_returns: pd.DataFrame) -> pd.DataFrame:
    """
    セクター別の予測精度を計算。
    """
    common_idx = predictions.index.intersection(actual_returns.index)
    preds = predictions.loc[common_idx]
    actuals = actual_returns.loc[common_idx]

    accuracy_rows = []
    for col in preds.columns:
        if col in actuals.columns:
            pred_col = preds[col]
            actual_col = actuals[col]

            # 方向性的中率
            pred_dir = (pred_col > pred_col.median()).astype(int)
            actual_dir = (actual_col > actual_col.median()).astype(int)
            direction_acc = (pred_dir == actual_dir).mean() * 100

            # 相関
            valid_mask = (~pred_col.isna()) & (~actual_col.isna())
            if valid_mask.sum() > 1:
                corr = np.corrcoef(pred_col[valid_mask], actual_col[valid_mask])[0, 1]
                corr = corr if not np.isnan(corr) else 0.0
            else:
                corr = 0.0

            # セクター名を抽出
            ticker = col.replace("JP_", "").replace("_intraday", "")

            accuracy_rows.append({
                "ティッカー": ticker,
                "方向性的中率": f"{direction_acc:.1f}%",
                "相関": f"{corr:.3f}",
                "予測数": valid_mask.sum(),
            })

    return pd.DataFrame(accuracy_rows).sort_values("方向性的中率", ascending=False)
