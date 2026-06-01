"""
テーマ分類マップ（米国株）

各銘柄をテーマ・リスク・参考配分タイプに分類する。
「推奨」「必ず買うべき」などの断定表現は使用しない。
表示はすべて「参考情報」「参考配分イメージ」として提示する。
"""

# ── テーマ定義 ────────────────────────────────────────────────
# key: テーマID（フィルター用）, value: 表示名
THEMES: dict[str, str] = {
    "large_ai":    "🤖 AI大型株",
    "semi":        "🔬 AI半導体",
    "ai_soft":     "💻 AIソフト",
    "infra_power": "⚡ AIインフラ・電力",
    "space":       "🚀 宇宙通信",
    "high_growth":  "📈 高リスク成長株",
    "nisa_core":   "🏦 NISA長期候補",
}

# ── 各銘柄のテーマ・リスク分類 ───────────────────────────────
# risk_type: "low" / "mid" / "high" / "very_high"
TICKER_THEME_MAP: dict[str, dict] = {
    # AI大型株
    "NVDA":  {"themes": ["large_ai", "semi", "nisa_core"],   "risk_type": "mid",
              "style": "NISA長期 / コア候補",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "MSFT":  {"themes": ["large_ai", "ai_soft", "nisa_core"],"risk_type": "low",
              "style": "NISA長期 / 安定成長",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "GOOGL": {"themes": ["large_ai", "nisa_core"],           "risk_type": "low",
              "style": "NISA長期 / コア候補",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "AMZN":  {"themes": ["large_ai", "nisa_core"],           "risk_type": "low",
              "style": "NISA長期 / コア候補",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "META":  {"themes": ["large_ai", "ai_soft"],             "risk_type": "mid",
              "style": "NISA長期 / サテライト",
              "alloc_note": "サテライト枠として少額から検討するタイプ"},
    "AMD":   {"themes": ["semi", "high_growth"],             "risk_type": "mid",
              "style": "サテライト / 成長枠",
              "alloc_note": "サテライト枠として少額から検討するタイプ"},
    "TSM":   {"themes": ["semi", "nisa_core"],               "risk_type": "mid",
              "style": "NISA長期 / 半導体コア",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "AVGO":  {"themes": ["semi", "infra_power", "nisa_core"],"risk_type": "mid",
              "style": "NISA長期 / インフラ",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "ORCL":  {"themes": ["ai_soft", "nisa_core"],            "risk_type": "low",
              "style": "NISA長期 / クラウドDB",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "CRWD":  {"themes": ["ai_soft", "high_growth"],          "risk_type": "mid",
              "style": "サテライト / セキュリティ",
              "alloc_note": "サテライト枠として少額から検討するタイプ"},
    "SNOW":  {"themes": ["ai_soft"],                         "risk_type": "high",
              "style": "サテライト / 高成長",
              "alloc_note": "値動きが大きいため、全体の一部に抑える参考イメージ"},
    # AIソフト・中型成長株
    "PLTR":  {"themes": ["ai_soft", "high_growth"],          "risk_type": "high",
              "style": "サテライト / 高ボラ",
              "alloc_note": "値動きが大きいため、全体の一部に抑える参考イメージ"},
    "ARM":   {"themes": ["semi", "ai_soft"],                 "risk_type": "high",
              "style": "サテライト / 成長枠",
              "alloc_note": "値動きが大きいため、全体の一部に抑える参考イメージ"},
    "SMCI":  {"themes": ["semi", "high_growth"],             "risk_type": "very_high",
              "style": "超高リスク / 少額分散",
              "alloc_note": "初心者は少額・分散・積立前提で検討するタイプ"},
    # AIインフラ・電力
    "VRT":   {"themes": ["infra_power"],                     "risk_type": "mid",
              "style": "サテライト / インフラ",
              "alloc_note": "サテライト枠として少額から検討するタイプ"},
    "GE":    {"themes": ["infra_power", "nisa_core"],        "risk_type": "low",
              "style": "NISA長期 / インフラ安定",
              "alloc_note": "長期保有の中心候補として検討しやすいタイプ"},
    "CEG":   {"themes": ["infra_power"],                     "risk_type": "mid",
              "style": "サテライト / 電力",
              "alloc_note": "サテライト枠として少額から検討するタイプ"},
    # 宇宙通信
    "ASTS":  {"themes": ["space", "high_growth"],            "risk_type": "very_high",
              "style": "超高リスク / 少額分散",
              "alloc_note": "初心者は少額・分散・積立前提で検討するタイプ"},
    "RKLB":  {"themes": ["space", "high_growth"],            "risk_type": "very_high",
              "style": "超高リスク / 少額分散",
              "alloc_note": "初心者は少額・分散・積立前提で検討するタイプ"},
}

# ── リスクタイプの表示設定 ───────────────────────────────────
RISK_TYPE_DISPLAY: dict[str, dict] = {
    "low":       {"label": "低め",       "color": "#00aa66", "stars": 1},
    "mid":       {"label": "中程度",     "color": "#ffaa00", "stars": 3},
    "high":      {"label": "やや高め",   "color": "#ff6600", "stars": 4},
    "very_high": {"label": "非常に高い", "color": "#ff2222", "stars": 5},
}

# ── 参考配分イメージ テキスト ──────────────────────────────────
ALLOC_STYLE_NOTES: dict[str, str] = {
    "low": (
        "📗 長期保有の中心候補として検討しやすいタイプ\n"
        "値動きが比較的安定しており、NISA口座での積立にも向いています。"
    ),
    "mid": (
        "📙 サテライト枠として少額から検討するタイプ\n"
        "成長期待は高いですが、コア（安定株）と組み合わせるイメージです。"
    ),
    "high": (
        "📕 値動きが非常に大きいため、全体の一部に抑える参考イメージ\n"
        "急落時に追加購入できる余力を残しておくことが重要です。"
    ),
    "very_high": (
        "🚨 初心者は少額・分散・積立前提で検討するタイプ\n"
        "上昇余地は大きい一方、元本割れリスクも高いです。全力投入は危険です。"
    ),
}

# ── IPO関連銘柄マップ（上場企業で代替投資できる銘柄）────────────
IPO_RELATED_STOCKS: dict[str, list[dict]] = {
    "SpaceX / Starlink": [
        {"ticker": "RKLB", "name": "Rocket Lab",   "reason": "小型ロケット打ち上げ事業。宇宙輸送の競合かつ恩恵銘柄"},
        {"ticker": "ASTS", "name": "AST SpaceMobile","reason": "衛星ブロードバンド。Starlinkと同分野で競合・成長"},
        {"ticker": "IRDM", "name": "Iridium",       "reason": "衛星通信の老舗。SpaceX台頭で注目度が上昇中"},
    ],
    "OpenAI": [
        {"ticker": "MSFT", "name": "Microsoft",    "reason": "OpenAIへの最大出資者。Azure経由でOpenAI技術を提供"},
        {"ticker": "NVDA", "name": "NVIDIA",       "reason": "OpenAIのAIモデル学習に使われるGPUの主要供給元"},
        {"ticker": "ORCL", "name": "Oracle",       "reason": "OpenAIとのクラウドインフラ提携を発表"},
    ],
    "Anthropic": [
        {"ticker": "AMZN", "name": "Amazon",       "reason": "Anthropicへの最大出資者の一つ。AWS上で提供"},
        {"ticker": "GOOGL", "name": "Alphabet",    "reason": "Anthropicへの大規模投資。GCP上でClaudeを提供"},
    ],
    "Stripe": [
        {"ticker": "ADYEN", "name": "Adyen",       "reason": "欧州の決済大手。Stripeと同分野の上場競合"},
        {"ticker": "V",    "name": "Visa",         "reason": "決済インフラの最大手。Stripe成長の恩恵も受ける"},
    ],
}
