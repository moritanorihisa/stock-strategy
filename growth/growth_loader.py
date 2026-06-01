"""
成長株データ取得モジュール（米国AI株 + 日本成長株）

設計方針:
  - データ取得は必ずこのモジュールに集約する
  - 将来的に Alpha Vantage / J-Quants 等の有料APIへ移行する際は、
    このファイルの fetch_* 関数だけを差し替えればよい
  - st.cache_data はUIレイヤー(growth_ui.py)で行うため、
    このモジュールはキャッシュに依存しない純粋な取得ロジックとする
  - ディスクキャッシュ（Parquet）は過剰アクセス防止のために実装

yfinance の ticker 命名規則:
  - 米国株 : NVDA, MSFT, ...
  - 日本株 : 6920.T, 9984.T, ... （東証コード + ".T"）
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path
from datetime import date

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

# ── 米国AI関連成長株 ──────────────────────────────────────────
US_AI_TICKERS = [
    "NVDA", "MSFT", "GOOGL", "AMZN", "META",
    "AMD",  "ARM",  "PLTR",  "TSM",  "AVGO",
    "SMCI", "CRWD", "SNOW",  "ORCL",
]

# ── 日本成長株（東証コード + .T）────────────────────────────────
# AI・半導体・テクノロジー系を中心に選定
JP_GROWTH_TICKERS = [
    "6920.T",   # レーザーテック（EUV半導体）
    "9984.T",   # ソフトバンクグループ（AI投資）
    "6861.T",   # キーエンス（FAセンサー・AI）
    "4063.T",   # 信越化学（半導体材料）
    "6857.T",   # アドバンテスト（半導体テスト）
    "8035.T",   # 東京エレクトロン（半導体製造装置）
    "6954.T",   # ファナック（FA・ロボット）
    "9613.T",   # NTTデータグループ（DX・AI）
    "4689.T",   # LINEヤフー（AI×インターネット）
    "3659.T",   # ネクソン（ゲーム×AI）
    "4751.T",   # サイバーエージェント（AI広告）
    "3092.T",   # ZOZO（EC×AI）
    "6758.T",   # ソニーグループ（AI×エンタメ）
    "7203.T",   # トヨタ自動車（自動運転・AI）
]

# 通貨単位
TICKER_CURRENCY = {t: "USD" for t in US_AI_TICKERS}
TICKER_CURRENCY.update({t: "JPY" for t in JP_GROWTH_TICKERS})


# ── 内部ユーティリティ ────────────────────────────────────────

def _cache_key_path(key: str) -> tuple[Path, Path]:
    return CACHE_DIR / f"{key}.parquet", CACHE_DIR / f"{key}_date.txt"


def _is_cache_fresh(date_file: Path) -> bool:
    """当日のキャッシュかどうかを確認する。"""
    if not date_file.exists():
        return False
    return date_file.read_text().strip() == date.today().isoformat()


def _save_cache(key: str, df: pd.DataFrame) -> None:
    data_path, date_path = _cache_key_path(key)
    df.to_parquet(data_path)
    date_path.write_text(date.today().isoformat())


def _load_cache(key: str) -> pd.DataFrame | None:
    data_path, date_path = _cache_key_path(key)
    if data_path.exists() and _is_cache_fresh(date_path):
        return pd.read_parquet(data_path)
    return None


def _fetch_ohlcv(tickers: list[str], period: str, cache_key: str) -> dict[str, pd.DataFrame]:
    """
    複数ティッカーのOHLCVを取得して {ticker: DataFrame} を返す。
    当日キャッシュがあれば再利用する。
    """
    cached = _load_cache(cache_key)
    if cached is not None:
        result = {}
        for t in tickers:
            try:
                # yfinance の multi-ticker parquet は MultiIndex (field, ticker)
                sub = cached.xs(t, axis=1, level=1) if isinstance(cached.columns, pd.MultiIndex) else cached
                if not sub.empty:
                    result[t] = sub.dropna(how="all")
            except Exception:
                pass
        if result:
            return result

    raw = yf.download(
        tickers, period=period,
        auto_adjust=True, progress=False, group_by="ticker",
    )
    try:
        _save_cache(cache_key, raw)
    except Exception:
        pass  # キャッシュ保存失敗は無視

    result = {}
    for t in tickers:
        try:
            df = raw[t].dropna(how="all")
            if not df.empty:
                result[t] = df
        except Exception:
            pass
    return result


# ── 公開 API ─────────────────────────────────────────────────

def fetch_us_price_data(period: str = "1y") -> dict[str, pd.DataFrame]:
    """米国AI株のOHLCVデータを返す。"""
    return _fetch_ohlcv(US_AI_TICKERS, period, "us_growth_prices")


def fetch_jp_price_data(period: str = "1y") -> dict[str, pd.DataFrame]:
    """日本成長株のOHLCVデータを返す。"""
    return _fetch_ohlcv(JP_GROWTH_TICKERS, period, "jp_growth_prices")


def calc_features(price_data: dict[str, pd.DataFrame], market: str = "US") -> pd.DataFrame:
    """
    OHLCVデータからテクニカル特徴量を計算する。

    【特徴量一覧】
    ret_5d        : 直近5日リターン（短期勢い）
    ret_20d       : 直近20日リターン（中期トレンド）
    ret_60d       : 直近60日リターン（長期トレンド）
    vol_20d       : 年率換算20日ボラティリティ（リスク指標）
    vol_ratio     : 直近5日出来高 / 20日平均出来高（需給の変化）
    ma_diff       : (現在値 − 20日MA) / 20日MA（移動平均との乖離）
    up_ratio      : 過去60日の翌日上昇確率
    next_ret_avg  : 過去60日の翌日平均リターン（期待値）
    similar_score : 過去の類似パターン（コサイン類似度）との翌日平均リターン
    market        : "US" or "JP"
    currency      : "USD" or "JPY"
    """
    rows = []
    for ticker, df in price_data.items():
        if len(df) < 65:
            continue
        close  = df["Close"].squeeze()
        volume = df["Volume"].squeeze()

        ret_1d  = close.pct_change()
        ret_5d  = close.pct_change(5).iloc[-1]
        ret_20d = close.pct_change(20).iloc[-1]
        ret_60d = close.pct_change(60).iloc[-1]
        vol_20d = ret_1d.iloc[-20:].std() * np.sqrt(252)
        ma20    = close.iloc[-20:].mean()
        ma_diff = (close.iloc[-1] - ma20) / ma20

        vol5       = volume.iloc[-5:].mean()
        vol20_avg  = volume.iloc[-20:].mean()
        vol_ratio  = float(vol5 / vol20_avg) if vol20_avg > 0 else 1.0

        # 翌日リターンの過去統計（過去60日）
        next_rets     = ret_1d.iloc[-61:-1]       # 60日分
        next_day_rets = ret_1d.iloc[-60:].values  # 対応する翌日リターン
        up_ratio      = float((next_day_rets > 0).mean())
        next_ret_avg  = float(np.nanmean(next_day_rets))

        # 類似パターン検索（直近5日ベクトルに似た過去日の翌日リターン平均）
        similar_score = _calc_similar_pattern_return(ret_1d)

        rows.append({
            "ticker":        ticker,
            "ret_5d":        float(ret_5d),
            "ret_20d":       float(ret_20d),
            "ret_60d":       float(ret_60d),
            "vol_20d":       float(vol_20d),
            "vol_ratio":     vol_ratio,
            "ma_diff":       float(ma_diff),
            "up_ratio":      up_ratio,
            "next_ret_avg":  next_ret_avg,
            "similar_score": similar_score,
            "current_price": float(close.iloc[-1]),
            "market":        market,
            "currency":      TICKER_CURRENCY.get(ticker, "USD"),
        })

    return pd.DataFrame(rows).set_index("ticker") if rows else pd.DataFrame()


def _calc_similar_pattern_return(ret_1d: pd.Series, window: int = 5, lookback: int = 252) -> float:
    """
    直近 window 日のリターンパターンに類似した過去の日を探し、
    その翌日リターンの平均値を返す。

    手法: コサイン類似度でトップ10%の類似日を抽出して平均。
    """
    if len(ret_1d) < lookback + window + 1:
        return float(ret_1d.iloc[-60:].shift(-1).dropna().mean())

    vals     = ret_1d.dropna().values
    current  = vals[-window:]
    norm_cur = np.linalg.norm(current)
    if norm_cur == 0:
        return 0.0

    similarities = []
    for i in range(len(vals) - window - lookback, len(vals) - window - 1):
        if i < 0:
            continue
        past = vals[i : i + window]
        norm_p = np.linalg.norm(past)
        if norm_p == 0:
            continue
        sim      = np.dot(current, past) / (norm_cur * norm_p)
        next_ret = vals[i + window] if i + window < len(vals) else np.nan
        similarities.append((sim, next_ret))

    if not similarities:
        return 0.0

    sim_df    = pd.DataFrame(similarities, columns=["sim", "next_ret"]).dropna()
    threshold = sim_df["sim"].quantile(0.90)
    top_rets  = sim_df[sim_df["sim"] >= threshold]["next_ret"]
    return float(top_rets.mean()) if len(top_rets) > 0 else 0.0
