"""
AI成長株スコアリングモデル
テクニカル指標を組み合わせて、各銘柄の「上昇期待スコア」を計算する。

重要:
  このスコアは過去データの統計的パターンに基づく「期待値」であり、
  将来の値動きを保証するものではありません。
  投資判断はご自身の責任で行ってください。
"""

import numpy as np
import pandas as pd
from growth.watchlist import AI_STOCK_INFO


def calc_scores(features: pd.DataFrame) -> pd.DataFrame:
    """
    各指標を0〜100点に正規化して重み付き合計スコアを計算する。

    重み付け（合計100%）:
      - 翌日上昇確率 (up_ratio)    : 30%
      - 翌日期待リターン            : 25%
      - 直近5日勢い (ret_5d)       : 15%
      - 直近20日トレンド (ret_20d) : 10%
      - 移動平均乖離 (ma_diff)     : 10%
      - 出来高増加 (vol_ratio)     : 10%
    """
    df = features.copy()

    def norm(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
        """0〜100に正規化。外れ値はクリップ。"""
        mn, mx = series.quantile(0.05), series.quantile(0.95)
        if mx == mn:
            return pd.Series(50.0, index=series.index)
        clipped = series.clip(mn, mx)
        normalized = (clipped - mn) / (mx - mn) * 100
        return normalized if higher_is_better else 100 - normalized

    # 各指標を正規化
    s_up      = norm(df["up_ratio"])
    s_next    = norm(df["next_ret_avg"])
    s_ret5    = norm(df["ret_5d"])
    s_ret20   = norm(df["ret_20d"])
    s_madiff  = norm(df["ma_diff"])
    s_vol     = norm(df["vol_ratio"])
    s_risk    = norm(df["vol_20d"], higher_is_better=False)  # ボラ高い = リスク高い

    # 総合スコア（重み付き平均）
    df["score"] = (
        s_up    * 0.30 +
        s_next  * 0.25 +
        s_ret5  * 0.15 +
        s_ret20 * 0.10 +
        s_madiff* 0.10 +
        s_vol   * 0.10
    ).round(1)

    # 上昇確率（%表示）
    df["up_prob_pct"] = (df["up_ratio"] * 100).round(1)

    # 予測上昇幅（翌日期待リターン）
    df["pred_return_pct"] = (df["next_ret_avg"] * 100).round(2)

    # リスクスコア（1〜5、高いほどリスク大）
    df["risk_stars"] = pd.cut(
        df["vol_20d"],
        bins=[0, 0.25, 0.40, 0.55, 0.75, np.inf],
        labels=[1, 2, 3, 4, 5],
    ).astype(float).fillna(3)

    # 補足情報を結合
    info_df = pd.DataFrame(AI_STOCK_INFO).T
    info_df.index.name = "ticker"
    df = df.join(info_df, how="left")

    # NISA向き度（補足情報から。デフォルト3）
    df["nisa_stars"] = pd.to_numeric(df["nisa"], errors="coerce").fillna(3).astype(int)

    # スコア順にソート
    df = df.sort_values("score", ascending=False).reset_index()

    return df


def stars(n: float, max_n: int = 5) -> str:
    """数値を★☆で表示する。"""
    n = int(round(n))
    return "★" * n + "☆" * (max_n - n)


def risk_label(stars_val: float) -> str:
    mapping = {1: "低め", 2: "やや低", 3: "中程度", 4: "やや高", 5: "高め"}
    return mapping.get(int(stars_val), "中程度")


def buy_timing(ticker: str) -> str:
    """初心者向け購入タイミングのガイド文。"""
    return "米国市場の寄付き付近（日本時間 夜23:30〜）または引け前（翌朝5:00前後）"


def sell_timing_short(ticker: str) -> str:
    return "短期検証なら1〜5営業日後、スコアが大きく低下したタイミング"


def sell_timing_nisa(ticker: str) -> str:
    return "NISA長期保有なら短期売買は不向き。月次でスコアを確認し見直す"
