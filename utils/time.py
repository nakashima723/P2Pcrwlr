import ntplib
from datetime import datetime, timezone, timedelta

def fetch_time():
    # NTPサーバのリストを定義
    ntp_servers = ['ntp.nict.jp', 'ntp.jst.mfeed.ad.jp', 'ntp.nifty.com', 'ntp1.jst.mfeed.ad.jp', 'ntp1.ocn.ne.jp']

    # NTPサーバからUNIX時刻を取得するクライアントを初期化
    ntp_client = ntplib.NTPClient()

    unix_time = None
    for ntp_server in ntp_servers:
        try:
            response = ntp_client.request(ntp_server)
            unix_time = response.tx_time
            break
        except:
            continue

    if unix_time is None:
        return 0
    else:
        return unix_time

def fetch_jst() -> datetime:
    """
    NTPサーバからUNIX時刻を取得し、JSTに変換して返却する。

    Returns
    -------
    jst_time: datetime
        JSTを表すdatetime。
    """
    unix_time = fetch_time()

    # UNIX時刻をJSTに変換する
    jst = timezone(timedelta(hours=+9), 'JST')
    jst_time = datetime.fromtimestamp(unix_time, jst)

    return jst_time

def utc_to_jst(datetime_utc):  
    # UTCをJSTに変換  
    utc = timezone.utc
    jst = timezone(timedelta(hours=9))
    
    datetime_utc = datetime_utc.replace(tzinfo=utc)
    datetime_jst = datetime_utc.astimezone(jst)
    
    return datetime_jst
