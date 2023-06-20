import ntplib
from datetime import datetime, timezone, timedelta


def fetch_jst() -> datetime:
    """
    NTPサーバからタイムスタンプを取得し、JSTに変換して返却する。

    Returns
    -------
    jst_time: datetime
        JSTを表すdatetime。
    """
    # NTPサーバのリストを定義
    ntp_servers = ['ntp.nict.jp', 'ntp.jst.mfeed.ad.jp', 'ntp.nifty.com', 'ntp1.jst.mfeed.ad.jp', 'ntp1.ocn.ne.jp']

    # NTPサーバからタイムスタンプを取得するクライアントを初期化
    ntp_client = ntplib.NTPClient()

    for ntp_server in ntp_servers:
        try:
            response = ntp_client.request(ntp_server)
            timestamp = response.tx_time
            # UNIX時刻をJSTに変換する
            jst = timezone(timedelta(hours=+9), 'JST')
            jst_time = datetime.fromtimestamp(timestamp, jst)

            return jst_time
        except:
            continue

    return datetime.now()


def utc_to_jst(datetime_utc):  
    # UTCをJSTに変換  
    utc = timezone.utc
    jst = timezone(timedelta(hours=9))
    
    datetime_utc = datetime_utc.replace(tzinfo=utc)
    datetime_jst = datetime_utc.astimezone(jst)
    
    return datetime_jst
