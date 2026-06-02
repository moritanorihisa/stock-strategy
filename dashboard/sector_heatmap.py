"""
セクターヒートマップモジュール
業種別の予測スコア・リターン・AI関連度を視覚化する。
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import streamlit as st
from data.loader import JP_SECTOR_ETFS


# AI関連度マッピング（0-100スケール）
AI_RELEVANCE = {
    "1615.T": 20,   # 銀行業：金融AI
    "1617.T": 10,   # 食品：低い
    "1618.T": 15,   # エネルギー資源：スマートグリッド関連
    "1619.T": 30,   # 建設・資材：スマートシティ
    "1620.T": 25,   # 素材・化学：プロセス最適化
    "1621.T": 35,   # 医薬品：AI創薬
    "1622.T": 40,   # 自動車・輸送機：自動運転
    "1623.T": 20,   # 鉄鋼・非鉄：製造効率化
    "1624.T": 40,   # 機械：ロボティクス
    "1625.T": 90,   # 電機・精密：AI チップ（最重要）
    "1626.T": 85,   # 情報通信：クラウド・AI（最重要）
    "1627.T": 25,   # 電力・ガス：スマートグリッド
    "1628.T": 50,   # 不動産：スマートビル
    "1629.T": 45,   # 小売業：リテールAI
    "1630.T": 35,   # 運輸・物流：自動化・ロジスティクス
    "1631.T": 25,   # 金融（除く銀行）：フィンテック
}


def create_sector_heatmap(predictions: pd.DataFrame) -> go.Figure:
    """
    セクターの予測スコアをヒートマップで表示。
    各セクターのAI関連度で色を調整。
    """
    latest_pred = predictions.iloc[-1]

    # データの整理
    sectors = []
    scores = []
    ai_relevance = []
    colors = []

    for col in latest_pred.index:
        ticker = col.replace("JP_", "").replace("_intraday", "")
        sector_name = JP_SECTOR_ETFS.get(ticker, ticker)
        score = latest_pred[col]

        sectors.append(sector_name)
        scores.append(score)
        ai_rel = AI_RELEVANCE.get(ticker, 50)
        ai_relevance.append(ai_rel)

        # スコアと AI 関連度で色を決定
        if score > 0.5:
            colors.append(f"rgba(0, 200, 136, {0.5 + ai_rel/200})")  # 緑（上昇予測 + AI度）
        elif score < -0.5:
            colors.append(f"rgba(255, 68, 68, {0.5 + (100-ai_rel)/200})")  # 赤（下落予測）
        else:
            colors.append(f"rgba(255, 170, 0, 0.5)")  # 黄（中立）

    # ソート（スコア順）
    sorted_indices = np.argsort(scores)[::-1]
    sectors = [sectors[i] for i in sorted_indices]
    scores = [scores[i] for i in sorted_indices]
    ai_relevance = [ai_relevance[i] for i in sorted_indices]
    colors = [colors[i] for i in sorted_indices]

    # グラフ作成
    fig = go.Figure(data=[
        go.Bar(
            y=sectors,
            x=scores,
            orientation='h',
            marker=dict(color=colors, line=dict(color='white', width=2)),
            text=[f"AI度: {ar}%" for ar in ai_relevance],
            textposition='auto',
            hovertemplate='<b>%{y}</b><br>予測スコア: %{x:.4f}<br>AI関連度: %{text}<extra></extra>',
        )
    ])

    fig.update_layout(
        title="📊 セクター別予測スコア＆AI関連度",
        xaxis_title="予測スコア",
        yaxis_title="業種",
        height=600,
        margin=dict(l=200),
        hovermode='y unified',
    )

    return fig


def create_ai_sector_highlights() -> pd.DataFrame:
    """
    AI関連度トップセクターを強調表示。
    """
    ai_sorted = sorted(AI_RELEVANCE.items(), key=lambda x: x[1], reverse=True)

    highlights = []
    for ticker, ai_score in ai_sorted[:5]:
        sector_name = JP_SECTOR_ETFS.get(ticker, ticker)
        highlights.append({
            "ティッカー": ticker,
            "業種": sector_name,
            "AI関連度": f"{ai_score}%",
            "説明": _get_ai_explanation(ticker),
        })

    return pd.DataFrame(highlights)


def _get_ai_explanation(ticker: str) -> str:
    """AI関連度の説明を返す。"""
    explanations = {
        "1625.T": "AI チップ製造・半導体",
        "1626.T": "クラウド・データセンター",
        "1622.T": "自動運転・EV 関連",
        "1628.T": "スマートビル・スマートシティ",
        "1629.T": "リテール AI・自動決済",
        "1621.T": "AI 創薬・医療 AI",
        "1624.T": "ロボティクス・FA",
        "1630.T": "物流自動化・配送 AI",
        "1619.T": "スマートシティインフラ",
    }
    return explanations.get(ticker, "AI関連度は低い")


def render_sector_heatmap_tab(predictions: pd.DataFrame) -> None:
    """
    セクターヒートマップタブを描画。
    """
    st.subheader("🔥 セクターヒートマップ＆AI関連度")

    # ヒートマップ表示
    fig = create_sector_heatmap(predictions)
    st.plotly_chart(fig, use_container_width=True)

    # AI関連セクターのハイライト
    st.divider()
    st.markdown("### 🤖 AI関連度トップセクター")
    col1, col2 = st.columns([2, 1])

    with col1:
        ai_highlights = create_ai_sector_highlights()
        st.dataframe(ai_highlights, use_container_width=True, hide_index=True)

    with col2:
        st.info("""
        **AI関連度とは**

        テクノロジー産業の成長に直結する業種の度合い。

        ✅ **高い（75%以上）**
        - 電機・精密
        - 情報通信

        🟡 **中程度（40-70%）**
        - 自動車・輸送機
        - 機械
        - 医薬品

        ⚠️ **低い（20%以下）**
        - 食品
        - エネルギー
        """)

    # 解説
    st.divider()
    with st.expander("📚 AI時代のセクター戦略"):
        st.markdown("""
        ### AI時代の投資戦略

        **高AI度セクターの特徴**
        - 長期的な上昇トレンド（テック産業成長）
        - ボラティリティが高い（リスク・リターン大）
        - 米国テック企業の好調が直結

        **低AI度セクターの特徴**
        - 景気循環型（経済サイクルに連動）
        - 相対的に安定（ディフェンシブ）
        - 資源価格やドル相場に影響

        ### 売買アイデア
        1. **AI度の高いセクター**: 米国テック企業の好調をキャッチして買い
        2. **AI度の低いセクター**: リセッション時の防御銘柄として活用
        3. **バランス**: 両者をポートフォリオに混在させてリスク分散
        """)
