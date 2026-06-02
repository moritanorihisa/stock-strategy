"""
VIX指数ウィジェット
ダッシュボードに恐怖指数を表示。
"""

import streamlit as st
from data.market_indicators import get_vix, get_market_temp


def render_vix_card() -> None:
    """
    VIX指数をカード形式で表示。
    """
    vix_data = get_vix()

    # 色付きメトリクス表示
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "⚠️ VIX（恐怖指数）",
            f"{vix_data['value']:.1f}",
            f"{vix_data['change_pct']:+.1f}%",
            delta_color="inverse",  # VIXは高いほど悪いので逆表示
        )

    with col2:
        st.markdown(f"""
        <div style="background:#1a1a2e; padding:16px; border-radius:8px; border-left:6px solid {vix_data['color']};">
        <small style="color:#aaa;">市場の温度</small><br>
        <strong style="color:{vix_data['color']};">{vix_data['status']}</strong>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
        <div style="background:#1a1a2e; padding:16px; border-radius:8px; border-left:6px solid #4488ff;">
        <small style="color:#aaa;">全体の雰囲気</small><br>
        <strong>{get_market_temp()}</strong>
        </div>
        """, unsafe_allow_html=True)

    # 詳細説明
    with st.expander("📚 VIX指数とは？"):
        st.markdown("""
        **VIX（Volatility Index）** は「恐怖指数」と呼ばれる市場ボラティリティ（変動性）の指標です。

        - **VIX < 15**: 市場は非常に楽観的。リスク資産が買われやすい。
        - **VIX 15-20**: 市場は安定。通常の投資環境。
        - **VIX 20-30**: 市場は注意深い。やや不安定。
        - **VIX > 30**: 市場は恐怖。大きな下落や不安定さが予想される。

        💡 **投資家向けヒント**: VIXが低い時は成長銘柄が買われやすく、高い時は防御銘柄（食品・医薬品など）が買われやすい傾向があります。
        """)
