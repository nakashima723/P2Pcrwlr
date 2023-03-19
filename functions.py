from datetime import datetime, timedelta, timezone
import urllib.request
from bs4 import BeautifulSoup

def is_within_days(datetime_utc):
    # x日以内の日付時刻かどうかチェックする関数
    # 入力文字列をUTCでdatetimeオブジェクトに変換
    now_utc = datetime.now(timezone.utc)
    three_days_ago = now_utc - timedelta(days=90)
    return datetime_utc >= three_days_ago

def utc_to_jst(datetime_utc):    
    # UTCをJSTに変換
    utc = timezone.utc
    jst = timezone(timedelta(hours=9))
    
    datetime_utc = datetime_utc.replace(tzinfo=utc)
    datetime_jst = datetime_utc.astimezone(jst)
    
    return datetime_jst

def process_query(query):
    # 半角スペースと全角スペースを半角スペースに統一
    query = query.replace("　", " ")

    # 連続するスペースを1つのスペースに置き換え
    query = " ".join(query.split())

    # スペースの前後にダブルクォートを追加し、先頭と末尾にもダブルクォートを追加
    query = '"' + query.replace(" ", '" "') + '"'

    return query