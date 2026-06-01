"""
AI成長株スクリーナー UIコンポーネント
app.py のタブから呼び出して使う。
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from growth.growth_loader import fetch_price_data, calc_features
from growth.growth_model  import calc_scores, stars, risk_label, buy_timing, sell_timing_short, sell_timing_nisa
from growth.watchlist     import IPO_WATCHLIST


@st.cache_data(ttl=3600, show_spinner="AI成長株データを取得中...")
def load_growth_data() -> pd.DataFrame:
    price_data = fetch_price_data(period="1y")
    features   = calc_features(price_data)
    scores     = calc_scores(features)
    return scores


def render_growth_tab():
    """タブ5「🚀 AI成長株スクリーナー」の全コンテンツを描画する。"""

    st.subheader("🚀 NISA向け AI成長株スクリーナー")
    st.warning(
        "⚠️ このランキングは過去データの統計パターンに基づく **検証用シグナル** です。"
        "将来の値動きを保証するものではありません。投資助言ではありません。",
        icon="⚠️",
    )

    with st.spinner("データを取得・計算中..."):
        try:
            df = load_growth_data()
        except Exception as e:
            st.error(f"データ取得に失敗しました: {e}")
            return

    # ===== フィルター =====
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        min_prob = st.slider("上昇確率フィルター（以上）", 40, 80, 50, step=5, format="%d%%")
    with col_f2:
        show_n = st.slider("表示件数", 5, len(df), min(10, len(df)))

    filtered = df[df["up_prob_pct"] >= min_prob].head(show_n)

    if filtered.empty:
        st.info("条件に合う銘柄がありません。フィルターを緩めてください。")
        return

    # ===== ランキングカード =====
    st.markdown("### 📊 上昇期待ランキング（過去データ上の期待値）")
    st.caption("※「上昇確率」「予測上昇幅」はいずれも過去60営業日のパターンに基づく統計値です")

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 20

    for rank, (_, row) in enumerate(filtered.iterrows(), 1):
        medal      = medals[rank - 1] if rank <= len(medals) else f"{rank}位"
        score      = row.get("score", 0)
        name       = row.get("name",    row["ticker"])
        category   = row.get("category", "")
        comment    = row.get("comment",  "")
        nisa_s     = int(row.get("nisa_stars", 3))
        risk_s     = int(row.get("risk_stars", 3))
        up_prob    = row.get("up_prob_pct",    0)
        pred_ret   = row.get("pred_return_pct", 0)
        price      = row.get("current_price",   0)

        color = "#0d3b2e" if pred_ret >= 0 else "#3b0d0d"
        border_color = "#00cc88" if pred_ret >= 0 else "#ff4444"

        st.markdown(f"""
        <div style="background:{color};border-left:6px solid {border_color};
                    padding:16px 20px;border-radius:10px;margin-bottom:12px;">
          <div style="font-size:1.5rem;font-weight:900;">
            {medal} {rank}位　{name}（{row['ticker']}）
          </div>
          <div style="color:#aaa;font-size:0.85rem;margin-bottom:8px;">
            📂 {category}
          </div>
          <hr style="border-color:#333;margin:8px 0">
          <table style="width:100%;border-collapse:collapse;">
            <tr>
              <td style="padding:4px 8px;"><b>🎯 AI期待スコア</b></td>
              <td style="padding:4px 8px;font-size:1.3rem;font-weight:900;color:#ffd700;">{score:.0f} 点 / 100点</td>
              <td style="padding:4px 8px;"><b>📈 予測上昇幅</b></td>
              <td style="padding:4px 8px;font-weight:bold;color:{'#00cc88' if pred_ret>=0 else '#ff4444'};">
                {'+' if pred_ret >= 0 else ''}{pred_ret:.2f}%
                <span style="color:#888;font-size:0.8rem;">（過去平均期待値）</span>
              </td>
            </tr>
            <tr>
              <td style="padding:4px 8px;"><b>🎲 上昇確率</b></td>
              <td style="padding:4px 8px;">{up_prob:.1f}%
                <span style="color:#888;font-size:0.8rem;">（過去60日）</span></td>
              <td style="padding:4px 8px;"><b>💰 現在株価</b></td>
              <td style="padding:4px 8px;">${price:,.2f}</td>
            </tr>
            <tr>
              <td style="padding:4px 8px;"><b>⚠️ リスクレベル</b></td>
              <td style="padding:4px 8px;">{stars(risk_s)} {risk_label(risk_s)}</td>
              <td style="padding:4px 8px;"><b>🏦 NISA向き度</b></td>
              <td style="padding:4px 8px;">{stars(nisa_s)}</td>
            </tr>
          </table>
          <hr style="border-color:#333;margin:8px 0">
          <div style="font-size:0.9rem;color:#ccc;">💬 {comment}</div>
        </div>
        """, unsafe_allow_html=True)

        with st.expander(f"📋 {row['ticker']} の売買タイミングと注意点"):
            c1, c2, c3 = st.columns(3)
            with c1:
                st.success(f"**【購入タイミング】**\n\n{buy_timing(row['ticker'])}")
            with c2:
                st.warning(f"**【売却目安（短期）】**\n\n{sell_timing_short(row['ticker'])}")
            with c3:
                st.info(f"**【NISA長期の場合】**\n\n{sell_timing_nisa(row['ticker'])}")
            st.caption("⚠️ これは過去データに基づく参考情報です。確実な利益を保証するものではありません。")

    # ===== 比較チャート =====
    st.divider()
    st.markdown("### 📊 銘柄比較チャート")
    col_c1, col_c2 = st.columns(2)

    with col_c1:
        fig1 = px.bar(
            filtered.sort_values("score"),
            x="score", y="ticker",
            orientation="h",
            color="score",
            color_continuous_scale="YlGn",
            title="AI期待スコア比較",
            labels={"score": "スコア", "ticker": "銘柄"},
        )
        fig1.update_layout(height=400, margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig1, use_container_width=True)

    with col_c2:
        fig2 = px.scatter(
            filtered,
            x="up_prob_pct",
            y="pred_return_pct",
            size="score",
            color="risk_stars",
            color_continuous_scale="RdYlGn_r",
            hover_name="ticker",
            text="ticker",
            title="上昇確率 vs 予測上昇幅",
            labels={
                "up_prob_pct":     "上昇確率（%）",
                "pred_return_pct": "予測上昇幅（%）",
                "risk_stars":      "リスク",
            },
        )
        fig2.update_traces(textposition="top center")
        fig2.update_layout(height=400, margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # ===== CSV出力 =====
    output_cols = ["ticker","name","category","score","up_prob_pct","pred_return_pct",
                   "risk_stars","nisa_stars","current_price"]
    available   = [c for c in output_cols if c in filtered.columns]
    col_rename  = {
        "ticker":"銘柄コード","name":"銘柄名","category":"カテゴリ",
        "score":"AI期待スコア","up_prob_pct":"上昇確率(%)","pred_return_pct":"予測上昇幅(%)",
        "risk_stars":"リスク(1-5)","nisa_stars":"NISA向き(1-5)","current_price":"現在株価($)",
    }
    csv_df    = filtered[available].rename(columns=col_rename)
    csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 ランキングCSVをダウンロード", data=csv_bytes,
                       file_name="ai_growth_ranking.csv", mime="text/csv")

    # ===== IPOウォッチリスト =====
    st.divider()
    st.markdown("### 🛸 近未来の IPO候補ウォッチリスト（未上場企業）")
    st.info("以下は **現在株式市場に上場していない** 企業です。現時点ではNISAを含むいかなる証券口座でも購入できません。上場後の参考情報としてご覧ください。")

    for ipo in IPO_WATCHLIST:
        heat_str = "🔥" * ipo["heat"] + "　" * (5 - ipo["heat"])
        st.markdown(f"""
        <div style="background:#1a1a2e;border-left:6px solid #ff9900;
                    padding:16px 20px;border-radius:10px;margin-bottom:12px;">
          <div style="font-size:1.3rem;font-weight:900;">
            🛸 {ipo['name']}　<span style="color:#aaa;font-size:1rem;">（{ipo['symbol']}）</span>
          </div>
          <div style="margin:6px 0;">
            <b>上場観測度：</b>{heat_str}
            &nbsp;&nbsp;<b>カテゴリ：</b>{ipo['category']}
          </div>
          <div style="margin:6px 0;"><b>想定時価総額：</b>{ipo['valuation']}</div>
          <hr style="border-color:#333;margin:8px 0">
          <div style="color:#ccc;margin-bottom:6px;">📰 {ipo['summary']}</div>
          <div style="color:#aaa;font-size:0.85rem;">🇯🇵 日本人投資家向け：{ipo['jp_note']}</div>
          <div style="color:#ff6666;font-size:0.85rem;margin-top:4px;">⚠️ リスク：{ipo['risk']}</div>
        </div>
        """, unsafe_allow_html=True)
