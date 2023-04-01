from datetime import datetime, timedelta, timezone
import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from torrentool.api import Torrent
import shutil
import os
import requests
import tempfile
import time

 # フォルダ名・ファイル名に使用できない文字を削除し、ハイフンに置き換える関数
def sanitize_filename(filename: str) -> str:
    invalid_chars = '\\/:*?"<>|'
    sanitized_filename = ''.join(c if c not in invalid_chars else '-' for c in filename)
    return sanitized_filename

 # x日以内の日付時刻かどうかチェックする関数
def is_within_days(datetime_utc):
    # 入力文字列をUTCでdatetimeオブジェクトに変換
    now_utc = datetime.now(timezone.utc)
    three_days_ago = now_utc - timedelta(days=60)
    return datetime_utc >= three_days_ago

# UTCをJSTに変換
def utc_to_jst(datetime_utc):    
    utc = timezone.utc
    jst = timezone(timedelta(hours=9))
    
    datetime_utc = datetime_utc.replace(tzinfo=utc)
    datetime_jst = datetime_utc.astimezone(jst)
    
    return datetime_jst

# 検索語の正規化
def process_query(query):
    # 半角スペースと全角スペースを半角スペースに統一
    query = query.replace("　", " ")

    # 連続するスペースを1つのスペースに置き換え
    query = " ".join(query.split())

    # スペースの前後にダブルクォートを追加し、先頭と末尾にもダブルクォートを追加
    query = '"' + query.replace(" ", '" "') + '"'

    return query

input_str = input("検索語を入力してください: ")
output_str = process_query(input_str)
output_str = urllib.parse.quote(output_str)
print('検索語：' + output_str)

url = 'https://nyaa.si/?f=0&c=0_0&q=' + output_str
response = urllib.request.urlopen(url)

# responseオブジェクトからデコード済みのテキストを取得
html_content = response.read().decode(response.headers.get_content_charset())

soup = BeautifulSoup(html_content, 'html.parser')
# 'data-timestamp' クラスを持つtable dataの text contentを抽出
data_timestamp_elements = soup.find_all('td', attrs={'data-timestamp': True})

if len(data_timestamp_elements) == 0:
    print("「" + input_str + "」アップロードされたファイルなし")
else:
    if len(data_timestamp_elements) > 5:
        data_timestamp_elements = data_timestamp_elements[:5]
    print("「" + input_str + "」5件以上を検出：検索語が適切か確認してください")

    latest_dates = []

    for element in data_timestamp_elements:
        timestamp_str = element.get_text()
        timestamp_str = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)

        if not is_within_days(timestamp_str):
            break
        else:
            datetime_jst = utc_to_jst(timestamp_str)
            formatted_date = datetime_jst.strftime('%Y-%m-%d-%H-%M')
            latest_dates.append(formatted_date)
            
    print('90日以内にアップロードされたファイル:' + str(len(latest_dates)) + '件')

    # evidenceフォルダが存在しない場合は作成
    if not os.path.exists("../evidence"):
        os.makedirs("../evidence")
    torrent_folder = os.path.join("../evidence", "torrent")
    if not os.path.exists(torrent_folder):
        os.makedirs(torrent_folder)
    
    base_url = "https://nyaa.si/"  # スクレイピング対象のウェブサイトのベースURLを記入

    for i, date in enumerate(latest_dates):
        # .torrentで終わるaタグを探す
        torrent_links = [a["href"] for a in soup.find_all("a") if 'href' in a.attrs and a["href"].endswith(".torrent")]
        formatted_date = latest_dates[i]
        
        # これまで取得したtorrentファイルを確認
        log_file_path = os.path.join(torrent_folder, "nyaa_torrent.log")

        # nyaa_torrent.logファイルが存在しない場合、作成
        if not os.path.exists(log_file_path):
            with open(log_file_path, "w") as log_file:
                pass

        # nyaa_torrent.logファイルの内容を取得し、torrent_urlが存在するか検索
        with open(log_file_path, "r+") as log_file:
            content = log_file.read()
            torrent_url = urljoin(base_url, torrent_links[i])
            
            # まだ存在しないファイルだった場合、新規にtorrentファイルをダウンロード
            if torrent_url not in content:
                log_file.write(torrent_url + "\n")
                    
                # i番目のリンク先URLからファイルを取得
                torrent_file = requests.get(torrent_url)
                time.sleep(1)

                # ファイルがtorrentであることを確認し、ファイル名を取得
                if torrent_url.endswith(".torrent"):
                    with tempfile.NamedTemporaryFile(delete=False) as f:
                        temp_file_path = f.name
                        f.write(torrent_file.content)
                    with open(temp_file_path, "rb") as f:
                        torrent = Torrent.from_string(f.read())
                        file_name = sanitize_filename(torrent.name)

                    # 新しいフォルダを作成
                    new_folder = os.path.join("../evidence", "torrent", f"{file_name}_{formatted_date}")
                    if not os.path.exists(new_folder):  # フォルダが存在しない場合のみ作成
                        os.makedirs(new_folder)
                        print('新しく作成されたフォルダ：\n' + new_folder)
                        
                        new_file_name = os.path.join(new_folder, f"{file_name}.torrent")
                        if len(new_file_name) > 200:
                            new_file_name = new_file_name[:200]
                        # torrentファイルを新しいフォルダに移動
                        shutil.move(temp_file_path, new_file_name)
                    else:
                        os.unlink(temp_file_path)
                        print('フォルダが既に存在します：\n' + new_folder)
