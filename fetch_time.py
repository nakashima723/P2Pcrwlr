from datetime import datetime, timedelta, timezone
import ntplib

def fetch_unix_time_from_ntp():
    ntp_server = 'ntp.nict.jp'

    # NTPサーバからUNIX時刻を取得する
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request(ntp_server)
    unix_time = response.tx_time

    return unix_time
def convert_unix_to_jst(unix_time):
    # UNIX時刻をJSTに変換する
    jst = timezone(timedelta(hours=+9), 'JST')
    jst_time = datetime.fromtimestamp(unix_time, jst)

    return jst_time

def fetch_jst():
    unix_time = fetch_unix_time_from_ntp()
    return convert_unix_to_jst(unix_time)