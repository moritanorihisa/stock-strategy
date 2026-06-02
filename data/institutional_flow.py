"""
機関投資家動向予測モジュール
Put/Call Ratio、先物建玉などから機関投資家の動向を推測。
"""

import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
import numpy as np


@st.cache_data(ttl=3600)
def analyze_institutional_sentiment() -> dict:
    """
    機関投資家のセンチメントを分析。

    Returns
    -------
    dict with keys:
        "bullish_score"    : 強気スコア（0-100）
        "bearish_score"    : 弱気スコア（0-100）
        "net_position"     : ネットポジション（買い/売り/中立）
        "indicators"       : 各指標の詳細
    """
    try:
        # 1. Put/Call Ratio（オプション市場のセンチメント）
        # VIXは恐怖を示すため、高いほど売り圧力
        vix_data = yf.download("^VIX", period="30d", auto_adjust=True, progress=False)
        if not vix_data.empty:
            vix_current = float(vix_data["Close"].iloc[-1])
            vix_avg = float(vix_data["Close"].mean())
            # VIXが平均より高い = 売り圧力が強い
            put_call_signal = max(0, min(100, 50 + (vix_current - vix_avg) * 5))
        else:
            put_call_signal = 50

        # 2. 先物建玉（ミニ）から推測
        # S&P500先物の強気ポジション判定
        sp500 = yf.download("^GSPC", period="60d", auto_adjust=True, progress=False)
        if not sp500.empty:
            recent_return = ((sp500["Close"].iloc[-1] - sp500["Close"].iloc[0]) / sp500["Close"].iloc[0]) * 100
            # 上昇トレンド = 機関投資家が買いポジション
            futures_signal = min(100, max(0, 50 + recent_return * 2))
        else:
            futures_signal = 50

        # 3. 機関投資家の典型的な行動パターン
        # 15時を過ぎたら、売却圧力が高まる傾向
        now = datetime.now()
        hour = now.hour
        if hour >= 15:
            # 後場：決済売却の圧力
            closing_pressure = min(100, 60 + (hour - 15) * 5)
        else:
            closing_pressure = 30

        # 4. S&P500 vs ドル指数の乖離
        # ドルが強い = 安全資産への逃避 = 売り圧力
        try:
            dxy = yf.download("DXY=F", period="30d", auto_adjust=True, progress=False)
            if not dxy.empty:
                dxy_return = ((dxy["Close"].iloc[-1] - dxy["Close"].iloc[0]) / dxy["Close"].iloc[0]) * 100
                # ドル上昇 = 売り圧力
                safe_haven_signal = min(100, max(0, 50 - dxy_return * 3))
            else:
                safe_haven_signal = 50
        except:
            safe_haven_signal = 50

        # 総合判定
        bullish_indicators = [futures_signal, 100 - closing_pressure, 100 - safe_haven_signal]
        bearish_indicators = [put_call_signal, closing_pressure, safe_haven_signal]

        bullish_score = int(np.mean(bullish_indicators))
        bearish_score = int(np.mean(bearish_indicators))

        # ネットポジション判定
        if bullish_score > bearish_score + 15:
            net_position = "🟢 買い圧力（強気）"
        elif bearish_score > bullish_score + 15:
            net_position = "🔴 売り圧力（弱気）"
        else:
            net_position = "🟡 中立（様子見）"

        return {
            "bullish_score": bullish_score,
            "bearish_score": bearish_score,
            "net_position": net_position,
            "indicators": {
                "先物建玉": round(futures_signal, 1),
                "オプション比率": round(put_call_signal, 1),
                "決済売却圧": round(closing_pressure, 1),
                "安全資産逃避": round(safe_haven_signal, 1),
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    except Exception as e:
        print(f"機関投資家動向分析エラー: {e}")
        return {
            "bullish_score": 50,
            "bearish_score": 50,
            "net_position": "🟡 分析中...",
            "indicators": {},
            "timestamp": "N/A",
        }


def get_typical_institutional_moves() -> str:
    """
    時間帯別の機関投資家の典型的な行動パターンを返す。
    """
    now = datetime.now()
    hour = now.hour

    if hour < 9:
        return """
        🌅 **朝（寄付き前）**
        - NY市場の終値を反映した指値注文が入る
        - 機関投資家は大口買いの準備
        - スケールイン戦略を用意
        """
    elif hour < 11:
        return """
        📈 **前場（9:00-11:30）**
        - 大口機関投資家が実際に買い付け
        - 個人投資家の売却に乗じた買い
        - 業績好調な成長企業に集中
        """
    elif hour < 15:
        return """
        ☀️ **昼（11:30-15:00）**
        - 前場の買い持ちをポジション調整
        - 午後の戻り売りを狙う投機筋
        - ポジション確定の売却が増加
        """
    else:
        return """
        🌙 **後場（15:00以降）**
        - NY市場への対応を準備
        - 決済売却で利益確定
        - 明日への仕込みを検討中
        """
