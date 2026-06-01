"""
銘柄補足情報・IPOウォッチリスト（固定データ）

将来的に外部API（Alpha Vantage等）から動的取得する場合は、
このファイルの定数を API レスポンスで上書きする形で拡張する。
"""

# ── 米国AI株の補足情報 ────────────────────────────────────────
US_STOCK_INFO: dict[str, dict] = {
    "NVDA":  {"name": "NVIDIA",               "category": "AIチップ",        "nisa": 4,
              "comment": "AI向けGPUの圧倒的シェア。データセンター需要が急拡大中。"},
    "MSFT":  {"name": "Microsoft",            "category": "AI×クラウド",     "nisa": 5,
              "comment": "OpenAIとの連携でAzureが急成長。配当もあり安定性高い。"},
    "GOOGL": {"name": "Alphabet (Google)",    "category": "AI×広告",         "nisa": 4,
              "comment": "Gemini AIとクラウド（GCP）が成長ドライバー。"},
    "AMZN":  {"name": "Amazon",               "category": "AI×EC×クラウド",  "nisa": 4,
              "comment": "AWSがクラウドNo.1。AI投資を積極拡大中。"},
    "META":  {"name": "Meta Platforms",       "category": "AI×SNS",          "nisa": 3,
              "comment": "LlamaなどオープンソースAIで存在感。広告収益が安定。"},
    "AMD":   {"name": "AMD",                  "category": "AIチップ",        "nisa": 3,
              "comment": "NVIDIAに次ぐAIチップ候補。InstinctシリーズでHPC市場を狙う。"},
    "ARM":   {"name": "Arm Holdings",         "category": "半導体設計",      "nisa": 3,
              "comment": "スマホ・AI機器のCPU設計をほぼ独占。ライセンス収益モデル。"},
    "PLTR":  {"name": "Palantir",             "category": "AI×データ分析",   "nisa": 3,
              "comment": "政府・企業向けAIプラットフォーム。成長率が急加速中。"},
    "TSM":   {"name": "TSMC",                 "category": "半導体製造",      "nisa": 4,
              "comment": "世界最先端の半導体受託製造。AI需要の恩恵を直接受ける。"},
    "AVGO":  {"name": "Broadcom",             "category": "AIネットワーク",  "nisa": 4,
              "comment": "AIデータセンター向けネットワーク半導体。配当も充実。"},
    "SMCI":  {"name": "Super Micro Computer", "category": "AIサーバー",      "nisa": 2,
              "comment": "AIサーバー需要で急成長だが、会計問題で信頼性リスクあり。"},
    "CRWD":  {"name": "CrowdStrike",          "category": "AIセキュリティ",  "nisa": 3,
              "comment": "AI活用のサイバーセキュリティ最大手。ARRが高成長中。"},
    "SNOW":  {"name": "Snowflake",            "category": "AIデータ基盤",    "nisa": 3,
              "comment": "クラウドデータ基盤。AI時代のデータ分析需要の恩恵を受ける。"},
    "ORCL":  {"name": "Oracle",               "category": "AI×クラウドDB",   "nisa": 4,
              "comment": "クラウドDB転換が加速。AI向けデータベース需要で復活。"},
}

# ── 日本成長株の補足情報 ──────────────────────────────────────
JP_STOCK_INFO: dict[str, dict] = {
    "6920.T": {"name": "レーザーテック",         "category": "EUV半導体検査",    "nisa": 4,
               "comment": "EUV露光装置の検査機器で世界唯一の技術。ASML依存の恩恵を受ける。"},
    "9984.T": {"name": "ソフトバンクグループ",    "category": "AI投資",           "nisa": 3,
               "comment": "ARM保有・Vision Fundを通じてAI企業に幅広く投資。"},
    "6861.T": {"name": "キーエンス",             "category": "FAセンサー・AI",   "nisa": 5,
               "comment": "高付加価値センサー・FAのグローバルリーダー。高い利益率が強み。"},
    "4063.T": {"name": "信越化学",               "category": "半導体材料",       "nisa": 5,
               "comment": "半導体シリコンウェーハで世界最大手。財務健全性も非常に高い。"},
    "6857.T": {"name": "アドバンテスト",         "category": "半導体テスト",     "nisa": 4,
               "comment": "AIチップのテスト装置で高シェア。NVIDIAの恩恵を直接受ける。"},
    "8035.T": {"name": "東京エレクトロン",       "category": "半導体製造装置",   "nisa": 4,
               "comment": "半導体製造装置の世界3位。AI向け先端チップ需要で好調。"},
    "6954.T": {"name": "ファナック",             "category": "FAロボット",       "nisa": 4,
               "comment": "工場自動化ロボットの世界トップ。製造業のAI化を支える。"},
    "9613.T": {"name": "NTTデータグループ",      "category": "DX・AIサービス",   "nisa": 3,
               "comment": "官公庁・金融向けDXとAI導入支援。安定した大型案件が多い。"},
    "4689.T": {"name": "LINEヤフー",             "category": "AI×インターネット","nisa": 3,
               "comment": "国内最大のメッセンジャーとポータル。AI機能を積極導入中。"},
    "3659.T": {"name": "ネクソン",               "category": "ゲーム×AI",        "nisa": 3,
               "comment": "グローバルオンラインゲーム大手。AI活用でゲーム体験を進化中。"},
    "4751.T": {"name": "サイバーエージェント",   "category": "AI広告",           "nisa": 3,
               "comment": "AI活用の広告テクノロジーとAbemaTV。成長速度は安定している。"},
    "3092.T": {"name": "ZOZO",                   "category": "EC×AI",            "nisa": 3,
               "comment": "ファッションECにAIサイズフィットなど先進技術を導入。"},
    "6758.T": {"name": "ソニーグループ",         "category": "AI×エンタメ",      "nisa": 4,
               "comment": "PlayStation・映画・音楽とAIを融合。多角化による安定感がある。"},
    "7203.T": {"name": "トヨタ自動車",           "category": "自動運転・AI",     "nisa": 5,
               "comment": "自動運転・EV・水素に巨額投資。配当実績と財務基盤が極めて安定。"},
}

# ── 全銘柄統合辞書（growth_model.py で使用）──────────────────
ALL_STOCK_INFO: dict[str, dict] = {**US_STOCK_INFO, **JP_STOCK_INFO}

# ── IPO候補ウォッチリスト ─────────────────────────────────────
IPO_WATCHLIST: list[dict] = [
    {
        "name":      "SpaceX / Starlink",
        "symbol":    "非上場",
        "heat":      4,
        "valuation": "約3,500億ドル（2025年資金調達時の想定時価総額）",
        "summary":   "2026年現在、Starlink部門の分離IPOが有力視されている。衛星インターネット事業の急成長が続いており、IPO実現なら時価総額で世界最大級の新規上場になる可能性がある。",
        "jp_note":   "上場時はSBI証券・楽天証券等の米国株口座で購入可能になる見込みだが未確定。NISAでの購入可否も上場後に確認が必要。",
        "risk":      "IPO時期・規模・条件はすべて未確定。報道ベースの情報が多く、予定変更の可能性が高い。",
        "category":  "宇宙・通信",
    },
    {
        "name":      "Anthropic",
        "symbol":    "非上場",
        "heat":      3,
        "valuation": "約600億ドル（2025年資金調達時）",
        "summary":   "Claude（本ツールが使うAI）の開発元。GoogleやAmazonが大規模投資を行っており、生成AI市場でOpenAIと激しく競合している。",
        "jp_note":   "IPO観測はあるが時期は未定。上場時はNASDAQへの上場が有力視されている。",
        "risk":      "非公開企業のため財務情報が限定的。生成AI市場は競争が激しく変化が速い。",
        "category":  "生成AI",
    },
    {
        "name":      "OpenAI",
        "symbol":    "非上場",
        "heat":      3,
        "valuation": "約3,000億ドル（2025年資金調達時）",
        "summary":   "ChatGPT開発元。2025年に営利企業への転換を発表し、IPOへの布石とも見られている。",
        "jp_note":   "IPO実現時は注目度が極めて高く、初値が大幅に上振れる可能性がある反面、過熱リスクも高い。",
        "risk":      "非営利組織からの転換に伴う構造的リスク。著作権訴訟等の法的リスクも存在する。",
        "category":  "生成AI",
    },
    {
        "name":      "Stripe",
        "symbol":    "非上場",
        "heat":      2,
        "valuation": "約700億ドル（直近推定）",
        "summary":   "決済インフラのグローバルリーダー。AI時代の電子商取引拡大の恩恵を受ける構造的成長企業。",
        "jp_note":   "フィンテック・決済分野のNISA長期投資候補として注目度が高い。",
        "risk":      "既存の上場競合（Visa, PayPalなど）との競争。規制リスク。",
        "category":  "フィンテック",
    },
]

# 後方互換のためエイリアスを残す
AI_STOCK_INFO = US_STOCK_INFO
