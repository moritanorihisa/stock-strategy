"""
AI成長株データ取得モジュール
yfinanceで対象銘柄の価格・出来高データを取得し、
予測に必要なテクニカル指標を計算する。
キャッシュを使ってyfinanceへの過剰アクセスを防ぐ。
"""

import pandas as pd
import numpy as np
import yfinance as yf
from pathlib import Path

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

# 対象銘柄
AI_TICKERS = [
    "NVDA", "MSFT", "GOOGL", "AMZN", "META",
    "AMD",  "ARM",  "PLTR",  "TSM",  "AVGO",
    "SMCI", "CRWD", "SNOW",  "ORCL",
]


def fetch_price_data(period: str = "1y") -> dict[str, pd.DataFrame]:
    """
    各銘柄のOHLCVデータを取得する。
    キャッシュファイルが当日分あれば再利用する。
    """
    cache_file = CACHE_DIR / "growth_prices.parquet"
    today_str  = pd.Timestamp.today().strftime("%Y-%m-%d")
    meta_file  = CACHE_DIR / "growth_prices_date.txt"

    # 当日キャッシュがあればそのまま使う
    if cache_file.exists() and meta_file.exists():
        cached_date = meta_file.read_text().strip()
        if cached_date == today_str:
            raw = pd.read_parquet(cache_file)
            # MultiIndex → dict に復元
            result = {}
            for ticker in AI_TICKERS:
                if ticker in raw.columns.get_level_values(1):
                    df = raw.xs(ticker, axis=1, level=1).dropna()
                    if not df.empty:
                        result[ticker] = df
            if result:
                return result

    # 新規取得
    raw = yf.download(AI_TICKERS, period=period, auto_adjust=True, progress=False, group_by="ticker")
    raw.to_parquet(cache_file)
    meta_file.write_text(today_str)

    result = {}
    for ticker in AI_TICKERS:
        try:
            df = raw[ticker].dropna()
            if not df.empty:
                result[ticker] = df
        except Exception:
            pass

    return result


def calc_features(price_data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    各銘柄のテクニカル指標を計算してDataFrameにまとめる。

    指標:
      - ret_5d   : 直近5日リターン（勢い）
      - ret_20d  : 直近20日リターン
      - ret_60d  : 直近60日リターン
      - vol_20d  : 20日ボラティリティ（標準偏差×√252）
      - vol_ratio: 直近5日出来高 / 20日平均出来高（出来高変化）
      - ma_diff  : (現在値 - 20日移動平均) / 20日移動平均
      - up_ratio : 過去60日間の翌日上昇率
      - next_ret_avg: 過去60日間の翌日平均リターン（期待値）
    """
    rows = []
    for ticker, df in price_data.items():
        if len(df) < 65:
            continue
        close  = df["Close"]
        volume = df["Volume"]

        ret_1d   = close.pct_change()
        ret_5d   = close.pct_change(5).iloc[-1]
        ret_20d  = close.pct_change(20).iloc[-1]
        ret_60d  = close.pct_change(60).iloc[-1]
        vol_20d  = ret_1d.iloc[-20:].std() * np.sqrt(252)
        ma20     = close.iloc[-20:].mean()
        ma_diff  = (close.iloc[-1] - ma20) / ma20

        # 出来高変化
        vol5  = volume.iloc[-5:].mean()
        vol20 = volume.iloc[-20:].mean()
        vol_ratio = vol5 / vol20 if vol20 > 0 else 1.0

        # 翌日リターンの過去統計（過去60日）
        next_rets = ret_1d.iloc[-60:].shift(-1).dropna()
        up_ratio      = (next_rets > 0).mean()
        next_ret_avg  = next_rets.mean()

        rows.append({
            "ticker":       ticker,
            "ret_5d":       ret_5d,
            "ret_20d":      ret_20d,
            "ret_60d":      ret_60d,
            "vol_20d":      vol_20d,
            "vol_ratio":    vol_ratio,
            "ma_diff":      ma_diff,
            "up_ratio":     up_ratio,
            "next_ret_avg": next_ret_avg,
            "current_price": close.iloc[-1],
        })

    return pd.DataFrame(rows).set_index("ticker")
