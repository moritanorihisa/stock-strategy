"""
Streamlitアプリ（知人限定公開版）
日米業種リードラグ投資戦略 研究・検証ツール

注意: 研究・検証目的専用。発注機能なし。
"""

import io
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

from auth import login_wall, logout_button
from data.loader import (
    load_all,
    get_feature_columns,
    get_target_columns,
    JP_SECTOR_ETFS,
    US_SECTOR_ETFS,
)
from models.predictor import run_prediction
from backtest.engine import run_backtest, get_today_signals

# ---- ページ設定（最初に呼ぶ必要あり）----
st.set_page_config(
    page_title="日米業種リードラグ戦略",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 認証ウォール ----
if not login_wall():
    st.stop()  # ログインしていなければここで止まる

# ---- ログアウトボタン ----
logout_button()

# ---- ヘッダー ----
st.title("📊 日米業種リードラグ戦略 研究ツール")
st.caption(
    "参考: 中川慧ら「部分空間正則化付き主成分分析を用いた日米業種リードラグ投資戦略」"
    "（人工知能学会 FIN-036, 2026）"
)
st.warning("⚠️ 研究・検証目的専用。投資助言ではありません。発注機能はありません。", icon="⚠️")

# ---- サイドバー ----
with st.sidebar:
    st.header("⚙️ パラメータ設定")

    st.subheader("データ期間")
    start_date = st.date_input("開始日", value=datetime(2018, 1, 1))
    end_date   = st.date_input("終了日", value=datetime.today())

    st.subheader("予測モデル")
    model_name = st.selectbox(
        "モデル",
        ["pca", "linear"],
        format_func=lambda x: {"pca": "PCA + Ridge（推奨）", "linear": "単純線形回帰"}.get(x, x),
    )
    window = st.slider("学習ウィンドウ（営業日）", 60, 504, 252, step=21)
    n_components = st.slider("PCA主成分数", 2, 10, 5) if model_name == "pca" else 5
    alpha = st.number_input("Ridge 正則化 alpha", 0.01, 100.0, 1.0, step=0.1)

    st.subheader("バックテスト設定")
    n_long      = st.slider("ロング業種数", 1, 6, 3)
    allow_short = st.toggle("ショートを許可", value=False)
    n_short     = st.slider("ショート業種数", 1, 6, 3) if allow_short else 0
    fee_rate      = st.number_input("手数料率 (%)",      0.0, 1.0, 0.1, step=0.01) / 100
    slippage_rate = st.number_input("スリッページ率 (%)", 0.0, 1.0, 0.1, step=0.01) / 100

    run_btn = st.button("▶ 実行", type="primary", use_container_width=True)


# ---- キャッシュ付きデータ取得・予測 ----
@st.cache_data(ttl=3600, show_spinner="データをダウンロード中...")
def cached_load(start: str, end: str) -> pd.DataFrame:
    return load_all(start_date=start, end_date=end)


@st.cache_data(ttl=3600, show_spinner="予測モデルを実行中...")
def cached_predict(start: str, end: str, model: str, win: int, n_comp: int, alp: float):
    df        = cached_load(start, end)
    feat_cols = get_feature_columns(df)
    tgt_cols  = get_target_columns(df)
    preds     = run_prediction(df, feat_cols, tgt_cols, model, win, n_comp, alp)
    return df, preds, feat_cols, tgt_cols


# ---- メイン ----
if run_btn:
    with st.spinner("計算中..."):
        try:
            df, predictions, feat_cols, tgt_cols = cached_predict(
                str(start_date), str(end_date),
                model_name, window, n_components, alpha,
            )
            actual_returns = df[tgt_cols]
            bt = run_backtest(
                predictions, actual_returns,
                n_long=n_long, n_short=n_short, allow_short=allow_short,
                fee_rate=fee_rate, slippage_rate=slippage_rate,
            )

            tab1, tab2, tab3 = st.tabs(["📅 本日のシグナル", "📈 バックテスト", "🔍 データ確認"])

            # ===== タブ1: 本日のシグナル =====
            with tab1:
                st.subheader("本日の売買候補")
                st.info("注文はSBI証券等で手動発注してください（このツールに発注機能はありません）")

                latest_pred = predictions.iloc[-1]
                today_sig   = get_today_signals(
                    latest_pred, JP_SECTOR_ETFS,
                    n_long=n_long, n_short=n_short, allow_short=allow_short,
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 🟢 買い候補（寄付き買い→引け売り）")
                    st.dataframe(today_sig["buy"], use_container_width=True)
                with col2:
                    if allow_short:
                        st.markdown("### 🔴 売り候補（空売り）")
                        st.dataframe(today_sig["sell"], use_container_width=True)

                # CSV ダウンロード
                combined = pd.concat([
                    today_sig["buy"],
                    today_sig["sell"] if allow_short and not today_sig["sell"].empty else pd.DataFrame(),
                ])
                csv_bytes = combined.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "📥 注文候補CSV",
                    data=csv_bytes,
                    file_name=f"signal_{predictions.index[-1].strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                )

                # 全業種スコアバーグラフ
                score_df = pd.DataFrame({
                    "業種":     [JP_SECTOR_ETFS.get(c.replace("JP_","").replace("_intraday",""), c) for c in latest_pred.index],
                    "予測スコア": latest_pred.values,
                }).sort_values("予測スコア")

                fig = px.bar(score_df, x="予測スコア", y="業種", orientation="h",
                             color="予測スコア", color_continuous_scale="RdYlGn",
                             title=f"全業種予測スコア（{predictions.index[-1].strftime('%Y-%m-%d')}）")
                st.plotly_chart(fig, use_container_width=True)

            # ===== タブ2: バックテスト =====
            with tab2:
                m = bt["metrics"]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("年率リターン",    f"{m['年率リターン (%)']:.1f}%")
                c2.metric("シャープレシオ",   f"{m['シャープレシオ']:.2f}")
                c3.metric("最大ドローダウン", f"{m['最大ドローダウン (%)']:.1f}%")
                c4.metric("勝率",            f"{m['勝率 (%)']:.1f}%")
                st.caption(f"総リターン {m['総リターン (%)']:.1f}% | 取引日数 {m['取引日数']} 日 | 手数料{fee_rate*100:.2f}%+スリッページ{slippage_rate*100:.2f}%（片道）")

                # 累積リターン
                cum   = bt["cum_returns"]
                bench = (1 + actual_returns.loc[bt["daily_returns"].index].mean(axis=1)).cumprod() - 1
                fig2  = go.Figure()
                fig2.add_trace(go.Scatter(x=cum.index,   y=cum.values*100,   name="戦略",         line=dict(color="#00cc88", width=2)))
                fig2.add_trace(go.Scatter(x=bench.index, y=bench.values*100, name="ベンチマーク", line=dict(color="#aaaaaa", width=1, dash="dot")))
                fig2.update_layout(title="累積リターン推移", xaxis_title="日付", yaxis_title="累積リターン (%)", hovermode="x unified")
                st.plotly_chart(fig2, use_container_width=True)

                # ドローダウン
                cv  = (1 + bt["daily_returns"]).cumprod()
                dd  = (cv - cv.cummax()) / cv.cummax() * 100
                fig3 = go.Figure(go.Scatter(x=dd.index, y=dd.values, fill="tozeroy", line=dict(color="#ff4444"), name="DD"))
                fig3.update_layout(title="ドローダウン", xaxis_title="日付", yaxis_title="%")
                st.plotly_chart(fig3, use_container_width=True)

                # 月次ヒートマップ
                monthly = bt["daily_returns"].resample("ME").apply(lambda x: (1+x).prod()-1) * 100
                pivot   = pd.DataFrame({"Y": monthly.index.year, "M": monthly.index.month, "R": monthly.values})
                pivot   = pivot.pivot(index="Y", columns="M", values="R")
                pivot.columns = ["1月","2月","3月","4月","5月","6月","7月","8月","9月","10月","11月","12月"]
                fig4 = px.imshow(pivot, color_continuous_scale="RdYlGn", color_continuous_midpoint=0, text_auto=".1f", title="月次リターン (%)")
                st.plotly_chart(fig4, use_container_width=True)

            # ===== タブ3: データ確認 =====
            with tab3:
                st.write(f"行数: {len(df)}, 列数: {len(df.columns)}")
                st.dataframe(df.tail(10), use_container_width=True)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.subheader("米国ETF（特徴量）")
                    st.dataframe(pd.DataFrame.from_dict(US_SECTOR_ETFS, orient="index", columns=["業種"]), use_container_width=True)
                with col_b:
                    st.subheader("日本ETF（ターゲット）")
                    st.dataframe(pd.DataFrame.from_dict(JP_SECTOR_ETFS, orient="index", columns=["業種"]), use_container_width=True)

        except Exception as e:
            st.error(f"エラー: {e}")
            st.exception(e)

else:
    st.info("サイドバーでパラメータを設定し「▶ 実行」を押してください。")
    with st.expander("ツールの説明"):
        st.markdown("""
        **概要**: NY市場（前日終値）→ 東京市場（翌日寄付き→引け）のリードラグを予測します。

        **利用の流れ**
        1. データ期間・モデルを設定 → 「▶ 実行」
        2. 「本日のシグナル」タブで買い候補を確認
        3. SBI証券等で **手動発注**（このツールは発注しません）

        **注意**: バックテストは過去の結果であり、将来の利益を保証しません。
        """)
