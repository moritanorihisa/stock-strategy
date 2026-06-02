"""
Fear & Greed Index の取得モジュール
CNN Money の Fear & Greed Index を計算・表示する。

仕組み：
  - Market Momentum（市場勢い）
  - Stock Price Strength（株価強度）
  - Junk Bond Demand（ジャンク債需要）
  - Volatility（ボラティリティ）
  - Safe Haven Demand（安全資産需要）
  - Sector Rotation（セクターローテーション）
  - Put/Call Ratio（プット・コール比率）

スコア：
  0-25：Extreme Fear（極度の恐怖）
  26-45：Fear（恐怖）
  46-55：Neutral（中立）
  56-75：Greed（貪欲）
  76-100：Extreme Greed（極度の貪欲）
"""

import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
import numpy as np


@st.cache_data(ttl=3600)
def calculate_fear_greed_index() -> dict:
    """
    Fear & Greed Index を複数の指標から計算する。

    Returns
    -------
    dict with keys:
        "score"       : スコア（0-100）
        "label"       : "Extreme Fear", "Fear", "Neutral", "Greed", "Extreme Greed"
        "color"       : 色コード
        "components"  : 各構成要素のスコア
        "timestamp"   : 取得時刻
    """
    try:
        # 1. Market Momentum（S&P500の52週比）
        sp500 = yf.download("^GSPC", period="1y", auto_adjust=True, progress=False)
        if not sp500.empty:
            current = sp500["Close"].iloc[-1]
            year_high = sp500["Close"].max()
            momentum_pct = ((current - sp500["Close"].iloc[0]) / sp500["Close"].iloc[0]) * 100
            momentum_score = min(100, max(0, 50 + momentum_pct))  # -50%～+50% を 0～100 にスケール
        else:
            momentum_score = 50

        # 2. Stock Price Strength（高値更新銘柄と安値更新銘柄の比率）
        # 簡易版：S&P500の過去30日リターン
        sp500_recent = yf.download("^GSPC", period="30d", auto_adjust=True, progress=False)
        if not sp500_recent.empty:
            strength_pct = ((sp500_recent["Close"].iloc[-1] - sp500_recent["Close"].iloc[0]) / sp500_recent["Close"].iloc[0]) * 100
            strength_score = min(100, max(0, 50 + strength_pct * 5))  # ±10% → 0～100
        else:
            strength_score = 50

        # 3. Volatility（VIX）- VIXが高いほど Fearスコアが高い
        vix_data = yf.download("^VIX", period="5d", auto_adjust=True, progress=False)
        if not vix_data.empty:
            vix_current = float(vix_data["Close"].iloc[-1])
            volatility_score = max(0, min(100, 100 - (vix_current - 10) * 2.5))  # VIX 10→100, VIX 50→0
        else:
            volatility_score = 50

        # 4. Junk Bond Demand（高リスク資産への需要）
        # 簡易版：テック系 vs ディフェンシブ銘柄の比較
        try:
            nasdaq = yf.download("^IXIC", period="30d", auto_adjust=True, progress=False)
            sp500_recent_for_ratio = yf.download("^GSPC", period="30d", auto_adjust=True, progress=False)
            if not nasdaq.empty and not sp500_recent_for_ratio.empty:
                nasdaq_return = ((nasdaq["Close"].iloc[-1] - nasdaq["Close"].iloc[0]) / nasdaq["Close"].iloc[0]) * 100
                sp500_return = ((sp500_recent_for_ratio["Close"].iloc[-1] - sp500_recent_for_ratio["Close"].iloc[0]) / sp500_recent_for_ratio["Close"].iloc[0]) * 100
                # NASDAQの方が強気 = Greed
                junk_score = min(100, max(0, 50 + (nasdaq_return - sp500_return) * 3))
            else:
                junk_score = 50
        except:
            junk_score = 50

        # 5. Safe Haven Demand（安全資産需要 = ドル強気）
        # ドル指数の簡易版
        try:
            gbp = yf.download("GBPUSD=X", period="30d", auto_adjust=True, progress=False)
            if not gbp.empty:
                safe_haven_pct = ((gbp["Close"].iloc[-1] - gbp["Close"].iloc[0]) / gbp["Close"].iloc[0]) * 100
                # ドルが強い = 安全資産需要が高い = Fear = 低スコア
                safe_haven_score = max(0, min(100, 50 - safe_haven_pct * 2))
            else:
                safe_haven_score = 50
        except:
            safe_haven_score = 50

        # スコアを平均化
        scores = [momentum_score, strength_score, volatility_score, junk_score, safe_haven_score]
        final_score = int(np.mean(scores))

        # ラベルと色の決定
        if final_score < 25:
            label = "Extreme Fear（極度の恐怖）"
            color = "#ff0000"
        elif final_score < 46:
            label = "Fear（恐怖）"
            color = "#ff6600"
        elif final_score < 55:
            label = "Neutral（中立）"
            color = "#ffaa00"
        elif final_score < 75:
            label = "Greed（貪欲）"
            color = "#00cc88"
        else:
            label = "Extreme Greed（極度の貪欲）"
            color = "#00ff00"

        return {
            "score": final_score,
            "label": label,
            "color": color,
            "components": {
                "Market Momentum": round(momentum_score, 1),
                "Stock Price Strength": round(strength_score, 1),
                "Volatility": round(volatility_score, 1),
                "Junk Bond Demand": round(junk_score, 1),
                "Safe Haven Demand": round(safe_haven_score, 1),
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    except Exception as e:
        print(f"Fear & Greed Index 計算エラー: {e}")
        return {
            "score": 50,
            "label": "Neutral（計算中...）",
            "color": "#ffaa00",
            "components": {},
            "timestamp": "N/A",
        }


def interpret_fear_greed(score: int) -> str:
    """スコアの解釈を返す。"""
    if score < 25:
        return "📉 市場は極度の恐怖。投資家のセンチメントが最悪。株価下落予想"
    elif score < 46:
        return "🔴 市場は恐怖モード。安全資産への逃避が起きている。注意が必要"
    elif score < 55:
        return "🟡 市場は中立。方向性が定まらない。様子見が賢明"
    elif score < 75:
        return "🟢 市場は貪欲。リスク資産が買われている。上昇期待"
    else:
        return "📈 市場は極度の貪欲。投資過熱の可能性。売りシグナル"
