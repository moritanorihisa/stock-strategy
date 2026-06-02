"""
市場サマリーモジュール
主要指数の当日騰落・VIX・ドル円を取得して
ダッシュボードに表示するための集計を行う。
"""

import streamlit as st
import pandas as pd
import yfinance as yf


# 主要指数ティッカー
INDEX_TICKERS = {
    "日経225":    "^N225",
    "TOPIX":      "1306.T",
    "S&P500":     "^GSPC",
    "NASDAQ":     "^IXIC",
    "VIX（恐怖指数）": "^VIX",
    "ドル円":     "JPY=X",
}


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_market_overview() -> pd.DataFrame:
    """主要指数の直近2日分を取得して前日比を計算する。"""
    rows = []
    for name, ticker in INDEX_TICKERS.items():
        try:
            raw = yf.download(ticker, period="5d", auto_adjust=True, progress=False)
            if isinstance(raw.columns, pd.MultiIndex):
                raw = raw.xs(ticker, axis=1, level=1)
            close = raw["Close"].dropna().squeeze()
            if len(close) < 2:
                continue
            last    = float(close.iloc[-1])
            prev    = float(close.iloc[-2])
            change  = (last - prev) / prev * 100
            rows.append({
                "指数・通貨": name,
                "ticker":     ticker,
                "現在値":     last,
                "前日比(%)":  round(change, 2),
            })
        except Exception:
            pass
    return pd.DataFrame(rows)


def render_market_bar(df: pd.DataFrame) -> None:
    """市場概況をコンパクトな横並びメトリクスで表示する。"""
    if df.empty:
        st.caption("市場データを取得できませんでした")
        return

    cols = st.columns(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        chg  = row["前日比(%)"]
        sign = "+" if chg >= 0 else ""
        cols[i].metric(
            label=row["指数・通貨"],
            value=f"{row['現在値']:,.2f}",
            delta=f"{sign}{chg:.2f}%",
        )


def get_market_mood(df: pd.DataFrame) -> tuple[str, str]:
    """
    市場全体の雰囲気を文字列で返す。
    VIXと主要指数の騰落から判定。

    Returns
    -------
    mood_label : str  例「リスクオン」
    mood_color : str  CSSカラーコード
    """
    if df.empty:
        return "データなし", "#888"

    vix_row = df[df["ticker"] == "^VIX"]
    sp_row  = df[df["ticker"] == "^GSPC"]

    vix_val = float(vix_row["現在値"].values[0]) if not vix_row.empty else 20.0
    sp_chg  = float(sp_row["前日比(%)"].values[0]) if not sp_row.empty else 0.0

    if vix_val < 15 and sp_chg > 0:
        return "🟢 リスクオン（強気）", "#00cc88"
    elif vix_val > 25 or sp_chg < -1.5:
        return "🔴 リスクオフ（警戒）", "#ff4444"
    elif vix_val > 20:
        return "🟡 やや不安定", "#ffaa00"
    else:
        return "🔵 中立・様子見", "#4488ff"
