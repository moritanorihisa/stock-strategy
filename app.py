"""
Streamlitアプリ（初心者向けUI版）
日米業種リードラグ投資戦略 研究・検証ツール

注意: 研究・検証目的専用。発注機能なし。投資助言ではありません。
"""

import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from auth import login_wall, logout_button
from growth.growth_ui import render_growth_tab
from dashboard.dashboard_ui import render_dashboard_tab
from dashboard.vix_widget import render_vix_card
from dashboard.explanation import render_explanation_tab
from dashboard.sector_heatmap import render_sector_heatmap_tab
from utils.time_handler import get_analysis_label, get_display_date, is_after_market_close
from data.loader import (
    load_all,
    get_feature_columns,
    get_target_columns,
    get_latest_us_returns,
    JP_SECTOR_ETFS,
    US_SECTOR_ETFS,
)
from data.fear_greed import calculate_fear_greed_index, interpret_fear_greed
from data.news_fetcher import render_news_section, get_market_sentiment
from data.institutional_flow import analyze_institutional_sentiment, get_typical_institutional_moves
from data.short_pressure import calculate_short_pressure, get_short_squeeeze_warning
from data.earnings_calendar import render_earnings_calendar_tab, get_next_major_earnings
from models.predictor import run_prediction
from backtest.engine import run_backtest, get_today_signals
from backtest.accuracy_tracker import calculate_accuracy_metrics, get_recent_accuracy, get_sector_accuracy

# =============================================
# 証券コード → 初心者向け日本語表記マッピング
# =============================================
JP_DISPLAY_NAMES = {
    "1615.T": {"code": "1615", "name": "NF・TOPIX-17 銀行業",         "short": "銀行業"},
    "1617.T": {"code": "1617", "name": "NF・TOPIX-17 食品",           "short": "食品"},
    "1618.T": {"code": "1618", "name": "NF・TOPIX-17 エネルギー資源", "short": "エネルギー"},
    "1619.T": {"code": "1619", "name": "NF・TOPIX-17 建設・資材",     "short": "建設・資材"},
    "1620.T": {"code": "1620", "name": "NF・TOPIX-17 素材・化学",     "short": "素材・化学"},
    "1621.T": {"code": "1621", "name": "NF・TOPIX-17 医薬品",         "short": "医薬品"},
    "1622.T": {"code": "1622", "name": "NF・TOPIX-17 自動車・輸送機", "short": "自動車"},
    "1623.T": {"code": "1623", "name": "NF・TOPIX-17 鉄鋼・非鉄",    "short": "鉄鋼・非鉄"},
    "1624.T": {"code": "1624", "name": "NF・TOPIX-17 機械",           "short": "機械"},
    "1625.T": {"code": "1625", "name": "NF・TOPIX-17 電機・精密",     "short": "電機・精密"},
    "1626.T": {"code": "1626", "name": "NF・TOPIX-17 情報通信",       "short": "情報通信"},
    "1627.T": {"code": "1627", "name": "NF・TOPIX-17 電力・ガス",     "short": "電力・ガス"},
    "1628.T": {"code": "1628", "name": "NF・TOPIX-17 不動産",         "short": "不動産"},
    "1629.T": {"code": "1629", "name": "NF・TOPIX-17 小売業",         "short": "小売業"},
    "1630.T": {"code": "1630", "name": "NF・TOPIX-17 運輸・物流",     "short": "運輸・物流"},
    "1631.T": {"code": "1631", "name": "NF・TOPIX-17 金融（除く銀行）","short": "金融"},
}

def ticker_to_display(col: str) -> dict:
    """JP_xxxx.T_intraday → 表示用辞書に変換"""
    ticker = col.replace("JP_", "").replace("_intraday", "")
    return JP_DISPLAY_NAMES.get(ticker, {"code": ticker, "name": ticker, "short": ticker})


# =============================================
# ページ設定
# =============================================
st.set_page_config(
    page_title="日米業種リードラグ戦略",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# カスタムCSS（スマホ最適化・カード型デザイン）
st.markdown("""
<style>
  .big-code { font-size: 2.4rem; font-weight: 900; line-height: 1.1; }
  .sector-name { font-size: 1.0rem; color: #aaa; }
  .card-buy  { background:#0d3b2e; border-left:6px solid #00cc88; padding:16px 20px; border-radius:10px; margin-bottom:10px; }
  .card-sell { background:#3b0d0d; border-left:6px solid #ff4444; padding:16px 20px; border-radius:10px; margin-bottom:10px; }
  .card-info { background:#1a1a2e; border-left:6px solid #4488ff; padding:16px 20px; border-radius:10px; margin-bottom:10px; }
  .footer    { position:fixed; bottom:0; left:0; right:0; background:#111; color:#666; text-align:center; font-size:0.75rem; padding:6px; z-index:999; }
  @media(max-width:600px){ .big-code { font-size:1.8rem; } }
</style>
<div class="footer">⚠️ 本ツールは研究・検証目的専用です。投資助言ではありません。売買はご自身の判断と責任で行ってください。</div>
""", unsafe_allow_html=True)

# =============================================
# 認証
# =============================================
if not login_wall():
    st.stop()
logout_button()

# ログイン直後の自動分析実行フラグ
if "auto_analyzed" not in st.session_state:
    st.session_state.auto_analyzed = False

# =============================================
# サイドバー
# =============================================
with st.sidebar:
    st.header("⚙️ 設定")
    start_date   = st.date_input("開始日", value=datetime(2018, 1, 1))
    end_date     = st.date_input("終了日", value=datetime.today())
    model_name   = st.selectbox("モデル", ["pca","linear"],
                     format_func=lambda x: {"pca":"PCA+Ridge（推奨）","linear":"単純線形回帰"}.get(x,x))
    window       = st.slider("学習ウィンドウ（営業日）", 60, 504, 252, step=21)
    n_components = st.slider("PCA主成分数", 2, 10, 5) if model_name=="pca" else 5
    alpha        = st.number_input("Ridge alpha", 0.01, 100.0, 1.0, step=0.1)
    st.divider()
    n_long       = st.slider("ロング業種数", 1, 6, 3)
    allow_short  = st.toggle("ショートを許可", value=False)
    n_short      = st.slider("ショート業種数", 1, 6, 3) if allow_short else 0
    fee_rate     = st.number_input("手数料率 (%)", 0.0, 1.0, 0.1, step=0.01) / 100
    slippage     = st.number_input("スリッページ (%)", 0.0, 1.0, 0.1, step=0.01) / 100
    run_btn      = st.button("▶ 分析実行", type="primary", use_container_width=True)

# =============================================
# キャッシュ付き処理
# =============================================
@st.cache_data(ttl=3600, show_spinner="データ取得中...")
def cached_load(start, end):
    return load_all(start_date=start, end_date=end)

@st.cache_data(ttl=3600, show_spinner="予測モデル実行中...")
def cached_predict(start, end, model, win, n_comp, alp):
    df        = cached_load(start, end)
    feat_cols = get_feature_columns(df)
    tgt_cols  = get_target_columns(df)
    preds     = run_prediction(df, feat_cols, tgt_cols, model, win, n_comp, alp)
    return df, preds, feat_cols, tgt_cols

# =============================================
# メイン
# =============================================
st.title(f"📊 {get_analysis_label()}")
st.caption("参考: 中川慧ら「部分空間正則化付き主成分分析を用いた日米業種リードラグ投資戦略」（人工知能学会 FIN-036, 2026）")

# マーケット指標表示（常に表示）
st.divider()
col_vix, col_fg = st.columns(2)

with col_vix:
    render_vix_card()

with col_fg:
    st.markdown("### 😨/😊 Fear & Greed Index")
    fg = calculate_fear_greed_index()
    st.markdown(f"""
    <div style="background:#1a1a2e; padding:20px; border-radius:10px; border-left:6px solid {fg['color']};">
    <h1 style="color:{fg['color']};margin:0;">{fg['score']}</h1>
    <p style="color:#aaa;margin:5px 0;">{fg['label']}</p>
    <small>{interpret_fear_greed(fg['score'])}</small>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# 自動実行フラグまたはボタンクリック時に実行
if run_btn:
    st.session_state.auto_analyzed = True

if st.session_state.auto_analyzed:
    with st.spinner("分析中..."):
        try:
            df, predictions, feat_cols, tgt_cols = cached_predict(
                str(start_date), str(end_date), model_name, window, n_components, alpha)
            actual_returns = df[tgt_cols]
            bt = run_backtest(predictions, actual_returns,
                              n_long=n_long, n_short=n_short, allow_short=allow_short,
                              fee_rate=fee_rate, slippage_rate=slippage)

            tab0, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
                ["🏠 ダッシュボード", "📅 今日の売買", "📈 バックテスト成績",
                 "📖 戦略説明", "💡 初心者向け解説", "✅ 精度検証",
                 "🔥 セクターヒートマップ", "⚠️ 注意事項", "🚀 AI成長株・日本株予測"])

            # =========================================================
            # タブ0：総合ダッシュボード
            # =========================================================
            with tab0:
                render_dashboard_tab()

            # =========================================================
            # タブ1：今日の売買（初心者向け）
            # =========================================================
            with tab1:

                # --- 翌営業日の予測（最新米国データを使ってリアルタイム予測）---
                st.subheader("🔮 翌営業日の予測シグナル（最新データ）")
                try:
                    x_next_series, us_date = get_latest_us_returns()

                    # 予測モデルを再構築して翌日を予測
                    from models.predictor import PCAPredictor, SimpleLinearPredictor
                    if model_name == "pca":
                        predictor_obj = PCAPredictor(window=window, n_components=n_components, alpha=alpha)
                    else:
                        predictor_obj = SimpleLinearPredictor(window=window, alpha=alpha)

                    X_all = df[feat_cols]
                    Y_all = df[tgt_cols]

                    # 特徴量の列順を学習データに合わせる
                    x_next_aligned = x_next_series.reindex(feat_cols).fillna(0).values
                    next_pred_arr   = predictor_obj.predict_next_day(X_all, Y_all, x_next_aligned)
                    next_pred       = pd.Series(next_pred_arr, index=tgt_cols)

                    next_scores      = next_pred.sort_values(ascending=False)
                    next_buy_cols    = next_scores.iloc[:n_long].index.tolist()
                    next_sell_cols   = next_scores.iloc[-n_short:].index.tolist() if allow_short else []

                    # 翌営業日の日付を計算
                    from pandas.tseries.offsets import BDay
                    next_jp_date = (pd.Timestamp.today() + BDay(1)).strftime("%Y年%m月%d日")

                    st.success(f"**{next_jp_date}（翌営業日）の推奨アクション**　※米国 {us_date} 終値データをもとに予測")

                    next_cols_layout = st.columns(min(n_long, 3))
                    for i, col in enumerate(next_buy_cols):
                        info     = ticker_to_display(col)
                        score    = next_scores[col]
                        past_rets = actual_returns[col][actual_returns[col] > 0]
                        exp_val  = past_rets.mean() * 100 if len(past_rets) > 0 else 0
                        win_rate = (actual_returns[col] > 0).mean() * 100
                        with next_cols_layout[i % len(next_cols_layout)]:
                            st.markdown(f"""
                            <div class="card-buy">
                              <div class="big-code">🟢 {info['code']}</div>
                              <div class="sector-name">{info['name']}</div>
                              <hr style="border-color:#1a5c42;margin:8px 0">
                              <b>予測スコア:</b> {score:.4f}<br>
                              <b>過去平均期待値:</b> +{exp_val:.2f}%（保証ではありません）<br>
                              <b>過去勝率:</b> {win_rate:.1f}%
                            </div>
                            """, unsafe_allow_html=True)

                    # 今日やることリスト（翌営業日版）
                    st.markdown(f"#### ✅ {next_jp_date} にやること")
                    for i, col in enumerate(next_buy_cols, 1):
                        info = ticker_to_display(col)
                        st.markdown(f"""
                        <div class="card-info">
                          <b>買い {i}：{info['code']} {info['short']}</b><br>
                          ① SBI証券アプリを開く<br>
                          ② 銘柄コード「<b>{info['code']}</b>」を検索<br>
                          ③ 朝 8:45〜8:55 に「<b>寄付成行</b>」で注文<br>
                          ④ 14:50〜15:00 に「<b>引け成行</b>」で全売却
                        </div>
                        """, unsafe_allow_html=True)

                    # CSV出力（翌日版）
                    next_csv_rows = []
                    for col in next_buy_cols:
                        info = ticker_to_display(col)
                        next_csv_rows.append({"対象日":next_jp_date,"方向":"買い","証券コード":info["code"],
                                              "銘柄名":info["name"],"注文種別":"寄付成行",
                                              "買いタイミング":"8:45〜8:55","売りタイミング":"14:50〜15:00"})
                    if next_csv_rows:
                        next_csv = pd.DataFrame(next_csv_rows).to_csv(index=False).encode("utf-8-sig")
                        st.download_button("📥 翌営業日の注文メモCSV", data=next_csv,
                                           file_name=f"signal_next.csv", mime="text/csv")

                except Exception as e:
                    st.warning(f"翌営業日の予測取得に失敗しました: {e}\n\n米国市場が閉まっていない時間帯は予測できません。")

                st.divider()

                # --- 以下は過去の最終データ日のシグナル（参考表示）---
                latest_pred = predictions.iloc[-1]
                signal_date = predictions.index[-1].strftime("%Y年%m月%d日")
                st.caption(f"※ 以下は過去データ最終日（{signal_date}）のシグナル（参考）")
                scores      = latest_pred.sort_values(ascending=False)

                buy_cols  = scores.iloc[:n_long].index.tolist()
                sell_cols = scores.iloc[-n_short:].index.tolist() if allow_short else []

                # --- 今日やること ---
                st.subheader(f"📋 {signal_date} の推奨アクション")
                st.info("注文はSBI証券などで **手動発注** してください。このツールは発注しません。")

                # 売買ガイド
                with st.expander("🕐 売買タイミングガイド（初めての方はここを確認）", expanded=True):
                    col_g1, col_g2, col_g3 = st.columns(3)
                    with col_g1:
                        st.success("**【買いタイミング】**\n\n朝 **8:45〜8:55** の間に\n「**寄付成行**（よりつきなりゆき）」で注文")
                    with col_g2:
                        st.error("**【売りタイミング】**\n\n**14:50〜15:00** の間に\n「**引け成行**（ひけなりゆき）」ですべて売却")
                    with col_g3:
                        st.warning("**【絶対NG】**\n\n翌日への **持ち越し禁止**\n当日中に必ず決済してください")

                st.divider()

                # 買い候補カード
                st.markdown("### 🟢 買い候補（寄付き9:00に買い→引け15:00に売り）")
                buy_cols_layout = st.columns(min(n_long, 3))
                for i, col in enumerate(buy_cols):
                    info    = ticker_to_display(col)
                    score   = scores[col]
                    # 過去の同方向リターン平均を期待値として表示
                    past_rets = actual_returns[col][actual_returns[col] > 0]
                    exp_val   = past_rets.mean() * 100 if len(past_rets) > 0 else 0
                    win_rate  = (actual_returns[col] > 0).mean() * 100

                    with buy_cols_layout[i % len(buy_cols_layout)]:
                        st.markdown(f"""
                        <div class="card-buy">
                          <div class="big-code">🟢 {info['code']}</div>
                          <div class="sector-name">{info['name']}</div>
                          <hr style="border-color:#1a5c42;margin:8px 0">
                          <b>予測スコア:</b> {score:.4f}<br>
                          <b>過去平均期待値:</b> +{exp_val:.2f}%（保証ではありません）<br>
                          <b>過去勝率:</b> {win_rate:.1f}%
                        </div>
                        """, unsafe_allow_html=True)

                if allow_short and sell_cols:
                    st.divider()
                    st.markdown("### 🔴 売り候補（空売り）")
                    sell_cols_layout = st.columns(min(n_short, 3))
                    for i, col in enumerate(sell_cols):
                        info  = ticker_to_display(col)
                        score = scores[col]
                        with sell_cols_layout[i % len(sell_cols_layout)]:
                            st.markdown(f"""
                            <div class="card-sell">
                              <div class="big-code">🔴 {info['code']}</div>
                              <div class="sector-name">{info['name']}</div>
                              <hr style="border-color:#5c1a1a;margin:8px 0">
                              <b>予測スコア:</b> {score:.4f}
                            </div>
                            """, unsafe_allow_html=True)

                st.divider()

                # 今日やることリスト
                st.markdown("### ✅ 今日やること（ステップ順）")
                for i, col in enumerate(buy_cols, 1):
                    info = ticker_to_display(col)
                    st.markdown(f"""
                    <div class="card-info">
                      <b>買い {i}：{info['code']} {info['short']}</b><br>
                      ① SBI証券アプリを開く<br>
                      ② 銘柄コード「<b>{info['code']}</b>」を検索<br>
                      ③ 朝 8:45〜8:55 に「<b>寄付成行</b>」で注文<br>
                      ④ 14:50〜15:00 に「<b>引け成行</b>」で全売却
                    </div>
                    """, unsafe_allow_html=True)

                st.divider()

                # 全業種スコアバーグラフ
                st.markdown("### 📊 全業種の予測スコア（高いほど買い有力）")
                score_df = pd.DataFrame({
                    "証券コード・業種": [f"{ticker_to_display(c)['code']} {ticker_to_display(c)['short']}" for c in scores.index],
                    "予測スコア":       scores.values,
                }).sort_values("予測スコア")

                fig = px.bar(score_df, x="予測スコア", y="証券コード・業種", orientation="h",
                             color="予測スコア", color_continuous_scale="RdYlGn")
                fig.update_layout(height=500, margin=dict(l=0,r=0,t=30,b=0))
                st.plotly_chart(fig, use_container_width=True)

                # CSV出力
                csv_rows = []
                for col in buy_cols:
                    info = ticker_to_display(col)
                    csv_rows.append({"方向":"買い","証券コード":info["code"],"銘柄名":info["name"],
                                     "注文種別":"寄付成行","買いタイミング":"8:45〜8:55","売りタイミング":"14:50〜15:00"})
                for col in sell_cols:
                    info = ticker_to_display(col)
                    csv_rows.append({"方向":"売り（空売り）","証券コード":info["code"],"銘柄名":info["name"],
                                     "注文種別":"寄付成行","買いタイミング":"8:45〜8:55","売りタイミング":"14:50〜15:00"})
                if csv_rows:
                    csv_df    = pd.DataFrame(csv_rows)
                    csv_bytes = csv_df.to_csv(index=False).encode("utf-8-sig")
                    st.download_button("📥 注文メモCSVをダウンロード", data=csv_bytes,
                                       file_name=f"order_{predictions.index[-1].strftime('%Y%m%d')}.csv",
                                       mime="text/csv")

            # =========================================================
            # タブ2：バックテスト成績
            # =========================================================
            with tab2:
                m = bt["metrics"]
                st.subheader("📈 バックテスト成績（過去の結果。将来を保証しません）")

                c1,c2,c3,c4 = st.columns(4)
                c1.metric("年率リターン（過去平均）", f"{m['年率リターン (%)']:.1f}%", help="過去バックテストの結果です")
                c2.metric("シャープレシオ",           f"{m['シャープレシオ']:.2f}")
                c3.metric("最大ドローダウン",         f"{m['最大ドローダウン (%)']:.1f}%")
                c4.metric("勝率",                     f"{m['勝率 (%)']:.1f}%")

                st.caption(f"総リターン {m['総リターン (%)']:.1f}% | 取引日数 {m['取引日数']} 日 | 手数料{fee_rate*100:.2f}%+スリッページ{slippage*100:.2f}%（片道）")
                st.warning("⚠️ これは過去データのシミュレーション結果です。将来の利益を保証するものではありません。")

                # 累積リターングラフ
                cum   = bt["cum_returns"]
                bench = (1 + actual_returns.loc[bt["daily_returns"].index].mean(axis=1)).cumprod() - 1
                fig2  = go.Figure()
                fig2.add_trace(go.Scatter(x=cum.index, y=cum.values*100, name="この戦略", line=dict(color="#00cc88",width=2)))
                fig2.add_trace(go.Scatter(x=bench.index, y=bench.values*100, name="全業種均等（比較）", line=dict(color="#aaa",width=1,dash="dot")))
                fig2.update_layout(title="資産推移（累積リターン）", xaxis_title="日付", yaxis_title="累積リターン (%)", hovermode="x unified")
                st.plotly_chart(fig2, use_container_width=True)

                # ドローダウン
                cv  = (1 + bt["daily_returns"]).cumprod()
                dd  = (cv - cv.cummax()) / cv.cummax() * 100
                fig3 = go.Figure(go.Scatter(x=dd.index, y=dd.values, fill="tozeroy", line=dict(color="#ff4444"), name="ドローダウン"))
                fig3.update_layout(title="ドローダウン（最大損失の推移）", xaxis_title="日付", yaxis_title="%")
                st.plotly_chart(fig3, use_container_width=True)

                # 月次ヒートマップ
                monthly = bt["daily_returns"].resample("ME").apply(lambda x: (1+x).prod()-1) * 100
                pivot   = pd.DataFrame({"Y":monthly.index.year,"M":monthly.index.month,"R":monthly.values})
                pivot   = pivot.pivot(index="Y", columns="M", values="R")
                pivot.columns = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
                fig4 = px.imshow(pivot, color_continuous_scale="RdYlGn", color_continuous_midpoint=0,
                                 text_auto=".1f", title="月次リターン ヒートマップ（%）")
                st.plotly_chart(fig4, use_container_width=True)

            # =========================================================
            # タブ3：戦略説明
            # =========================================================
            with tab3:
                st.subheader("📖 この戦略の仕組み（初心者向け解説）")
                st.markdown("""
                ### なぜこの戦略が機能するのか？

                **ニューヨーク市場は東京市場より約14時間早く動きます。**

                例えば、NY時間の夜（日本時間の早朝）にエネルギー株が大きく上がると、
                その日の東京市場でもエネルギー関連ETFが上がる傾向があります。
                これを「**リードラグ効果**（時差を使った先行指標）」と呼びます。

                ---

                ### 売買の流れ

                | ステップ | 時間 | 内容 |
                |---------|------|------|
                | ① NY市場の分析 | 深夜〜朝6時 | 前日のNY市場が閉まり、このツールが自動で分析 |
                | ② シグナル確認 | 朝8:45まで | このアプリを開いて「今日の買い候補」を確認 |
                | ③ 買い注文 | 8:45〜8:55 | SBI証券アプリで「寄付成行」注文 |
                | ④ 売り注文 | 14:50〜15:00 | 「引け成行」で全売却 |

                ---

                ### 対象銘柄について

                個別株（トヨタ、ソニーなど）ではなく、**業種別ETF**を売買します。

                | 証券コード | 銘柄名 | 説明 |
                |-----------|--------|------|
                | 1617 | NF・TOPIX-17 食品 | 食品業界全体に投資するETF |
                | 1618 | NF・TOPIX-17 エネルギー | エネルギー業界全体 |
                | 1625 | NF・TOPIX-17 電機・精密 | 電機・精密業界全体 |
                | ...  | （以下同様）| |

                ETFは個別株より値動きが安定しており、初心者向きです。

                ---

                ### 参考文献

                中川慧・竹本悠城・久保健治・加藤真大
                「部分空間正則化付き主成分分析を用いた日米業種リードラグ投資戦略」
                人工知能学会第二種研究会資料 2026 FIN-036、p.76-83
                """)

            # =========================================================
            # タブ4：注意事項
            # =========================================================
            with tab4:
                # 初心者向け解説タブ
                if 'predictions' in locals() and 'feat_cols' in locals():
                    render_explanation_tab(predictions, predictions.iloc[-1])
                else:
                    st.info("先に「▶ 分析実行」をしてください。")

            # =========================================================
            # タブ5：予測精度検証
            # =========================================================
            with tab5:
                st.subheader("✅ 予測精度検証")
                st.info("このモデルがどのくらい正確に予測できているかを検証します。")

                # 全体的なメトリクス
                metrics = calculate_accuracy_metrics(predictions, actual_returns)
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("方向性的中率", f"{metrics['directional_accuracy']:.1f}%")
                col2.metric("相関係数", f"{metrics['correlation']:.3f}")
                col3.metric("トップ3的中率", f"{metrics['hit_rate_top3']:.1f}%")
                col4.metric("平均誤差", f"{metrics['mean_absolute_error']:.3f}")

                st.divider()

                # 最近N日間の精度テーブル
                st.markdown("### 📊 最近20日間の的中記録")
                recent_acc = get_recent_accuracy(predictions, actual_returns, days=20)
                st.dataframe(recent_acc, use_container_width=True, hide_index=True)

                st.divider()

                # セクター別精度
                st.markdown("### 🎯 セクター別的中率ランキング")
                sector_acc = get_sector_accuracy(predictions, actual_returns)
                st.dataframe(sector_acc, use_container_width=True, hide_index=True)

                with st.expander("📚 精度指標の説明"):
                    st.markdown("""
                    **方向性的中率**
                    - 予測が上昇/下落の方向性を正しく予測できた割合
                    - 50%以上なら、ランダムより優れている

                    **相関係数**
                    - 予測スコアと実際のリターンの相関
                    - 1.0に近いほど完璧、0は関係なし、-1は逆相関

                    **トップ3的中率**
                    - 予測トップ3に選んだ銘柄が、実際のトップ3に含まれた割合
                    - このモデルの最重要指標

                    **平均誤差**
                    - 予測値と実際の値の平均的なズレ
                    - 小さいほど良い
                    """)

            # =========================================================
            # タブ6：セクターヒートマップ
            # =========================================================
            with tab6:
                render_sector_heatmap_tab(predictions)

            with tab7:
                st.subheader("⚠️ 必ずお読みください")
                st.error("""
                ### 重要な注意事項

                **本ツールは研究・検証目的専用です。投資助言ではありません。**

                - ✅ 過去のバックテストで良い結果が出ていても、**将来の利益を保証しません**
                - ✅ 相場急変時（リーマンショック・コロナショック等）は大きな損失が出る可能性があります
                - ✅ ETFにも**流動性リスク**があります（板が薄く希望価格で売買できないことがあります）
                - ✅ 空売りには**追加コスト**（貸株料等）がかかります
                - ✅ **税金**はバックテスト結果に含まれていません
                - ✅ 売買はすべて**ご自身の判断と責任**で行ってください
                """)

                st.warning("""
                ### 初心者が特に注意すべきこと

                | NG行動 | 理由 |
                |--------|------|
                | 翌日への持ち越し | このロジックは日中（朝〜夕）の動きだけを予測しています |
                | 全財産を投入 | 負ける日も必ずあります。余裕資金の一部だけで試してください |
                | 毎日必ず勝てると思う | 勝率は約55〜60%です。4〜5回に1〜2回は負けます |
                | シグナルを盲信する | 予測は外れることがあります。自分でも相場を確認してください |
                """)

                st.info("""
                ### 推奨する始め方

                1. **まず1〜2ヶ月は紙取引**（実際には注文せず、メモだけして結果を記録）
                2. 紙取引で感覚をつかんだら**少額（1〜3万円程度）**で試す
                3. 安定して成績が出てから徐々に金額を増やす
                """)

            # =========================================================
            # タブ8：AI成長株スクリーナー（ETF戦略とは独立）
            # =========================================================
            with tab8:
                render_growth_tab()

        except Exception as e:
            st.error(f"エラー: {e}")
            st.exception(e)

else:
    st.info("👈 左のサイドバーでパラメータを設定し「▶ 分析実行」を押してください。")

    st.markdown("""
    ### このツールでできること

    | 機能 | 内容 |
    |------|------|
    | 📅 今日の売買 | 証券コードと売買タイミングを表示 |
    | 📈 バックテスト | 過去の成績を検証 |
    | 📖 戦略説明 | 初心者向けの仕組み解説 |
    | ⚠️ 注意事項 | リスクと正しい使い方 |

    **⚠️ 本ツールは研究・検証目的専用です。投資助言ではありません。**
    """)
