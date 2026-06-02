"""
時間帯判定ユーティリティ
日本時間で15時を基準に、本日/翌日の表示を切り替える。
"""

from datetime import datetime, timedelta, timezone
import pytz


def get_jst_now() -> datetime:
    """日本標準時(JST)の現在時刻を取得。"""
    jst = pytz.timezone('Asia/Tokyo')
    return datetime.now(jst)


def is_after_market_close() -> bool:
    """
    日本市場の取引終了時刻（15時）を過ぎているかを判定。
    平日のみ有効（土日は常に False）。
    """
    now = get_jst_now()
    weekday = now.weekday()

    # 土日（5, 6）は False
    if weekday >= 5:
        return False

    # 15時以降なら True
    return now.hour >= 15


def get_display_date() -> str:
    """
    表示用の日付を返す。
    15時以降は翌営業日の日付。
    """
    now = get_jst_now()

    if is_after_market_close():
        # 翌営業日を計算
        next_date = now + timedelta(days=1)
        # 土日をスキップ
        while next_date.weekday() >= 5:
            next_date += timedelta(days=1)
        return next_date.strftime("%m月%d日")
    else:
        return now.strftime("%m月%d日")


def get_analysis_label() -> str:
    """
    表示ラベルを返す。
    例: "本日の注目銘柄" or "翌日の注目銘柄"
    """
    if is_after_market_close():
        return f"📅 {get_display_date()}の注目銘柄"
    else:
        return f"📅 本日 {get_display_date()} の注目銘柄"
