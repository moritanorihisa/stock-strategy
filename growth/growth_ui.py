"""
AI成長株スクリーナー UIコンポーネント
app.py のタブから render_growth_tab() を呼び出して使う。

構成:
  サブタブ1: 🇺🇸 米国AI株（テーマ別フィルター・ソート）
  サブタブ2: 🇯🇵 日本成長株
  サブタブ3: 🛸 IPO候補ウォッチ（関連上場銘柄マップ付き）

重要:
  「推奨」「必ず買うべき」「確実に儲かる」などの断定表現は使用しない。
  すべて「参考情報」「参考配分イメージ」「過去データ上の傾向」として表示。
"""

import streamlit as st
import pandas as pd
import plotly.express as px

from growth.growth_loader import fetch_us_price_data, fetch_jp_price_data, calc_features
from growth.growth_model  import (
    calc_scores, stars, risk_label,
    buy_timing_us, buy_timing_jp,
    sell_timing_short, sell_timing_nisa, price_display,
)
from growth.watchlist    import IPO_WATCHLIST
from growth.theme_map    import (
    THEMES, TICKER_THEME_MAP, RISK_TYPE_DISPLAY,
    ALLOC_STYLE_NOTES, IPO_RELATED_STOCKS,
)


# ── キャッシュ付きデータ取得 ──────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="米国AI株データを取得中...")
def _load_us_scores() -> pd.DataFrame:
    price_data = fetch_us_price_data(period="1y")
    features   = calc_features(price_data, market="US")
    df         = calc_scores(features)
    # テーマ情報を付与
    df["risk_type"]  = df["ticker"].map(lambda t: TICKER_THEME_MAP.get(t, {}).get("risk_type", "mid"))
    df["style"]      = df["ticker"].map(lambda t: TICKER_THEME_MAP.get(t, {}).get("style", ""))
    df["alloc_note"] = df["ticker"].map(lambda t: TICKER_THEME_MAP.get(t, {}).get("alloc_note", ""))
    df["theme_ids"]  = df["ticker"].map(lambda t: TICKER_THEME_MAP.get(t, {}).get("themes", []))
    return df


@st.cache_data(ttl=3600, show_spinner="日本成長株データを取得中...")
def _load_jp_scores() -> pd.DataFrame:
    price_data = fetch_jp_price_data(period="1y")
    features   = calc_features(price_data, market="JP")
    return calc_scores(features)


# ── カードUI ─────────────────────────────────────────────────

def _alloc_badge(risk_type: str) -> str:
    """参考配分イメージのバッジHTML。"""
    d = RISK_TYPE_DISPLAY.get(risk_type, RISK_TYPE_DISPLAY["mid"])
    return (
        f'<span style="background:{d["color"]}22;border:1px solid {d["color"]};'
        f'color:{d["color"]};padding:2px 8px;border-radius:4px;font-size:0.8rem;">'
        f'{d["label"]}</span>'
    )


def _render_stock_card(rank: int, row: pd.Series, is_jp: bool = False) -> None:
    medals   = ["🥇","🥈","🥉"] + ["🏅"] * 30
    medal    = medals[rank - 1] if rank <= len(medals) else f"{rank}位"

    score      = float(row.get("score", 0))
    name       = str(row.get("name",    row["ticker"]))
    category   = str(row.get("category", ""))
    comment    = str(row.get("comment",  ""))
    nisa_s     = int(row.get("nisa_stars", 3))
    risk_s     = int(row.get("risk_stars", 3))
    up_prob    = float(row.get("up_prob_pct",    0))
    pred_ret   = float(row.get("pred_return_pct", 0))
    price      = float(row.get("current_price",   0))
    currency   = str(row.get("currency", "JPY" if is_jp else "USD"))
    ticker     = str(row["ticker"])
    risk_type  = str(row.get("risk_type", "mid"))
    style      = str(row.get("style", ""))
    alloc_note = str(row.get("alloc_note", ""))

    color        = "#0d3b2e" if pred_ret >= 0 else "#3b0d0d"
    border_color = "#00cc88" if pred_ret >= 0 else "#ff4444"
    ret_color    = "#00cc88" if pred_ret >= 0 else "#ff4444"
    ret_sign     = "+" if pred_ret >= 0 else ""

    st.markdown(f"""
    <div style="background:{color};border-left:6px solid {border_color};
                padding:16px 20px;border-radius:10px;margin-bottom:10px;">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
        <span style="font-size:1.4rem;font-weight:900;">{medal} {rank}位　{name}（{ticker}）</span>
        {_alloc_badge(risk_type)}
      </div>
      <div style="color:#aaa;font-size:0.82rem;margin:4px 0 8px;">
        📂 {category}　｜　🏷 {style}
      </div>
      <hr style="border-color:#333;margin:8px 0">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <td style="padding:4px 8px;width:50%;">
            <b>🎯 AI期待スコア</b><br>
            <span style="font-size:1.5rem;font-weight:900;color:#ffd700;">{score:.0f}点</span>
            <span style="color:#888;font-size:0.8rem;"> / 100点</span>
          </td>
          <td style="padding:4px 8px;width:50%;">
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
            <b>⚠️ リスクレベル</b><br>{stars(risk_s)} {risk_label(risk_s)}
          </td>
          <td style="padding:4px 8px;">
            <b>🏦 NISA向き度</b><br>{stars(nisa_s)}
          </td>
        </tr>
      </table>
      <hr style="border-color:#333;margin:8px 0">
      <div style="font-size:0.9rem;color:#ccc;margin-bottom:6px;">💬 {comment}</div>
      <div style="font-size:0.82rem;color:#aaa;border-top:1px solid #333;padding-top:6px;">
        📊 参考配分イメージ（断定ではありません）：{alloc_note}
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander(f"📋 {ticker} の売買タイミング・注意点"):
        c1, c2, c3 = st.columns(3)
        timing_fn = buy_timing_jp if is_jp else buy_timing_us
        with c1:
            st.success(f"**【購入タイミング（参考）】**\n\n{timing_fn(ticker)}")
        with c2:
            st.warning(f"**【売却目安（短期検証）】**\n\n{sell_timing_short()}")
        with c3:
            st.info(f"**【NISA長期の場合】**\n\n{sell_timing_nisa()}")

        # 参考配分イメージ（詳細）
        alloc_detail = ALLOC_STYLE_NOTES.get(risk_type, "")
        if alloc_detail:
            st.markdown(f"**📊 参考配分イメージ（詳細）**\n\n{alloc_detail}")
        st.caption(
            "⚠️ 過去データに基づく参考情報です。将来の値動きを保証するものではありません。"
            "実際の売買はご自身の判断で行ってください。"
        )


# ── 米国株セクション ──────────────────────────────────────────

def _render_us_section(min_prob: int, show_n: int, selected_themes: list[str], sort_key: str) -> None:
    try:
        df = _load_us_scores()
    except Exception as e:
        st.error(f"米国株データの取得に失敗しました: {e}")
        st.exception(e)
        return

    # テーマフィルター
    if selected_themes:
        mask = df["theme_ids"].apply(
            lambda ids: any(t in (ids if isinstance(ids, list) else []) for t in selected_themes)
        )
        df = df[mask]

    # 上昇確率フィルター
    df = df[df["up_prob_pct"] >= min_prob]

    # ソート
    sort_map = {
        "AI期待スコア順":   ("score",           False),
        "予測上昇幅順":     ("pred_return_pct", False),
        "上昇確率順":       ("up_prob_pct",     False),
        "NISA向き度順":     ("nisa_stars",      False),
        "リスクが低い順":   ("risk_stars",      True),
    }
    col, asc = sort_map.get(sort_key, ("score", False))
    if col in df.columns:
        df = df.sort_values(col, ascending=asc)

    df = df.head(show_n)

    if df.empty:
        st.info("条件に合う銘柄がありません。フィルターを調整してください。")
        return

    st.markdown(f"### 🇺🇸 米国AI・テーマ株ランキング（{len(df)}銘柄）")
    st.caption("※「予測上昇幅」「上昇確率」はいずれも過去データの統計的期待値です")

    for rank, (_, row) in enumerate(df.iterrows(), 1):
        _render_stock_card(rank, row, is_jp=False)

    # チャート
    col1, col2 = st.columns(2)
    with col1:
        fig1 = px.bar(
            df.sort_values("score"),
            x="score", y="ticker", orientation="h",
            color="score", color_continuous_scale="YlGn",
            title="AI期待スコア比較",
            labels={"score": "スコア", "ticker": "銘柄"},
        )
        fig1.update_layout(height=max(300, len(df)*30), margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig1, use_container_width=True)
    with col2:
        fig2 = px.scatter(
            df, x="up_prob_pct", y="pred_return_pct",
            size="score", color="risk_stars",
            color_continuous_scale="RdYlGn_r",
            hover_name="ticker", text="ticker",
            title="上昇確率 vs 予測上昇幅",
            labels={"up_prob_pct":"上昇確率(%)","pred_return_pct":"予測上昇幅(%)","risk_stars":"リスク"},
        )
        fig2.update_traces(textposition="top center")
        fig2.update_layout(height=400, margin=dict(l=0,r=0,t=40,b=0))
        st.plotly_chart(fig2, use_container_width=True)

    # CSV
    col_map = {
        "ticker":"銘柄","name":"銘柄名","category":"カテゴリ","style":"参考スタイル",
        "score":"AI期待スコア","up_prob_pct":"上昇確率(%)","pred_return_pct":"予測上昇幅(%)",
        "risk_stars":"リスク(1-5)","nisa_stars":"NISA向き(1-5)","current_price":"現在株価($)",
        "alloc_note":"参考配分イメージ",
    }
    avail     = [c for c in col_map if c in df.columns]
    csv_bytes = df[avail].rename(columns=col_map).to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 米国株ランキングCSV", data=csv_bytes,
                       file_name="us_growth_ranking.csv", mime="text/csv")


# ── 日本株セクション ──────────────────────────────────────────

def _render_jp_section(min_prob: int, show_n: int, sort_key: str) -> None:
    st.info(
        "📌 日本株の参考タイミング：朝 **8:45〜8:55** に寄付成行 → **14:50〜15:00** に引け成行\n\n"
        "⚠️ 翌日持ち越しはこのロジックの想定外です。自己判断でご利用ください。"
    )
    try:
        df = _load_jp_scores()
    except Exception as e:
        st.error(f"日本株データの取得に失敗しました: {e}")
        st.exception(e)
        return

    df = df[df["up_prob_pct"] >= min_prob]

    sort_map = {
        "AI期待スコア順":   ("score",           False),
        "予測上昇幅順":     ("pred_return_pct", False),
        "上昇確率順":       ("up_prob_pct",     False),
        "NISA向き度順":     ("nisa_stars",      False),
        "リスクが低い順":   ("risk_stars",      True),
    }
    col, asc = sort_map.get(sort_key, ("score", False))
    if col in df.columns:
        df = df.sort_values(col, ascending=asc)
    df = df.head(show_n)

    if df.empty:
        st.info("条件に合う銘柄がありません。上昇確率フィルターを下げてください。")
        return

    st.markdown(f"### 🇯🇵 日本AI・成長株ランキング（{len(df)}銘柄）")
    st.caption("※「予測上昇幅」「上昇確率」はいずれも過去データの統計的期待値です")

    for rank, (_, row) in enumerate(df.iterrows(), 1):
        _render_stock_card(rank, row, is_jp=True)

    col_map = {
        "ticker":"証券コード","name":"銘柄名","category":"カテゴリ",
        "score":"AI期待スコア","up_prob_pct":"上昇確率(%)","pred_return_pct":"予測上昇幅(%)",
        "risk_stars":"リスク(1-5)","nisa_stars":"NISA向き(1-5)","current_price":"現在株価(¥)",
    }
    avail     = [c for c in col_map if c in df.columns]
    csv_bytes = df[avail].rename(columns=col_map).to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 日本株ランキングCSV", data=csv_bytes,
                       file_name="jp_growth_ranking.csv", mime="text/csv")


# ── IPOウォッチリストセクション ───────────────────────────────

def _render_ipo_section() -> None:
    st.markdown("### 🛸 IPO候補ウォッチリスト（未上場企業）")
    st.info(
        "以下は **現在株式市場に上場していない** 企業です。\n"
        "現時点ではNISAを含むいかなる証券口座でも購入できません。\n"
        "NISA購入可否は上場後に確認が必要です。"
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
            <b>上場観測度：</b>{heat_str}　<b>カテゴリ：</b>{ipo['category']}
          </div>
          <div style="margin:4px 0;"><b>想定時価総額：</b>{ipo['valuation']}</div>
          <hr style="border-color:#333;margin:8px 0">
          <div style="color:#ccc;margin-bottom:6px;">📰 注目理由：{ipo['summary']}</div>
          <div style="color:#aaa;font-size:0.85rem;">
            🇯🇵 日本人投資家向けメモ：{ipo['jp_note']}
          </div>
          <div style="color:#ff6666;font-size:0.85rem;margin-top:4px;">
            ⚠️ リスク：{ipo['risk']}
          </div>
        </div>
        """, unsafe_allow_html=True)

        # 関連上場銘柄マップ
        related = IPO_RELATED_STOCKS.get(ipo["name"], [])
        if related:
            with st.expander(f"📎 {ipo['name']} に直接投資できない場合の関連上場銘柄（参考）"):
                st.caption("⚠️ 関連銘柄への投資は、IPO候補企業への直接投資と異なります。参考情報としてご覧ください。")
                for r in related:
                    st.markdown(
                        f"**{r['ticker']}（{r['name']}）**　— {r['reason']}"
                    )


# ── メイン描画関数 ────────────────────────────────────────────

def render_growth_tab() -> None:
    """タブ「🚀 AI成長株・日本株予測」の全コンテンツを描画する。"""

    st.subheader("🚀 AI成長株・日本株 翌日予測スクリーナー")

    # 注意ボックス（大きく表示）
    st.warning(
        "**⚠️ ご利用前に必ずお読みください**\n\n"
        "AI関連株は上昇余地が大きい一方、急落リスクも大きいです。"
        "一括全力ではなく、**分散・積立・暴落時の追加検討** が安全です。\n\n"
        "本ツールは **研究・検証用** であり、**投資助言ではありません**。"
        "「予測上昇幅」「上昇確率」はいずれも過去データの統計的期待値であり、"
        "将来の値動きを保証するものではありません。実際の売買はご自身の判断で行ってください。",
        icon="⚠️",
    )

    # 共通フィルター
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        min_prob = st.slider("上昇確率フィルター（以上）", 40, 75, 50, step=5,
                             format="%d%%", key="growth_prob")
    with col_f2:
        show_n = st.slider("表示件数", 3, 19, 8, key="growth_n")
    with col_f3:
        sort_key = st.selectbox(
            "並び替え",
            ["AI期待スコア順","予測上昇幅順","上昇確率順","NISA向き度順","リスクが低い順"],
            key="growth_sort",
        )

    sub1, sub2, sub3 = st.tabs(["🇺🇸 米国AI・テーマ株", "🇯🇵 日本成長株", "🛸 IPO候補ウォッチ"])

    with sub1:
        # テーマフィルター（米国のみ）
        st.markdown("**テーマで絞り込む（複数選択可）**")
        theme_cols = st.columns(len(THEMES))
        selected_themes: list[str] = []
        for i, (tid, tname) in enumerate(THEMES.items()):
            if theme_cols[i].checkbox(tname, key=f"theme_{tid}"):
                selected_themes.append(tid)
        _render_us_section(min_prob, show_n, selected_themes, sort_key)

    with sub2:
        _render_jp_section(min_prob, show_n, sort_key)

    with sub3:
        _render_ipo_section()

    # フッター
    st.divider()
    st.caption(
        "📌 本ツールは研究・検証用であり、投資助言ではありません。"
        "実際の売買はご自身の判断で行ってください。"
        "過去の実績は将来の結果を保証するものではありません。"
    )
