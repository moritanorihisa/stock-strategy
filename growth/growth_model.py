"""
成長株スコアリングモデル（米国AI株 + 日本成長株 共通）

【重要な免責事項】
  このスコアは過去データの統計的パターンに基づく「検証用シグナル」であり、
  将来の値動きを保証するものではありません。
  「予測上昇幅」「上昇確率」はいずれも過去類似条件における統計的期待値です。
  投資判断はすべてご自身の責任で行ってください。
"""

import numpy as np
import pandas as pd
from growth.watchlist import ALL_STOCK_INFO


def calc_scores(features: pd.DataFrame) -> pd.DataFrame:
    """
    テクニカル特徴量を0〜100点に正規化し、重み付き総合スコアを計算する。

    重み付け（合計100%）:
      翌日上昇確率 (up_ratio)           30%  ← 最重視
      類似パターン翌日期待値             25%  ← 論文手法に近い指標
      直近5日勢い (ret_5d)              15%
      直近20日トレンド (ret_20d)        10%
      移動平均乖離 (ma_diff)            10%
      出来高増加 (vol_ratio)            10%

    リスクスコアはボラティリティから独立して計算（スコアには含めない）。
    """
    df = features.copy()
    if df.empty:
        return df

    def norm(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
        """5〜95パーセンタイルの範囲で0〜100に正規化する。"""
        mn, mx = series.quantile(0.05), series.quantile(0.95)
        if mx == mn:
            return pd.Series(50.0, index=series.index)
        clipped    = series.clip(mn, mx)
        normalized = (clipped - mn) / (mx - mn) * 100.0
        return normalized if higher_is_better else 100.0 - normalized

    s_up      = norm(df["up_ratio"])
    s_similar = norm(df["similar_score"])
    s_ret5    = norm(df["ret_5d"])
    s_ret20   = norm(df["ret_20d"])
    s_madiff  = norm(df["ma_diff"])
    s_vol     = norm(df["vol_ratio"])

    df["score"] = (
        s_up      * 0.30 +
        s_similar * 0.25 +
        s_ret5    * 0.15 +
        s_ret20   * 0.10 +
        s_madiff  * 0.10 +
        s_vol     * 0.10
    ).round(1)

    # 上昇確率・予測上昇幅（類似パターンを優先使用）
    df["up_prob_pct"]     = (df["up_ratio"] * 100).round(1)
    df["pred_return_pct"] = (df["similar_score"] * 100).round(2)

    # ボラティリティ → リスク星1〜5
    df["risk_stars"] = pd.cut(
        df["vol_20d"],
        bins=[0, 0.20, 0.35, 0.50, 0.70, np.inf],
        labels=[1, 2, 3, 4, 5],
    ).astype(float).fillna(3)

    # 銘柄補足情報を結合
    info_df = pd.DataFrame(ALL_STOCK_INFO).T.rename_axis("ticker")
    df      = df.join(info_df, how="left")

    df["nisa_stars"] = pd.to_numeric(df.get("nisa"), errors="coerce").fillna(3).astype(int)

    return df.sort_values("score", ascending=False).reset_index()


# ── 表示ヘルパー ──────────────────────────────────────────────

def stars(n: float, max_n: int = 5) -> str:
    """数値を★☆で表示する。"""
    n = max(0, min(max_n, int(round(n))))
    return "★" * n + "☆" * (max_n - n)


def risk_label(v: float) -> str:
    return {1: "低め", 2: "やや低", 3: "中程度", 4: "やや高", 5: "高め"}.get(int(v), "中程度")


def buy_timing_us(ticker: str) -> str:
    return "米国市場の寄付き付近（日本時間 夜23:30〜）または引け前（翌朝5:00前後）"


def buy_timing_jp(ticker: str) -> str:
    return "東証の寄付き付近（朝 8:45〜8:55 に寄付成行注文）"


def sell_timing_short() -> str:
    return "短期検証なら1〜5営業日後、スコアが大きく低下したタイミング"


def sell_timing_nisa() -> str:
    return "NISA長期保有なら短期売買は不向き。月次でスコアを確認し見直す"


def price_display(price: float, currency: str) -> str:
    if currency == "JPY":
        return f"¥{price:,.0f}"
    return f"${price:,.2f}"
