# NTPサーバーから正確な時刻を取得し、JSTやフォーマット済の日付形式で返すモジュール
import ntplib
from datetime import datetime, timezone, timedelta


class TimeException(Exception):
    """timeモジュール用の例外。"""


def fetch_jst() -> datetime:
    """
    NTPサーバからタイムスタンプを取得し、JSTに変換して返却する。

    Returns
    -------
    jst_time: datetime
        JSTを表すdatetime。

    Raises
    -------
    TimeException
        時刻が取得できなかった場合。
    """
    # NTPサーバのリストを定義
    ntp_servers = [
        "ntp.nict.jp",
        "ntp.jst.mfeed.ad.jp",
        "ntp.nifty.com",
        "ntp1.jst.mfeed.ad.jp",
        "ntp1.ocn.ne.jp",
    ]

    # NTPサーバからタイムスタンプを取得するクライアントを初期化
    ntp_client = ntplib.NTPClient()

    for ntp_server in ntp_servers:
        try:
            response = ntp_client.request(ntp_server)
            timestamp = response.tx_time
            # UNIX時刻をJSTに変換する
            jst = timezone(timedelta(hours=+9), "JST")
            jst_time = datetime.fromtimestamp(timestamp, jst)

            return jst_time
        except Exception:
            continue

    raise TimeException("利用可能なNTPサーバがありませんでした")


def get_jst_str() -> str:
    try:
        jst = fetch_jst()
    except TimeException:
        jst = None

    if jst is None:
        return "エラー NTPサーバーから時刻を取得できませんでした。"

    # ミリ秒を計算
    milliseconds = jst.microsecond // 1000

    # 年、月、日、時間、分、秒をフォーマットし、ミリ秒を追加
    formatted_time = jst.strftime("%Y-%m-%d %H:%M:%S") + f".{milliseconds:03d}"

    return formatted_time


def utc_to_jst(datetime_utc) -> datetime:
    # UTCをJSTに変換
    utc = timezone.utc
    jst = timezone(timedelta(hours=9))

    datetime_utc = datetime_utc.replace(tzinfo=utc)
    datetime_jst = datetime_utc.astimezone(jst)

    return datetime_jst
