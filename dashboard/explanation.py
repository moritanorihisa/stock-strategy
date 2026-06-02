"""
初心者向け解説モジュール
「なぜこの銘柄が上昇予測なのか」を簡潔に説明する。
"""

import pandas as pd
import streamlit as st
from data.loader import JP_SECTOR_ETFS, US_SECTOR_ETFS


# セクター日本語説明
SECTOR_EXPLANATIONS = {
    "1615.T": {
        "name": "銀行業",
        "us_related": "XLF（米国金融）",
        "reason": "米国金利が上昇すると、銀行の利ザヤが広がって収益が増加する傾向があります。",
    },
    "1617.T": {
        "name": "食品",
        "us_related": "XLP（米国生活必需品）",
        "reason": "食品は景気に左右されにくい「ディフェンシブセクター」。市場が不安定な時は買われやすい。",
    },
    "1618.T": {
        "name": "エネルギー資源",
        "us_related": "XLE（米国エネルギー）",
        "reason": "原油価格の上昇、地政学的緊張が買い材料。米国石油需要の増加も好材料。",
    },
    "1619.T": {
        "name": "建設・資材",
        "us_related": "XLI（米国資本財）",
        "reason": "インフレ・金利上昇時に建設需要が高まる。また公共事業関連株として好景気の恩恵を受ける。",
    },
    "1620.T": {
        "name": "素材・化学",
        "us_related": "XLB（米国素材）",
        "reason": "世界経済が好調な時（リスク選好）に買われやすい。輸出関連として円安の恩恵も。",
    },
    "1621.T": {
        "name": "医薬品",
        "us_related": "XLV（米国ヘルスケア）",
        "reason": "新薬承認、M&A期待、高齢化による需要増。不況時も買われやすい防御銘柄。",
    },
    "1622.T": {
        "name": "自動車・輸送機",
        "us_related": "XLI（米国資本財）",
        "reason": "EV化進展、燃料電池期待、供給不安の解消。円安も追い風。",
    },
    "1623.T": {
        "name": "鉄鋼・非鉄",
        "us_related": "XLB（米国素材）",
        "reason": "世界的なインフラ投資、脱炭素関連（再生可能エネルギー）の需要増加が好材料。",
    },
    "1625.T": {
        "name": "電機・精密",
        "us_related": "XLK（米国情報技術）",
        "reason": "AIチップ需要、半導体の好況が波及。テック関連として買われやすい。",
    },
    "1626.T": {
        "name": "情報通信",
        "us_related": "XLC（米国通信）, XLK（米国IT）",
        "reason": "5G投資、DX推進、クラウド需要の拡大。テック系セクター全体の好況の恩恵。",
    },
}


def render_explanation_tab(predictions: pd.Series, latest_pred: pd.Series) -> None:
    """
    初心者向けの詳細解説タブを描画。
    """
    st.subheader("💡 なぜこの予測なのか？初心者向け解説")

    with st.expander("📖 戦略の基本的な考え方", expanded=True):
        st.markdown("""
        ### 🌍 日米時差を使った投資戦略

        このツールは以下の「時差」を活用しています：

        1. **米国市場の終値**（日本時間 朝6:00）
           - NY市場が閉じる前に、投資家の買いや売りが決まっている

        2. **日本市場の寄付き～引け**（朝9:00～15:00）
           - 米国市場の情報が入るまでの数時間、まだ反映されていない

        3. **予測の仕組み**
           - 米国セクターETFの前日リターン → 日本セクターの翌日リターンへの波及を機械学習で学習
           - 「米国で○○セクターが上昇 → 日本の□□セクターも上昇する可能性が高い」という相関を活用

        📌 **重要**: これは統計的な相関に基づく予測であり、必ず当たるわけではありません。
        """)

    # 上昇予測トップ3の解説
    st.divider()
    st.subheader("🚀 今日の上昇予測 トップ3")

    top_3 = latest_pred.nlargest(3)
    for rank, (ticker, score) in enumerate(top_3.items(), 1):
        col_ticker = ticker.replace("JP_", "").replace("_intraday", "")
        sector_info = SECTOR_EXPLANATIONS.get(col_ticker, {})
        sector_name = sector_info.get("name", col_ticker)
        us_related = sector_info.get("us_related", "N/A")
        reason = sector_info.get("reason", "詳細情報なし")

        with st.container():
            st.markdown(f"#### #{rank} **{sector_name}** (スコア: {score:.3f})")
            col1, col2 = st.columns(2)
            with col1:
                st.caption(f"🇺🇸 関連する米国ETF: **{us_related}**")
            with col2:
                st.caption(f"💹 予測スコア: **{score:.4f}**")
            st.write(reason)
            st.divider()


def render_simple_explanation(ticker: str) -> str:
    """
    銘柄の1行説明を返す。
    """
    col_ticker = ticker.replace("JP_", "").replace("_intraday", "")
    sector_info = SECTOR_EXPLANATIONS.get(col_ticker, {})
    reason = sector_info.get("reason", "")
    if reason:
        return reason.split("。")[0]  # 最初の文だけ
    return ""
