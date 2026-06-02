"""
外部リンク生成モジュール
銘柄コードからYahoo Finance等の外部URLを生成する。
"""


def yahoo_finance_url(ticker: str) -> str:
    """Yahoo Finance（米国）の銘柄ページURLを返す。"""
    return f"https://finance.yahoo.com/quote/{ticker}"


def yahoo_finance_jp_url(ticker: str) -> str:
    """
    Yahoo Finance Japan の銘柄ページURLを返す。
    日本株は '6920.T' → コード部分 '6920' を使う。
    """
    code = ticker.replace(".T", "")
    return f"https://finance.yahoo.co.jp/quote/{code}.T"


def tradingview_url(ticker: str) -> str:
    """TradingView の銘柄チャートページURLを返す。"""
    if ticker.endswith(".T"):
        code = ticker.replace(".T", "")
        return f"https://www.tradingview.com/chart/?symbol=TSE%3A{code}"
    return f"https://www.tradingview.com/chart/?symbol=NASDAQ%3A{ticker}"


def get_links(ticker: str) -> dict[str, str]:
    """
    銘柄コードから外部リンク辞書を返す。
    日本株（.T付き）と米国株で自動的に振り分ける。
    """
    is_jp = ticker.endswith(".T")
    links = {
        "TradingView（大きなチャート）": tradingview_url(ticker),
    }
    if is_jp:
        links["Yahoo Finance Japan"] = yahoo_finance_jp_url(ticker)
        links["Yahoo Finance（US）"]  = yahoo_finance_url(ticker)
    else:
        links["Yahoo Finance"] = yahoo_finance_url(ticker)
    return links
