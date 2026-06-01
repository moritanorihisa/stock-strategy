"""
AI成長株スクリーナー UIコンポーネント
app.py のタブから render_growth_tab() を呼び出して使う。

構成:
  1. 米国AI成長株ランキング（翌日予測スコア順）
  2. 日本成長株ランキング（翌日予測スコア順）
  3. IPO候補ウォッチリスト（未上場）
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from growth.growth_loader import (
    fetch_us_price_data,
    fetch_jp_price_data,
    calc_features,
)
from growth.growth_model import (
    calc_scores,
    stars, risk_label,
    buy_timing_us, buy_timing_jp,
    sell_timing_short, sell_timing_nisa,
    price_display,
)
from growth.watchlist import IPO_WATCHLIST


# ── キャッシュ付きデータ取得 ──────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="米国AI株データを取得中...")
def _load_us_scores() -> pd.DataFrame:
    price_data = fetch_us_price_data(period="1y")
    features   = calc_features(price_data, market="US")
    return calc_scores(features)


@st.cache_data(ttl=3600, show_spinner="日本成長株データを取得中...")
def _load_jp_scores() -> pd.DataFrame:
    price_data = fetch_jp_price_data(period="1y")
    features   = calc_features(price_data, market="JP")
    return calc_scores(features)


# ── カードUI部品 ──────────────────────────────────────────────

def _render_stock_card(rank: int, row: pd.Series, is_jp: bool = False) -> None:
    """1銘柄のカードを描画する。"""
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 30
    medal  = medals[rank - 1] if rank <= len(medals) else f"{rank}位"

    score      = float(row.get("score", 0))
    name       = str(row.get("name", row["ticker"]))
    category   = str(row.get("category", ""))
    comment    = str(row.get("comment", ""))
    nisa_s     = int(row.get("nisa_stars", 3))
    risk_s     = int(row.get("risk_stars", 3))
    up_prob    = float(row.get("up_prob_pct", 0))
    pred_ret   = float(row.get("pred_return_pct", 0))
    price      = float(row.get("current_price", 0))
    currency   = str(row.get("currency", "JPY" if is_jp else "USD"))
    ticker     = str(row["ticker"])

    color        = "#0d3b2e" if pred_ret >= 0 else "#3b0d0d"
    border_color = "#00cc88" if pred_ret >= 0 else "#ff4444"
    ret_color    = "#00cc88" if pred_ret >= 0 else "#ff4444"
    ret_sign     = "+" if pred_ret >= 0 else ""

    st.markdown(f"""
    <div style="background:{color};border-left:6px solid {border_color};
                padding:16px 20px;border-radius:10px;margin-bottom:12px;">
      <div style="font-size:1.4rem;font-weight:900;">
        {medal} {rank}位　{name}（{ticker}）
      </div>
      <div style="color:#aaa;font-size:0.85rem;margin-bottom:8px;">📂 {category}</div>
      <hr style="border-color:#333;margin:8px 0">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:4px 8px;width:50%">
            <b>🎯 AI期待スコア</b><br>
            <span style="font-size:1.5rem;font-weight:900;color:#ffd700;">{score:.0f}点</span>
            <span style="color:#888;font-size:0.8rem;"> / 100点</span>
          </td>
          <td style="padding:4px 8px;width:50%">
            <b>📈 翌日予測上昇幅</b><br>
            <span style="font-size:1.3rem;font-weight:bold;color:{ret_color};">
              {ret_sign}{pred_ret:.2f}%
            </span>
            <span style="color:#888;font-size:0.75rem;"><br>（過去類似パターンの期待値）</span>
          </td>
        </tr>
        <tr>
          <td style="padding:4px 8px;">
            <b>🎲 上昇確率</b><br>
            <span style="font-size:1.1rem;">{up_prob:.1f}%</span>
            <span style="color:#888;font-size:0.75rem;">（過去60日）</span>
          </td>
          <td style="padding:4px 8px;">
            <b>💰 現在株価</b><br>
            <span style="font-size:1.1rem;">{price_display(price, currency)}</span>
          </td>
        </tr>
        <tr>
          <td style="padding:4px 8px;">
            <b>⚠️ リスクレベル</b><br>
            {stars(risk_s)} {risk_label(risk_s)}
          </td>
          <td style="padding:4px 8px;">
            <b>🏦 NISA向き度</b><br>
            {stars(nisa_s)}
          </td>
        </tr>
      </table>
      <hr style="border-color:#333;margin:8px 0">
      <div style="font-size:0.9rem;color:#ccc;">💬 {comment}</div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"📋 {ticker} の売買タイミング・注意点"):
        c1, c2, c3 = st.columns(3)
        timing_fn = buy_timing_jp if is_jp else buy_timing_us
        with c1:
            st.success(f"**【購入タイミング】**\n\n{timing_fn(ticker)}")
        with c2:
            st.warning(f"**【売却目安（短期検証）】**\n\n{sell_timing_short()}")
        with c3:
            st.info(f"**【NISA長期の場合】**\n\n{sell_timing_nisa()}")
        st.caption("⚠️ 過去データに基づく参考情報です。確実な利益を保証するものではありません。")


def _render_ranking_section(
    df: pd.DataFrame,
    title: str,
    is_jp: bool,
    min_prob: int,
    show_n: int,
) -> None:
    """米国 or 日本のランキングセクションを描画する。"""
    st.markdown(f"### {title}")
    st.caption("※「上昇確率」「予測上昇幅」はいずれも過去データの統計的期待値です")

    filtered = df[df["up_prob_pct"] >= min_prob].head(show_n)

    if filtered.empty:
        st.info("条件に合う銘柄がありません。上昇確率フィルターを下げてください。")
        return

    for rank, (_, row) in enumerate(filtered.iterrows(), 1):
        _render_stock_card(rank, row, is_jp=is_jp)

    # 比較チャート
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(
            filtered.sort_values("score"),
            x="score", y="ticker", orientation="h",
            color="score", color_continuous_scale="YlGn",
            title="AI期待スコア比較",
            labels={"score": "スコア", "ticker": "銘柄"},
        )
        fig1.update_layout(height=max(300, len(filtered) * 30), margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = px.scatter(
            filtered,
            x="up_prob_pct", y="pred_return_pct",
            size="score", color="risk_stars",
            color_continuous_scale="RdYlGn_r",
            hover_name="ticker", text="ticker",
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

    # CSV
    col_map = {
        "ticker":"銘柄コード","name":"銘柄名","category":"カテゴリ",
        "score":"AI期待スコア","up_prob_pct":"上昇確率(%)","pred_return_pct":"予測上昇幅(%)",
        "risk_stars":"リスク(1-5)","nisa_stars":"NISA向き(1-5)","current_price":"現在株価",
    }
    available = [c for c in col_map if c in filtered.columns]
    csv_bytes = filtered[available].rename(columns=col_map).to_csv(index=False).encode("utf-8-sig")
    prefix = "jp" if is_jp else "us"
    st.download_button(
        f"📥 {title} CSVをダウンロード",
        data=csv_bytes,
        file_name=f"{prefix}_growth_ranking.csv",
        mime="text/csv",
    )


# ── メイン描画関数 ────────────────────────────────────────────

def render_growth_tab() -> None:
    """タブ「🚀 AI成長株・日本株予測」の全コンテンツを描画する。"""

    st.subheader("🚀 AI成長株・日本株 翌日予測スクリーナー")
    st.warning(
        "⚠️ このランキングは過去データの統計パターンに基づく **検証用シグナル** です。"
        "「予測上昇幅」「上昇確率」は過去の類似条件における統計的期待値であり、"
        "将来の値動きを保証するものではありません。投資助言ではありません。",
        icon="⚠️",
    )

    # フィルター
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        min_prob = st.slider("上昇確率フィルター（以上）", 40, 75, 50, step=5, format="%d%%",
                             key="growth_prob_filter")
    with col_f2:
        show_n = st.slider("表示件数", 3, 14, 7, key="growth_show_n")

    sub1, sub2, sub3 = st.tabs(["🇺🇸 米国AI株", "🇯🇵 日本成長株", "🛸 IPO候補ウォッチ"])

    # ── 米国AI株 ──────────────────────────────────────────────
    with sub1:
        try:
            us_df = _load_us_scores()
            _render_ranking_section(us_df, "🇺🇸 米国AI成長株ランキング", is_jp=False,
                                    min_prob=min_prob, show_n=show_n)
        except Exception as e:
            st.error(f"米国株データの取得に失敗しました: {e}")
            st.exception(e)

    # ── 日本成長株 ────────────────────────────────────────────
    with sub2:
        st.info(
            "📌 日本株の売買タイミング：朝 **8:45〜8:55** に寄付成行買い → **14:50〜15:00** に引け成行売り\n\n"
            "⚠️ 翌日への持ち越しは禁止ではありませんが、このロジックは日計り（1日）を想定しています。"
        )
        try:
            jp_df = _load_jp_scores()
            _render_ranking_section(jp_df, "🇯🇵 日本AI・成長株ランキング", is_jp=True,
                                    min_prob=min_prob, show_n=show_n)
        except Exception as e:
            st.error(f"日本株データの取得に失敗しました: {e}")
            st.exception(e)

    # ── IPOウォッチリスト ─────────────────────────────────────
    with sub3:
        st.markdown("### 🛸 近未来のIPO候補ウォッチリスト（未上場企業）")
        st.info(
            "以下は **現在株式市場に上場していない** 企業です。"
            "現時点ではNISAを含むいかなる証券口座でも購入できません。"
            "上場後の参考情報としてご覧ください。"
        )
        for ipo in IPO_WATCHLIST:
            heat_str = "🔥" * ipo["heat"] + "　" * (5 - ipo["heat"])
            st.markdown(f"""
            <div style="background:#1a1a2e;border-left:6px solid #ff9900;
                        padding:16px 20px;border-radius:10px;margin-bottom:12px;">
              <div style="font-size:1.3rem;font-weight:900;">
                🛸 {ipo['name']}
                <span style="color:#aaa;font-size:0.9rem;">（{ipo['symbol']}）</span>
              </div>
              <div style="margin:6px 0;">
                <b>上場観測度：</b>{heat_str}
                &nbsp;&nbsp;<b>カテゴリ：</b>{ipo['category']}
              </div>
              <div style="margin:4px 0;"><b>想定時価総額：</b>{ipo['valuation']}</div>
              <hr style="border-color:#333;margin:8px 0">
              <div style="color:#ccc;margin-bottom:6px;">📰 {ipo['summary']}</div>
              <div style="color:#aaa;font-size:0.85rem;">
                🇯🇵 日本人投資家向け：{ipo['jp_note']}
              </div>
              <div style="color:#ff6666;font-size:0.85rem;margin-top:4px;">
                ⚠️ リスク：{ipo['risk']}
              </div>
            </div>
            """, unsafe_allow_html=True)
