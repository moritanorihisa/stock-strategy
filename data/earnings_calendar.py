"""
決算カレンダーモジュール
重要企業の決算発表予定を表示。
"""

import pandas as pd
import streamlit as st
from datetime import datetime, timedelta


# 重要企業の決算予定（手動管理版）
# 実運用ではIEX Cloud, Finnhub等のAPIを使用
MAJOR_EARNINGS = [
    # テック企業（AI関連）
    {
        "company": "NVIDIA",
        "ticker": "NVDA",
        "date": "2026-06-15",
        "importance": "⭐⭐⭐⭐⭐",
        "reason": "AI チップメーカー最大手。決算で市場が動く。",
        "impact": "日本：電機・精密セクターに直結",
    },
    {
        "company": "Apple",
        "ticker": "AAPL",
        "date": "2026-07-20",
        "importance": "⭐⭐⭐⭐",
        "reason": "世界最大企業。S&P500の約7%を占める。",
        "impact": "日本：全体相場に影響",
    },
    {
        "company": "Microsoft",
        "ticker": "MSFT",
        "date": "2026-07-18",
        "importance": "⭐⭐⭐⭐",
        "reason": "AI/クラウド企業。OpenAI投資で注目。",
        "impact": "日本：情報通信セクターに影響",
    },
    {
        "company": "Tesla",
        "ticker": "TSLA",
        "date": "2026-07-19",
        "importance": "⭐⭐⭐",
        "reason": "EV・自動運転のリーダー。ボラティリティ高。",
        "impact": "日本：自動車・輸送機セクター",
    },
    {
        "company": "Amazon",
        "ticker": "AMZN",
        "date": "2026-07-22",
        "importance": "⭐⭐⭐⭐",
        "reason": "クラウド（AWS）が主要事業。AI投資も活発。",
        "impact": "日本：情報通信セクター",
    },
    # 日本企業
    {
        "company": "トヨタ自動車",
        "ticker": "7203.T",
        "date": "2026-05-18",
        "importance": "⭐⭐⭐⭐",
        "reason": "日本を代表する大企業。決算で相場が大きく動く。",
        "impact": "日本：自動車・輸送機セクターに直結",
    },
    {
        "company": "ソニー",
        "ticker": "6758.T",
        "date": "2026-05-26",
        "importance": "⭐⭐⭐",
        "reason": "テック企業。ゲーム・エレクトロニクス中心。",
        "impact": "日本：電機・精密セクター",
    },
]


@st.cache_data(ttl=3600)
def get_upcoming_earnings(days_ahead: int = 60) -> pd.DataFrame:
    """
    今後の重要な決算予定を取得。

    Parameters
    ----------
    days_ahead : int
        今日から何日先までの決算を取得

    Returns
    -------
    pd.DataFrame
        決算予定表
    """
    today = datetime.now().date()
    upcoming = []

    for earning in MAJOR_EARNINGS:
        earn_date = datetime.strptime(earning["date"], "%Y-%m-%d").date()
        days_until = (earn_date - today).days

        if 0 <= days_until <= days_ahead:
            upcoming.append({
                "企業": earning["company"],
                "ティッカー": earning["ticker"],
                "決算日": earn_date.strftime("%m月%d日"),
                "重要度": earning["importance"],
                "日数": f"{days_until}日後",
                "影響セクター": earning["impact"],
            })

    return pd.DataFrame(upcoming).sort_values("日数")


def get_next_major_earnings() -> dict:
    """
    最も近い重要決算を取得。
    """
    today = datetime.now().date()

    for earning in sorted(MAJOR_EARNINGS, key=lambda x: x["date"]):
        earn_date = datetime.strptime(earning["date"], "%Y-%m-%d").date()
        if earn_date >= today:
            days_until = (earn_date - today).days
            return {
                "company": earning["company"],
                "date": earn_date.strftime("%Y年%m月%d日"),
                "days_until": days_until,
                "importance": earning["importance"],
                "reason": earning["reason"],
                "impact": earning["impact"],
            }

    return None


def render_earnings_alert() -> None:
    """
    緊急：次の重要決算アラート。
    """
    next_earning = get_next_major_earnings()

    if next_earning:
        if next_earning["days_until"] <= 7:
            st.warning(f"""
            🚨 **緊急：重要決算が迫っています！**

            **{next_earning['company']} ({next_earning['importance']})**
            - 決算日：{next_earning['date']}（あと{next_earning['days_until']}日）
            - {next_earning['reason']}
            - 日本への影響：{next_earning['impact']}

            **⚠️ 決算前後は大きく相場が変動する可能性があります。**
            """)
        elif next_earning["days_until"] <= 30:
            st.info(f"""
            📅 **注目決算予定**

            {next_earning['company']}
            - 決算日：{next_earning['date']}（あと{next_earning['days_until']}日）
            - {next_earning['reason']}
            """)


def render_earnings_calendar_tab() -> None:
    """
    決算カレンダータブを描画。
    """
    st.subheader("📅 決算カレンダー")
    st.caption("今後30日間の重要決算予定")

    # アラート
    render_earnings_alert()

    st.divider()

    # テーブル表示
    earnings_df = get_upcoming_earnings(days_ahead=30)

    if not earnings_df.empty:
        st.dataframe(earnings_df, use_container_width=True, hide_index=True)
    else:
        st.info("今後30日間に重要決算の予定はありません。")

    # 解説
    st.divider()
    with st.expander("📚 決算カレンダーの活用方法"):
        st.markdown("""
        ### 決算発表のインパクト

        **決算発表前（1週間前）**
        - 期待値が織り込まれる
        - ボラティリティが上昇することもある
        - リスク管理を強化すべき期間

        **決算発表当日～翌日**
        - 決算内容によって大きく変動
        - 営利も重要だが、ガイダンスに注目
        - AI企業は特に技術ロードマップに注目

        **決算後**
        - 3-5営業日かけて方向性が確定することが多い
        - 市場全体への波及を観察

        ### 投資のコツ

        1. **NVIDIA決算** → テック全体＆日本電機・精密セクターが上昇/下落
        2. **Apple決算** → 消費者動向が見える → 日本小売業に影響
        3. **日本企業決算** → 為替（ドル円）の影響も考慮
        """)
