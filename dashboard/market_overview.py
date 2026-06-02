"""
マーケット概要パネル
ダッシュボードに表示する重要情報の概要。
詳細は別ページで表示。
"""

import streamlit as st
import pandas as pd
from data.earnings_calendar import get_next_major_earnings
from data.institutional_flow import analyze_institutional_sentiment
from data.short_pressure import calculate_short_pressure
from data.news_fetcher import get_japanese_stock_news


def render_market_overview_panels() -> None:
    """
    ダッシュボードに重要情報の概要を4つのパネルで表示。
    """
    col1, col2, col3, col4 = st.columns(4)

    # パネル1：次の重要決算
    with col1:
        next_earning = get_next_major_earnings()
        if next_earning and next_earning["days_until"] <= 30:
            st.markdown(f"""
            <div style="background:#1a3a2e; padding:16px; border-radius:10px; border-left:6px solid #00cc88;">
            <small style="color:#aaa;">📅 次の重要決算</small><br>
            <b style="color:#00cc88;">{next_earning['company']}</b><br>
            <small>{next_earning['importance']}</small><br>
            <tiny style="color:#888;">あと{next_earning['days_until']}日</tiny>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="background:#1a1a2e; padding:16px; border-radius:10px; border-left:6px solid #aaa;">
            <small style="color:#aaa;">📅 決算予定</small><br>
            <tiny>近日予定なし</tiny>
            </div>
            """, unsafe_allow_html=True)

    # パネル2：機関投資家動向
    with col2:
        inst = analyze_institutional_sentiment()
        color = "#00cc88" if inst["bullish_score"] > inst["bearish_score"] else "#ff4444"
        direction = "買い" if inst["bullish_score"] > inst["bearish_score"] else "売り"
        st.markdown(f"""
        <div style="background:#1a1a2e; padding:16px; border-radius:10px; border-left:6px solid {color};">
        <small style="color:#aaa;">🏢 機関投資家</small><br>
        <b style="color:{color};">{direction}圧力</b><br>
        <small style="color:#888;">スコア: {inst['bullish_score']}</small>
        </div>
        """, unsafe_allow_html=True)

    # パネル3：売り圧力
    with col3:
        short = calculate_short_pressure()
        st.markdown(f"""
        <div style="background:#1a1a2e; padding:16px; border-radius:10px; border-left:6px solid {short['risk_color']};">
        <small style="color:#aaa;">📉 売り圧力</small><br>
        <b style="color:{short['risk_color']};">{short['short_pressure']}/100</b><br>
        <small style="color:#888;">{"警戒" if short["short_pressure"] > 70 else "注視"}</small>
        </div>
        """, unsafe_allow_html=True)

    # パネル4：最新ニュース
    with col4:
        news = get_japanese_stock_news(max_results=1)
        if news:
            st.markdown(f"""
            <div style="background:#1a1a2e; padding:16px; border-radius:10px; border-left:6px solid #4488ff;">
            <small style="color:#aaa;">📰 最新ニュース</small><br>
            <small style="color:#4488ff;">{news[0]['title'][:20]}...</small><br>
            <tiny style="color:#888;">クリックで詳細</tiny>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # 各パネルの説明リンク
    col_links = st.columns(4)
    with col_links[0]:
        if st.button("📅 決算詳細", use_container_width=True):
            st.session_state.active_tab = "market_info"
    with col_links[1]:
        if st.button("🏢 機関動向", use_container_width=True):
            st.session_state.active_tab = "market_info"
    with col_links[2]:
        if st.button("📉 売り圧力", use_container_width=True):
            st.session_state.active_tab = "market_info"
    with col_links[3]:
        if st.button("📰 ニュース一覧", use_container_width=True):
            st.session_state.active_tab = "market_info"
