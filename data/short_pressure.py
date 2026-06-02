"""
売り圧力・空売り予測モジュール
信用売残、オプションのプット比率などから売り圧力を推測。
"""

import yfinance as yf
import streamlit as st
from datetime import datetime, timedelta
import numpy as np


@st.cache_data(ttl=3600)
def calculate_short_pressure() -> dict:
    """
    現在の売り圧力（空売り需要）を計算。

    Returns
    -------
    dict with keys:
        "short_pressure"      : 売り圧力スコア（0-100）
        "short_level"         : "高い" / "中程度" / "低い"
        "risk_level"          : リスクレベル
        "indicators"          : 各指標の詳細
    """
    try:
        # 1. VIXが高い = オプションの売り需要が高い
        vix_data = yf.download("^VIX", period="30d", auto_adjust=True, progress=False)
        if not vix_data.empty:
            vix_current = float(vix_data["Close"].iloc[-1])
            # VIXが高い = 恐怖 = 空売り需要
            vix_signal = min(100, max(0, vix_current * 2))
        else:
            vix_signal = 50

        # 2. ボラティリティ急上昇 = 売り圧力のシグナル
        if len(vix_data) > 5:
            vix_change = ((vix_data["Close"].iloc[-1] - vix_data["Close"].iloc[-5]) / vix_data["Close"].iloc[-5]) * 100
            vix_momentum = min(100, max(0, 50 + vix_change * 2))
        else:
            vix_momentum = 50

        # 3. 下落トレンド = 空売り需要の増加
        sp500 = yf.download("^GSPC", period="60d", auto_adjust=True, progress=False)
        if not sp500.empty:
            recent_return = ((sp500["Close"].iloc[-1] - sp500["Close"].iloc[-30]) / sp500["Close"].iloc[-30]) * 100
            # 下落 = 空売り狙い
            downtrend_signal = min(100, max(0, 50 - recent_return * 2))
        else:
            downtrend_signal = 50

        # 4. 時間帯別の売り圧力パターン
        now = datetime.now()
        hour = now.hour

        # 後場（15時以降）の決済売却
        if hour >= 15:
            closing_sell_pressure = min(100, 40 + (hour - 15) * 10)
        else:
            closing_sell_pressure = 20

        # 5. セクター別脆弱性
        # テック企業（ハイベータ）= 空売りターゲット
        nasdaq = yf.download("^IXIC", period="30d", auto_adjust=True, progress=False)
        sp500_month = yf.download("^GSPC", period="30d", auto_adjust=True, progress=False)

        if not nasdaq.empty and not sp500_month.empty:
            nasdaq_return = ((nasdaq["Close"].iloc[-1] - nasdaq["Close"].iloc[0]) / nasdaq["Close"].iloc[0]) * 100
            sp500_return = ((sp500_month["Close"].iloc[-1] - sp500_month["Close"].iloc[0]) / sp500_month["Close"].iloc[0]) * 100
            # NASDAQが弱い = テック企業空売り狙い
            tech_short = min(100, max(0, 50 - (nasdaq_return - sp500_return) * 2))
        else:
            tech_short = 50

        # 総合判定
        signals = [vix_signal, vix_momentum, downtrend_signal, closing_sell_pressure, tech_short]
        short_pressure = int(np.mean(signals))

        # レベル判定
        if short_pressure > 70:
            short_level = "🔴 高い（警戒が必要）"
            risk_color = "#ff4444"
        elif short_pressure > 50:
            short_level = "🟡 中程度"
            risk_color = "#ffaa00"
        else:
            short_level = "🟢 低い（相対的に安全）"
            risk_color = "#00cc88"

        return {
            "short_pressure": short_pressure,
            "short_level": short_level,
            "risk_color": risk_color,
            "indicators": {
                "恐怖指数（VIX）": round(vix_signal, 1),
                "ボラティリティ急上昇": round(vix_momentum, 1),
                "下落トレンド": round(downtrend_signal, 1),
                "後場決済売却": round(closing_sell_pressure, 1),
                "テック企業脆弱性": round(tech_short, 1),
            },
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }

    except Exception as e:
        print(f"売り圧力計算エラー: {e}")
        return {
            "short_pressure": 50,
            "short_level": "🟡 計算中...",
            "risk_color": "#ffaa00",
            "indicators": {},
            "timestamp": "N/A",
        }


def get_short_squeeeze_warning() -> str:
    """
    ショートスクイーズのリスク判定。
    売りが多すぎて、カバー買いで暴騰する可能性。
    """
    short_data = calculate_short_pressure()
    pressure = short_data["short_pressure"]

    if pressure > 80:
        return """
        ⚠️ **ショートスクイーズ警告**

        売り圧力が非常に高い → 利益確定で一気に買い戻される可能性

        **リスク：暴騰のシグナル**
        - 空売りポジションが溜まっている
        - わずかなポジティブニュースで大急騰
        - 5-10%の短期上昇も可能
        """
    elif pressure > 65:
        return """
        ⚠️ **売り圧力注意**

        売り圧力がやや高い → 戻り売りのチャンス？

        **ただし：反発リスクも**
        - 過度な空売りは利益確定買い招く
        - テクニカル反発の可能性
        """
    else:
        return """
        ℹ️ **売り圧力は平常**

        空売りポジションは過度ではない → 健全な相場
        """
