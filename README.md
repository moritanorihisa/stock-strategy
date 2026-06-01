# 日米業種リードラグ戦略 研究ツール

NY市場の前日終値から、翌営業日の東京市場（TOPIX-17業種ETF）の値動きを予測する研究・検証ツールです。

> 参考: 中川慧ら「部分空間正則化付き主成分分析を用いた日米業種リードラグ投資戦略」（人工知能学会 FIN-036, 2026）

**⚠️ 研究・検証目的専用。発注機能はありません。投資助言ではありません。**

---

## ローカルで動かす

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

ブラウザが自動で開きます。初回はユーザー名とパスワードを入力してください。

---

## 知人限定公開の手順（Streamlit Community Cloud）

### ステップ1：GitHubアカウントを作る

1. https://github.com を開く
2. 右上「Sign up」でアカウント作成（無料）

---

### ステップ2：Private リポジトリを作る

1. GitHub にログインして右上の「＋」→「New repository」
2. 以下を設定：
   - Repository name: `stock-strategy`（任意）
   - **Private** を選択 ← 必ずPrivate！
   - 「Create repository」をクリック

---

### ステップ3：コードをGitHubにアップする

コマンドプロンプトでプロジェクトフォルダに移動して実行：

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/あなたのID/stock-strategy.git
git push -u origin main
```

> `git` がない場合は https://git-scm.com からインストール

**確認**: `.streamlit/secrets.toml` がアップされていないこと（.gitignore に含まれているので自動除外されます）

---

### ステップ4：Streamlit Community Cloud にデプロイする

1. https://share.streamlit.io を開く
2. 「Sign in with GitHub」でGitHubアカウントでログイン
3. 「New app」をクリック
4. 以下を設定：
   - Repository: `あなたのID/stock-strategy`
   - Branch: `main`
   - Main file path: `app.py`
5. 「Deploy!」をクリック

数分でURLが発行されます（例: `https://xxx.streamlit.app`）

---

### ステップ5：secrets.toml をStreamlit Cloud に設定する

デプロイ後、パスワードをクラウド側に設定します。

1. デプロイ済みアプリの管理画面を開く
2. 右上「⋮」→「Settings」→「Secrets」タブ
3. 以下をコピー＆ペーストして、パスワードを変更：

```toml
[users]
alice = "パスワードをここに入力"
bob   = "別の人のパスワード"
```

4. 「Save」をクリック → アプリが自動的に再起動

> ユーザーを追加するときはこの画面に行を追加するだけです

---

### ステップ6：知人に共有する

発行されたURL（例: `https://xxx.streamlit.app`）をLINEやメールで送るだけです。

アクセスするとログイン画面が表示され、設定したユーザー名とパスワードを知っている人だけが利用できます。

---

## ファイル構成

```
stock_strategy/
├── app.py              # Streamlitメイン画面
├── auth.py             # ログイン認証
├── requirements.txt    # 必要ライブラリ
├── .gitignore          # GitHubに上げないファイルの設定
├── data/
│   └── loader.py       # データ取得・キャッシュ・リードラグ処理
├── models/
│   └── predictor.py    # ローリングウィンドウ予測モデル
├── backtest/
│   └── engine.py       # バックテスト・パフォーマンス計算
└── .streamlit/
    ├── config.toml             # 表示設定
    └── secrets.toml.example    # パスワード設定のサンプル
```

---

## ローカル用パスワード設定

ローカルで動かす場合は `.streamlit/secrets.toml` を作成：

```bash
# secrets.toml.example をコピー
copy .streamlit\secrets.toml.example .streamlit\secrets.toml
```

`secrets.toml` を開いてパスワードを変更してください。このファイルはGitHubには上がりません。

---

## 将来VPSへ移行する場合

このアプリはDockerやVPS（さくらVPS、ConoHa等）でも動きます。

```bash
# VPS上で実行するだけ
pip install -r requirements.txt
streamlit run app.py --server.port 8501
```

Nginxでリバースプロキシを設定すれば独自ドメインでも公開できます。
