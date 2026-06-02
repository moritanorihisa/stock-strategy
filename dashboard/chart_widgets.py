"""
ミニチャート小窓ウィジェット
yfinanceで直近データを取得してPlotlyでミニチャートを描画する。
st.cache_data でキャッシュして過剰アクセスを防ぐ。
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import yfinance as yf

from dashboard.link_builder import get_links


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_chart_data(ticker: str, days: int = 60) -> pd.DataFrame:
    """直近N日のOHLCVデータを取得してキャッシュする。"""
    try:
        raw = yf.download(ticker, period=f"{days}d", auto_adjust=True, progress=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw = raw.xs(ticker, axis=1, level=1)
        return raw[["Open", "High", "Low", "Close", "Volume"]].dropna()
    except Exception:
        return pd.DataFrame()


def render_mini_chart(ticker: str, name: str, days: int = 60) -> None:
    """
    銘柄の直近チャートを小窓で表示する。
    ローソク足 + 出来高バーを描画。
    外部リンク（TradingView・Yahoo Finance）も併せて表示。
    """
    df = _fetch_chart_data(ticker, days)

    if df.empty:
        st.caption(f"チャートデータを取得できませんでした（{ticker}）")
        return

    close  = df["Close"].squeeze()
    first  = float(close.iloc[0])
    last   = float(close.iloc[-1])
    change = (last - first) / first * 100
    color  = "#00cc88" if change >= 0 else "#ff4444"

    # ── ミニ折れ線チャート ──
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=close,
        mode="lines",
        line=dict(color=color, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({'0,204,136' if change>=0 else '255,68,68'},0.08)",
        hovertemplate="%{x|%Y/%m/%d}<br>%{y:,.2f}<extra></extra>",
        name="株価",
    ))

    # 直近高値・安値ライン
    high = float(df["High"].max())
    low  = float(df["Low"].min())
    fig.add_hline(y=high, line=dict(color="rgba(255, 255, 255, 0.13)", dash="dot"), annotation_text="高値", annotation_font_size=9)
    fig.add_hline(y=low,  line=dict(color="rgba(255, 255, 255, 0.13)", dash="dot"), annotation_text="安値", annotation_font_size=9)

    fig.update_layout(
        height=180,
        margin=dict(l=0, r=0, t=8, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=True, zeroline=False,
                   tickfont=dict(size=9, color="#aaa")),
        showlegend=False,
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    # 期間サマリー
    st.caption(
        f"直近{days}日間: "
        f"**{'+' if change>=0 else ''}{change:.1f}%** ｜ "
        f"高値 {high:,.1f} ｜ 安値 {low:,.1f}"
    )

    # 外部リンク
    links = get_links(ticker)
    link_parts = [f"[{label}]({url})" for label, url in links.items()]
    st.markdown("🔗 " + "　｜　".join(link_parts))


def render_mini_chart_compact(ticker: str, days: int = 30) -> go.Figure:
    """
    ダッシュボードカード内に埋め込む超コンパクトな折れ線チャートを返す。
    高さ100px・軸なし。
    """
    df = _fetch_chart_data(ticker, days)
    close  = df["Close"].squeeze() if not df.empty else pd.Series(dtype=float)
    change = 0.0
    if len(close) >= 2:
        change = (float(close.iloc[-1]) - float(close.iloc[0])) / float(close.iloc[0]) * 100
    color = "#00cc88" if change >= 0 else "#ff4444"

    fig = go.Figure()
    if not close.empty:
        fig.add_trace(go.Scatter(
            x=list(range(len(close))), y=close.values,
            mode="lines", line=dict(color=color, width=1.5),
            fill="tozeroy",
            fillcolor=f"rgba({'0,204,136' if change>=0 else '255,68,68'},0.1)",
            hoverinfo="skip",
        ))
    fig.update_layout(
        height=80, margin=dict(l=0,r=0,t=0,b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig, change
