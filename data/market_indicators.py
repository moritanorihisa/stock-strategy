"""
市場指標の取得モジュール
VIX、Fear & Greed Index など市場全体の状態を取得。
"""

import yfinance as yf
import streamlit as st
from datetime import datetime


@st.cache_data(ttl=3600, show_spinner="VIX取得中...")
def get_vix() -> dict:
    """
    VIX（恐怖指数）を取得。

    Returns
    -------
    dict with keys:
        "value"       : 現在値（float）
        "change"      : 変化額
        "change_pct"  : 変化率（%）
        "status"      : "低い" / "中程度" / "高い"
        "color"       : "#00cc88" / "#ffaa00" / "#ff4444"
        "timestamp"   : 取得日時
    """
    try:
        data = yf.download("^VIX", period="5d", auto_adjust=True, progress=False)
        if data.empty:
            return _default_vix()

        close = data["Close"]
        current = float(close.iloc[-1])
        previous = float(close.iloc[-2])
        change = current - previous
        change_pct = (change / previous) * 100 if previous != 0 else 0

        if current < 20:
            status = "低い（市場は安心）"
            color = "#00cc88"
        elif current < 30:
            status = "中程度（注意）"
            color = "#ffaa00"
        else:
            status = "高い（恐怖）"
            color = "#ff4444"

        return {
            "value": round(current, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "status": status,
            "color": color,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
    except Exception as e:
        print(f"VIX取得エラー: {e}")
        return _default_vix()


def _default_vix() -> dict:
    """VIX取得失敗時のデフォルト値。"""
    return {
        "value": 0,
        "change": 0,
        "change_pct": 0,
        "status": "データ取得失敗",
        "color": "#aaa",
        "timestamp": "N/A",
    }


@st.cache_data(ttl=3600)
def get_market_temp() -> str:
    """
    市場の温度を簡潔に表示。
    """
    vix = get_vix()
    value = vix["value"]

    if value < 15:
        return "🟢 市場は非常に楽観的"
    elif value < 20:
        return "🟢 市場は楽観的"
    elif value < 25:
        return "🟡 市場は中立的"
    elif value < 30:
        return "🟠 市場は注意深い"
    elif value < 40:
        return "🔴 市場は恐怖"
    else:
        return "🔴 市場は極度の恐怖"
