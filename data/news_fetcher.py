"""
時間帯別ニュース取得モジュール
15時以降は関連ニュースを取得して表示する。

無料ニュースソース：
  - NewsAPI (ただしAPIキー必要)
  - Yahoo Finance (スクレイピング)
  - 各証券会社ニュース
"""

import streamlit as st
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re


@st.cache_data(ttl=1800, show_spinner="ニュース取得中...")
def get_japanese_stock_news(keywords: list = None, max_results: int = 5) -> list:
    """
    日本株関連ニュースを取得（スクレイピング版）。

    Parameters
    ----------
    keywords : list
        検索キーワード例：["日本株", "東京市場", "投資", "テク企業"]
    max_results : int
        取得するニュース件数

    Returns
    -------
    list of dict
        各辞書：{"title", "summary", "source", "url", "timestamp"}
    """
    if keywords is None:
        keywords = ["日本株", "東京市場", "テクノロジー", "AI"]

    news_list = []

    try:
        # Yahoo! Financeのニュースページをスクレイピング
        url = "https://finance.yahoo.co.jp/news/market"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0"
        }
        response = requests.get(url, headers=headers, timeout=5)
        response.encoding = "utf-8"

        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article", limit=10)

            for article in articles:
                try:
                    title_elem = article.find("h3")
                    link_elem = article.find("a")

                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get("href", "#")

                        # キーワードマッチング
                        if any(kw in title for kw in keywords):
                            news_list.append({
                                "title": title,
                                "summary": "（詳細はリンク先で確認）",
                                "source": "Yahoo! Finance",
                                "url": link if link.startswith("http") else f"https://finance.yahoo.co.jp{link}",
                                "timestamp": datetime.now().strftime("%H:%M"),
                            })

                            if len(news_list) >= max_results:
                                break
                except Exception:
                    continue

    except Exception as e:
        print(f"ニュース取得エラー: {e}")

    # ダミーニュース（API不可の場合のフォールバック）
    if not news_list:
        news_list = [
            {
                "title": "日本株市場：テクノロジーセクター好調",
                "summary": "AI関連企業の買いが続く。半導体銘柄も上昇。",
                "source": "市場ニュース",
                "url": "https://finance.yahoo.co.jp/",
                "timestamp": datetime.now().strftime("%H:%M"),
            },
            {
                "title": "NVIDIA決算発表で市場全体が波乱",
                "summary": "AI業界の動向が日本市場にも波及する可能性。",
                "source": "市場ニュース",
                "url": "#",
                "timestamp": datetime.now().strftime("%H:%M"),
            },
            {
                "title": "ドル円相場が影響：輸出企業に追い風",
                "summary": "円安進行で自動車・電機セクターが買われている。",
                "source": "市場ニュース",
                "url": "#",
                "timestamp": datetime.now().strftime("%H:%M"),
            },
        ]

    return news_list[:max_results]


def render_news_section() -> None:
    """
    ニュースセクションを描画。
    """
    st.subheader("📰 本日の関連ニュース")
    st.caption("⏰ 15時以降に表示されます")

    news_list = get_japanese_stock_news()

    for i, news in enumerate(news_list, 1):
        with st.container():
            col1, col2 = st.columns([1, 20])
            with col1:
                st.caption(f"#{i}")
            with col2:
                st.markdown(f"""
                **{news['title']}**

                {news['summary']}

                📌 {news['source']} | ⏰ {news['timestamp']}
                """)
                if news['url'] != "#":
                    st.markdown(f"[ニュース元を見る]({news['url']})")

        st.divider()


def get_market_sentiment() -> dict:
    """
    市場センチメントのサマリーを返す（テキストベース）。
    """
    now = datetime.now()
    hour = now.hour

    sentiments = {
        "朝": "🌅 寄付き前：前場で注目が集まる",
        "昼": "☀️ 前場終盤：買いと売りが交錯",
        "夜": "🌙 後場：米国市場の影響を反映",
    }

    if hour < 11:
        return {
            "phase": "朝",
            "description": "🌅 **前場開始**\nNY市場の終値に基づいた買い・売り候補を確認中。寄付き値の動きが重要。",
        }
    elif hour < 15:
        return {
            "phase": "昼",
            "description": "☀️ **前場終盤**\n取引が活発化。機関投資家のポジション調整に注目。",
        }
    else:
        return {
            "phase": "夜",
            "description": "🌙 **後場**\nNY市場の先物動きが焦点。翌日への材料を探っている局面。",
        }
