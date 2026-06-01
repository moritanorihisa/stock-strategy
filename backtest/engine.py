"""
バックテストエンジン
予測スコアに基づいて売買シグナルを生成し、パフォーマンスを計算する。

戦略:
  毎営業日の予測スコアで日本ETFをランキングし、
  上位N業種をロング（寄付き買い→引け売り）、
  下位N業種をショート（またはノーポジ）する。
"""

import numpy as np
import pandas as pd


def generate_signals(
    predictions: pd.DataFrame,
    actual: pd.DataFrame,
    n_long: int = 3,
    n_short: int = 3,
    allow_short: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    予測スコアから売買シグナルと実際のリターンを生成する。

    Parameters
    ----------
    predictions : pd.DataFrame
        予測スコア（各行が1営業日、各列が日本ETF）
    actual : pd.DataFrame
        実際の日中リターン（predictions と同じ形状）
    n_long : int
        ロングする業種数
    n_short : int
        ショートする業種数
    allow_short : bool
        ショートを許可するか（Falseの場合はロングのみ）

    Returns
    -------
    dict with keys:
      "signals"      : シグナル行列（1=ロング, -1=ショート, 0=ノーポジ）
      "daily_returns": 戦略の日次リターン
    """
    common_idx = predictions.index.intersection(actual.index)
    preds = predictions.loc[common_idx]
    rets = actual.loc[common_idx, predictions.columns]

    signals = pd.DataFrame(0, index=preds.index, columns=preds.columns)

    for date in preds.index:
        scores = preds.loc[date].sort_values(ascending=False)
        long_targets = scores.iloc[:n_long].index
        short_targets = scores.iloc[-n_short:].index if allow_short else []

        signals.loc[date, long_targets] = 1
        if allow_short:
            signals.loc[date, short_targets] = -1

    return {"signals": signals, "actual_returns": rets}


def calc_strategy_returns(
    signals: pd.DataFrame,
    actual_returns: pd.DataFrame,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.001,
) -> pd.Series:
    """
    売買シグナルと実際のリターンから、手数料・スリッページ控除後の日次リターンを計算する。

    Parameters
    ----------
    fee_rate : float
        手数料率（片道）
    slippage_rate : float
        スリッページ率（片道）

    Returns
    -------
    pd.Series
        日次戦略リターン（手数料・スリッページ控除後）
    """
    total_cost = fee_rate + slippage_rate

    # 各日のポジション数
    n_positions = signals.abs().sum(axis=1).replace(0, np.nan)

    # 各銘柄のリターン × シグナル
    gross_returns = (signals * actual_returns).sum(axis=1)

    # ポジション均等配分で正規化
    gross_returns_normalized = gross_returns / n_positions.fillna(1)

    # 取引コスト（往復 = 2倍）
    # ポジション変化があった日のみコストを引く
    position_changes = signals.diff().abs().sum(axis=1) / 2
    costs = position_changes * total_cost * 2

    net_returns = gross_returns_normalized - costs

    return net_returns


def calc_performance_metrics(
    daily_returns: pd.Series,
    risk_free_rate: float = 0.0,
    trading_days: int = 252,
) -> dict:
    """
    年率リターン、シャープレシオ、最大ドローダウン、勝率を計算する。
    """
    cum_returns = (1 + daily_returns).cumprod()

    n_days = len(daily_returns)
    total_return = cum_returns.iloc[-1] - 1
    annual_return = (1 + total_return) ** (trading_days / n_days) - 1

    excess_returns = daily_returns - risk_free_rate / trading_days
    sharpe = (
        excess_returns.mean() / excess_returns.std() * np.sqrt(trading_days)
        if excess_returns.std() > 0
        else 0.0
    )

    # 最大ドローダウン
    rolling_max = cum_returns.cummax()
    drawdown = (cum_returns - rolling_max) / rolling_max
    max_drawdown = drawdown.min()

    win_rate = (daily_returns > 0).sum() / (daily_returns != 0).sum()

    return {
        "年率リターン (%)": round(annual_return * 100, 2),
        "シャープレシオ": round(sharpe, 3),
        "最大ドローダウン (%)": round(max_drawdown * 100, 2),
        "勝率 (%)": round(win_rate * 100, 2),
        "総リターン (%)": round(total_return * 100, 2),
        "取引日数": n_days,
    }


def run_backtest(
    predictions: pd.DataFrame,
    actual_returns: pd.DataFrame,
    n_long: int = 3,
    n_short: int = 3,
    allow_short: bool = False,
    fee_rate: float = 0.001,
    slippage_rate: float = 0.001,
) -> dict:
    """
    バックテストを実行して結果をまとめて返す。

    Returns
    -------
    dict with keys:
      "metrics"       : パフォーマンス指標
      "daily_returns" : 日次リターン Series
      "cum_returns"   : 累積リターン Series
      "signals"       : シグナル DataFrame
    """
    result = generate_signals(predictions, actual_returns, n_long, n_short, allow_short)
    signals = result["signals"]
    actual = result["actual_returns"]

    daily_returns = calc_strategy_returns(signals, actual, fee_rate, slippage_rate)
    cum_returns = (1 + daily_returns).cumprod() - 1
    metrics = calc_performance_metrics(daily_returns)

    return {
        "metrics": metrics,
        "daily_returns": daily_returns,
        "cum_returns": cum_returns,
        "signals": signals,
    }


def get_today_signals(
    latest_predictions: pd.Series,
    jp_etf_names: dict[str, str],
    n_long: int = 3,
    n_short: int = 3,
    allow_short: bool = False,
) -> dict[str, pd.DataFrame]:
    """
    最新の予測スコアから本日の売買候補を生成する。

    Parameters
    ----------
    latest_predictions : pd.Series
        最新日の予測スコア（インデックスが日本ETFのティッカー）
    jp_etf_names : dict
        {ティッカー: 業種名}

    Returns
    -------
    dict with keys "buy" and "sell" DataFrames
    """
    scores = latest_predictions.sort_values(ascending=False)

    buy_tickers = scores.iloc[:n_long].index.tolist()
    sell_tickers = scores.iloc[-n_short:].index.tolist() if allow_short else []

    buy_df = pd.DataFrame({
        "ティッカー": buy_tickers,
        "業種": [jp_etf_names.get(t.replace("JP_", "").replace("_intraday", ""), t) for t in buy_tickers],
        "予測スコア": scores.iloc[:n_long].values,
        "方向": "買い（ロング）",
    })

    sell_df = pd.DataFrame({
        "ティッカー": sell_tickers,
        "業種": [jp_etf_names.get(t.replace("JP_", "").replace("_intraday", ""), t) for t in sell_tickers],
        "予測スコア": scores.iloc[-n_short:].values if allow_short else [],
        "方向": "売り（ショート）",
    }) if allow_short else pd.DataFrame()

    return {"buy": buy_df, "sell": sell_df}
