"""
データ取得モジュール
米国セクターETFと日本TOPIX-17業種ETFのOHLCVデータをyfinanceで取得し、
リードラグを考慮した特徴量・ターゲットを作成する。

キャッシュ戦略:
  - yfinanceの生データをParquetでローカルキャッシュ（.cache/）
  - 当日分だけ差分取得してキャッシュを更新
  - Streamlit の @st.cache_data(ttl=3600) で1時間はメモリキャッシュ
"""

import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from pathlib import Path

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(exist_ok=True)

# 米国セクターETF
US_SECTOR_ETFS = {
    "XLK":  "情報技術",
    "XLF":  "金融",
    "XLE":  "エネルギー",
    "XLV":  "ヘルスケア",
    "XLI":  "資本財",
    "XLY":  "一般消費財",
    "XLP":  "生活必需品",
    "XLU":  "公益事業",
    "XLB":  "素材",
    "XLRE": "不動産",
    "XLC":  "通信サービス",
}

# 日本TOPIX-17業種ETF（NEXT FUNDS）
JP_SECTOR_ETFS = {
    "1615.T": "銀行業",
    "1617.T": "食品",
    "1618.T": "エネルギー資源",
    "1619.T": "建設・資材",
    "1620.T": "素材・化学",
    "1621.T": "医薬品",
    "1622.T": "自動車・輸送機",
    "1623.T": "鉄鋼・非鉄",
    "1624.T": "機械",
    "1625.T": "電機・精密",
    "1626.T": "情報通信・サービス",
    "1627.T": "電力・ガス",
    "1628.T": "不動産",
    "1629.T": "小売業",
    "1630.T": "運輸・物流",
    "1631.T": "金融（除く銀行）",
}


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.parquet"


def _load_cache(key: str) -> pd.DataFrame | None:
    path = _cache_path(key)
    if path.exists():
        return pd.read_parquet(path)
    return None


def _save_cache(key: str, df: pd.DataFrame) -> None:
    df.to_parquet(_cache_path(key))


def _download_with_cache(tickers: list[str], start_date: str, end_date: str, cache_key: str) -> pd.DataFrame:
    """
    キャッシュがあれば差分のみ取得してマージする。
    yfinanceへの過剰アクセスを防ぐ。
    """
    cached = _load_cache(cache_key)

    if cached is not None:
        last_cached = cached.index.max()
        fetch_start = (last_cached + timedelta(days=1)).strftime("%Y-%m-%d")
        if fetch_start >= end_date:
            return cached
    else:
        fetch_start = start_date

    raw = yf.download(tickers, start=fetch_start, end=end_date, auto_adjust=True, progress=False)
    if raw.empty:
        return cached if cached is not None else pd.DataFrame()

    new_data = raw["Close"][tickers].copy() if len(tickers) > 1 else raw["Close"].to_frame(tickers[0])
    new_data.index = pd.to_datetime(new_data.index).tz_localize(None)

    if cached is not None:
        merged = pd.concat([cached, new_data])
        merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    else:
        merged = new_data

    _save_cache(cache_key, merged)
    return merged


def download_us_close(start_date: str, end_date: str) -> pd.DataFrame:
    """米国ETF終値をキャッシュ付きで取得し、日次リターンを返す。"""
    tickers = list(US_SECTOR_ETFS.keys())
    close = _download_with_cache(tickers, start_date, end_date, "us_close")
    close.index.name = "Date"
    returns = close.pct_change()
    returns.columns = [f"US_{c}_ret" for c in returns.columns]
    return returns


def download_jp_intraday(start_date: str, end_date: str) -> pd.DataFrame:
    """日本ETFの始値・終値をキャッシュ付きで取得し、日中リターンを返す。"""
    tickers = list(JP_SECTOR_ETFS.keys())

    raw_open = _download_with_cache(tickers, start_date, end_date, "jp_open")
    raw_close = _download_with_cache(tickers, start_date, end_date, "jp_close")

    # jp_open は Open 価格が必要なため別途取得
    raw = yf.download(tickers, start=start_date, end=end_date, auto_adjust=True, progress=False)
    if not raw.empty:
        open_p = raw["Open"][tickers].copy()
        close_p = raw["Close"][tickers].copy()
        open_p.index = pd.to_datetime(open_p.index).tz_localize(None)
        close_p.index = pd.to_datetime(close_p.index).tz_localize(None)
        intraday = (close_p - open_p) / open_p
        intraday.columns = [f"JP_{c}_intraday" for c in intraday.columns]
        _save_cache("jp_intraday", intraday)
        return intraday

    cached = _load_cache("jp_intraday")
    return cached if cached is not None else pd.DataFrame()


def build_dataset(us_returns: pd.DataFrame, jp_intraday: pd.DataFrame) -> pd.DataFrame:
    """
    リードラグ処理:
      米国ETFの前日終値リターン（shift(1)）→ 翌営業日の日本ETF日中リターン
    未来データリークなし。
    """
    us_lagged = us_returns.shift(1)
    us_lagged.columns = [c.replace("_ret", "_lag1") for c in us_lagged.columns]
    df = jp_intraday.join(us_lagged, how="inner").dropna()
    return df


def load_all(start_date: str = "2016-01-01", end_date: str | None = None) -> pd.DataFrame:
    if end_date is None:
        end_date = datetime.today().strftime("%Y-%m-%d")
    us_returns = download_us_close(start_date, end_date)
    jp_intraday = download_jp_intraday(start_date, end_date)
    return build_dataset(us_returns, jp_intraday)


def get_feature_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("US_")]


def get_target_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c.startswith("JP_")]
