"""
総合ダッシュボード UI
アプリ最初のタブに表示する。

構成:
  1. 市場概況バー（主要指数・VIX・ドル円）
  2. 本日の注目ランキング 各カテゴリ1位カード（ミニチャート付き）
  3. 本日の市場メモ
  4. 免責事項フッター
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from dashboard.market_summary import fetch_market_overview, render_market_bar, get_market_mood
from dashboard.chart_widgets  import render_mini_chart_compact, render_mini_chart
from dashboard.link_builder   import get_links, yahoo_finance_url, yahoo_finance_jp_url, tradingview_url


# ── ダッシュボード用データ取得（各モジュールのキャッシュを活用）──

def _get_top_us(n: int = 1) -> list[dict]:
    """米国AI株スコアの上位N件を返す。"""
    try:
        from growth.growth_loader import fetch_us_price_data, calc_features
        from growth.growth_model  import calc_scores
        from growth.watchlist     import US_STOCK_INFO
        price_data = fetch_us_price_data(period="1y")
        features   = calc_features(price_data, market="US")
        df         = calc_scores(features)
        result = []
        for _, row in df.head(n).iterrows():
            info = US_STOCK_INFO.get(row["ticker"], {})
            result.append({
                "ticker":    row["ticker"],
                "name":      info.get("name", row["ticker"]),
                "category":  info.get("category", ""),
                "comment":   info.get("comment", ""),
                "score":     float(row.get("score", 0)),
                "up_prob":   float(row.get("up_prob_pct", 0)),
                "pred_ret":  float(row.get("pred_return_pct", 0)),
                "risk":      int(row.get("risk_stars", 3)),
                "nisa":      int(row.get("nisa_stars", 3)),
                "market":    "US",
            })
        return result
    except Exception as e:
        return [{"ticker": "N/A", "name": f"取得失敗: {e}", "market": "US",
                 "score":0,"up_prob":0,"pred_ret":0,"risk":3,"nisa":3,"category":"","comment":""}]


def _get_top_jp(n: int = 1) -> list[dict]:
    """日本成長株スコアの上位N件を返す。"""
    try:
        from growth.growth_loader import fetch_jp_price_data, calc_features
        from growth.growth_model  import calc_scores
        from growth.watchlist     import JP_STOCK_INFO
        price_data = fetch_jp_price_data(period="1y")
        features   = calc_features(price_data, market="JP")
        df         = calc_scores(features)
        result = []
        for _, row in df.head(n).iterrows():
            info = JP_STOCK_INFO.get(row["ticker"], {})
            result.append({
                "ticker":    row["ticker"],
                "name":      info.get("name", row["ticker"]),
                "category":  info.get("category", ""),
                "comment":   info.get("comment", ""),
                "score":     float(row.get("score", 0)),
                "up_prob":   float(row.get("up_prob_pct", 0)),
                "pred_ret":  float(row.get("pred_return_pct", 0)),
                "risk":      int(row.get("risk_stars", 3)),
                "nisa":      int(row.get("nisa_stars", 3)),
                "market":    "JP",
            })
        return result
    except Exception as e:
        return [{"ticker": "N/A", "name": f"取得失敗: {e}", "market": "JP",
                 "score":0,"up_prob":0,"pred_ret":0,"risk":3,"nisa":3,"category":"","comment":""}]


# ── カードUI部品 ──────────────────────────────────────────────

def _stars(n: int, max_n: int = 5) -> str:
    n = max(0, min(max_n, n))
    return "★" * n + "☆" * (max_n - n)


def _render_top_card(item: dict, rank_label: str, tab_hint: str) -> None:
    """
    1銘柄のダッシュボードカード（ミニチャート付き）を描画する。

    Parameters
    ----------
    item      : 銘柄データ辞書
    rank_label: 「🥇 米国AI株 1位」などのラベル
    tab_hint  : 詳細タブへの案内文
    """
    ticker   = item["ticker"]
    name     = item["name"]
    category = item["category"]
    comment  = item["comment"]
    score    = item["score"]
    up_prob  = item["up_prob"]
    pred_ret = item["pred_ret"]
    risk     = item["risk"]
    nisa     = item["nisa"]
    is_jp    = item["market"] == "JP"

    pred_color = "#00cc88" if pred_ret >= 0 else "#ff4444"
    sign       = "+" if pred_ret >= 0 else ""

    # ── カード上部：テキスト情報 ──
    col_info, col_chart = st.columns([3, 2])

    with col_info:
        st.markdown(f"""
        <div style="background:#1a2a1a;border-left:5px solid #00cc88;
                    padding:14px 16px;border-radius:10px;height:100%;">
          <div style="font-size:0.8rem;color:#aaa;">{rank_label}</div>
          <div style="font-size:1.3rem;font-weight:900;margin:4px 0;">
            {name}（{ticker}）
          </div>
          <div style="color:#888;font-size:0.8rem;margin-bottom:8px;">📂 {category}</div>
          <hr style="border-color:#333;margin:6px 0">
          <table style="width:100%;border-collapse:collapse;font-size:0.88rem;">
            <tr>
              <td style="padding:2px 4px;"><b>🎯 期待スコア</b></td>
              <td style="padding:2px 4px;color:#ffd700;font-weight:900;">{score:.0f}点</td>
              <td style="padding:2px 4px;"><b>📈 予測上昇幅</b></td>
              <td style="padding:2px 4px;color:{pred_color};font-weight:bold;">
                {sign}{pred_ret:.2f}%
              </td>
            </tr>
            <tr>
              <td style="padding:2px 4px;"><b>🎲 上昇確率</b></td>
              <td style="padding:2px 4px;">{up_prob:.1f}%</td>
              <td style="padding:2px 4px;"><b>⚠️ リスク</b></td>
              <td style="padding:2px 4px;">{_stars(risk)}</td>
            </tr>
            <tr>
              <td style="padding:2px 4px;"><b>🏦 NISA向き</b></td>
              <td style="padding:2px 4px;" colspan="3">{_stars(nisa)}</td>
            </tr>
          </table>
          <hr style="border-color:#333;margin:6px 0">
          <div style="font-size:0.82rem;color:#ccc;">💬 {comment}</div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        # ミニチャート
        mini_fig, chg_30d = render_mini_chart_compact(ticker, days=30)
        chg_color = "#00cc88" if chg_30d >= 0 else "#ff4444"
        chg_sign  = "+" if chg_30d >= 0 else ""
        st.markdown(
            f'<div style="color:{chg_color};font-size:0.85rem;font-weight:bold;margin-bottom:2px;">'
            f'直近30日: {chg_sign}{chg_30d:.1f}%</div>',
            unsafe_allow_html=True,
        )
        st.plotly_chart(mini_fig, use_container_width=True, config={"displayModeBar": False})

        # 外部リンク
        links = get_links(ticker)
        for label, url in links.items():
            st.markdown(f"[🔗 {label}]({url})")

    # 詳細チャート展開
    with st.expander(f"📊 {name} の詳細チャートを見る（60日）"):
        render_mini_chart(ticker, name, days=60)
        st.caption(f"👉 詳細分析は「{tab_hint}」タブで確認できます")


# ── メイン描画関数 ────────────────────────────────────────────

def render_dashboard_tab() -> None:
    """総合ダッシュボードタブの全コンテンツを描画する。"""

    today = datetime.today().strftime("%Y年%m月%d日")
    st.subheader(f"🏠 総合ダッシュボード　{today}")
    st.caption("各カテゴリの上位1位を一覧表示しています。詳細は各タブをご確認ください。")

    # ── 市場概況バー ──────────────────────────────────────────
    with st.container():
        st.markdown("#### 📡 本日の市場概況")
        with st.spinner("市場データを取得中..."):
            market_df = fetch_market_overview()
        render_market_bar(market_df)
        mood_label, mood_color = get_market_mood(market_df)
        st.markdown(
            f'<div style="background:#1a1a2e;border-left:5px solid {mood_color};'
            f'padding:10px 16px;border-radius:8px;margin:8px 0;">'
            f'<b>本日の市場メモ：</b> {mood_label}　'
            f'<span style="color:#888;font-size:0.85rem;">'
            f'（VIX・S&P500の前日比から自動判定。参考情報です）</span></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # ── 注目ランキング 各1位カード ────────────────────────────
    st.markdown("#### 🏆 本日の注目銘柄 各カテゴリ1位")
    st.warning(
        "予測値は過去データに基づく機械的な参考情報です。投資助言ではありません。",
        icon="⚠️",
    )

    with st.spinner("ランキングデータを計算中..."):
        top_us = _get_top_us(n=1)
        top_jp = _get_top_jp(n=1)

    # 米国AI株1位
    st.markdown("---")
    st.markdown("##### 🇺🇸 米国AI株 上昇期待1位")
    if top_us:
        _render_top_card(top_us[0], "🥇 米国AI株 上昇期待1位", "🚀 AI成長株・日本株予測")

    # 日本株1位
    st.markdown("---")
    st.markdown("##### 🇯🇵 日本成長株 上昇期待1位")
    if top_jp:
        _render_top_card(top_jp[0], "🥇 日本成長株 上昇期待1位", "🚀 AI成長株・日本株予測")

    st.divider()

    # ── フッター免責事項 ──────────────────────────────────────
    st.info(
        "📌 **本ツールは研究・検証用であり、投資助言ではありません。**\n\n"
        "予測値は過去データに基づく機械的な参考情報です。"
        "実際の売買はご自身の判断と責任で行ってください。"
        "過去の実績は将来の結果を保証するものではありません。"
    )
