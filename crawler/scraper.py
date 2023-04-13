from datetime import datetime, timedelta, timezone
import urllib.request
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from torrentool.api import Torrent
import pathlib
import shutil
import os
import requests
import tempfile
import time
import ntplib
import gzip
import json
from plyer import notification

def send_notification(title, message):
    notification.notify(
        title=title,
        message=message,
        app_name="P2Pスレイヤー",
        timeout=1,  # 通知の表示時間（秒）
    )

#NTPサーバからUNIX時刻を取得し、JSTに変換して返却する。
def fetch_jst():
    ntp_server = 'ntp.nict.jp'

    # NTPサーバからUNIX時刻を取得する
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request(ntp_server)
    unix_time = response.tx_time

    # UNIX時刻をJSTに変換する
    jst = timezone(timedelta(hours=+9), 'JST')
    jst_time = datetime.fromtimestamp(unix_time, jst)

    return jst_time

def fetch_time():
    ntp_server = 'ntp.nict.jp'

    # NTPサーバからUNIX時刻を取得する
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request(ntp_server)
    unix_time = response.tx_time

    return unix_time

 # x日以内の日付時刻かどうかチェックする関数
def is_within_days(datetime_utc):
    # 入力文字列をUTCでdatetimeオブジェクトに変換
    now_utc = datetime.now(timezone.utc)
    days_ago = now_utc - timedelta(days=7)
    return datetime_utc >= days_ago

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

    return query

# pathlib.Path(__file__)でこのファイルの場所を取得し、parents[1] で一階層上を指定する。
# "../"を利用するのと比べて、コードを実行するディレクトリに関係なくevidenceフォルダの位置を決めることができる。
EVIDENCE_FILE_PATH = os.path.join(pathlib.Path(__file__).parents[1], "evidence")
SETTING_FOLDER = os.path.join(pathlib.Path(__file__).parents[1], "settings")
QUERIES_FILE = os.path.join(SETTING_FOLDER, "queries.json")
R18_QUERIES_FILE = os.path.join(SETTING_FOLDER, "r18queries.json")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")

def get_element_count(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data:
      return len(data[0])
    
# SETTING_FILEが存在しない場合は生成
if not os.path.exists(SETTING_FILE) or os.stat(SETTING_FILE).st_size == 0:
    data = {
        "interval": 1800,
        "last_crawl_time": "null",
        "site_urls": [
            "https://nyaa.si/"
        ],
        "r18_site_urls": [
            "https://sukebei.nyaa.si/"
        ]
    }
    with open(SETTING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

element_count_queries = get_element_count(QUERIES_FILE)
element_count_r18_queries = get_element_count(R18_QUERIES_FILE)

def scraper(url, file_path):
    page = 1
    while not page == False:
        print(str(page) + "ページ目を探索中......")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            keywords = [item[0] for item in data]        
        
        with open(SETTING_FILE, "r", encoding="utf-8") as f:
            date_data = json.load(f)

        if date_data["last_crawl_time"] is not None and date_data["last_crawl_time"] != "null":
            last_crawl_time = date_data["last_crawl_time"]
        else:
            last_crawl_time = fetch_time()
        
        if page > 1:
            url = url.split('?')[0] + "?p=" + str(page) 
        print(url)

        response = urllib.request.urlopen(url)

        response_content = response.read()
        if response.headers.get('Content-Encoding') == 'gzip':
            response_content = gzip.decompress(response_content)

        html_content = response_content.decode(response.headers.get_content_charset() or 'utf-8')

        soup = BeautifulSoup(html_content, 'html.parser')

        for keyword in keywords:
            new_file = 0
            input_str = process_query(keyword)

            # 'data-timestamp' クラスを持つtd要素を探索
            data_timestamp_elements = soup.find_all('td', attrs={'data-timestamp': True})         
        
            if data_timestamp_elements:
                last_tag = soup.find('td', attrs={'data-timestamp': True}) 
                last_timestamp_str = last_tag['data-timestamp'] 
                last_timestamp = int(last_timestamp_str)
            else:
                print("リストが存在しませんでした。")
                
            target_elements = []
            target_index = []

            # すべてのtr要素を探索
            for row in soup.find_all('tr'):
                title_element = row.find('td', colspan="2")
                data_timestamp_element = row.find('td', attrs={'data-timestamp': True})
                
                if title_element and data_timestamp_element:
                    # aタグのテキスト部分を取得
                    title_text = title_element.find('a').get_text()

                    # titleタグのテキスト文字列に「input_str」が含まれる場合、対象の'data-timestamp' クラスを持つtd要素のtext_contentを抽出
                    # input_str から単語のリストを作成
                    words = input_str.split()

                    # すべての単語が title_text に含まれているかどうか判定
                    if all(word in title_text for word in words):
                        target_elements.append(data_timestamp_element.get_text())
                        target_index.append(data_timestamp_elements.index(data_timestamp_element))

            if len(target_elements) == 0:
                print("検索語「" + input_str + "」アップロードされたファイルなし")
            else:
                if len(target_elements) > 5:
                    target_elements = target_elements[:10]
                    target_index = target_index[:10]
                    print("「" + input_str + "」10件以上を検出：誤検出ではない場合、これ以上の採取はサイトから直接行ってください。→" + url)

                latest_dates = []

                for element in target_elements:
                    timestamp_str = datetime.strptime(element, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)

                    if not is_within_days(timestamp_str):
                        break
                    else:
                        datetime_jst = utc_to_jst(timestamp_str)
                        formatted_date = datetime_jst.strftime('%Y-%m-%d %H:%M') #サイト上でアップされた時刻
                        latest_dates.append(formatted_date)
                        
                print('7日以内にアップロードされたファイル:' + str(len(latest_dates)) + '件')

                # evidenceフォルダが存在しない場合は作成
                if not os.path.exists(EVIDENCE_FILE_PATH):
                    os.makedirs(EVIDENCE_FILE_PATH)
                torrent_folder = os.path.join(EVIDENCE_FILE_PATH, "torrent")
                if not os.path.exists(torrent_folder):
                    os.makedirs(torrent_folder)
                
                for index in target_index:
                    # .torrentで終わるaタグを探す
                    torrent_links = [a["href"] for a in soup.find_all("a") if 'href' in a.attrs and a["href"].endswith(".torrent")]

                    # これまで取得したtorrentファイルを確認
                    logfile_name = input_str + ".log"
                    TORRENT_LOG_FOLDER = os.path.join(SETTING_FOLDER, "torrent_log")
                    logfile_path = os.path.join(TORRENT_LOG_FOLDER, logfile_name)
                    
                    # torrent_logフォルダが存在しない場合、作成
                    if not os.path.exists(TORRENT_LOG_FOLDER):
                        os.makedirs(TORRENT_LOG_FOLDER)

                    # 検索語に対してlogファイルが存在しない場合、作成
                    if not os.path.exists(logfile_path):
                        with open(logfile_path, "w", encoding='utf-8') as log_file:
                            pass

                    # torrent.logファイルの内容を取得し、torrent_urlが存在するか検索
                    with open(logfile_path, "r+", encoding='utf-8') as log_file:
                        content = log_file.read()
                        torrent_url = urljoin(url, torrent_links[index])

                        # まだ存在しないファイルだった場合、新規にtorrentファイルをダウンロード
                        if torrent_url not in content:
                            new_file += 1

                            # index番目のリンク先URLからファイルを取得
                            torrent_file = requests.get(torrent_url)
                            time.sleep(1)
                            
                            # ファイルがtorrentであることを確認し、ファイル名を取得
                            if torrent_url.endswith(".torrent"):
                                with tempfile.NamedTemporaryFile(delete=False) as f:
                                    temp_file_path = f.name
                                    f.write(torrent_file.content)
                                with open(temp_file_path, "rb") as f:
                                    torrent = Torrent.from_string(f.read())
                                    log_file.write(torrent_url + "\n")

                                # フォルダ名に使う現在日時を取得
                                folder_time = fetch_jst().strftime('%Y-%m-%d_%H-%M-%S')
                                # 新しいフォルダを作成
                                new_folder = os.path.join(EVIDENCE_FILE_PATH, "torrent", f"{folder_time}")
                                if not os.path.exists(new_folder):  # フォルダが存在しない場合のみ作成
                                    os.makedirs(new_folder)
                                    print('新しく作成されたフォルダ：\n' + new_folder)
                                    
                                    new_file_name = os.path.join(new_folder, f"source.torrent")
                                    # torrentファイルを新しいフォルダに移動
                                    shutil.move(temp_file_path, new_file_name)
                                    # torrentファイル取得時の情報を記録
                                    logfile_path = os.path.join(new_folder, "evidence_" + folder_time +".log")
                                    with open(logfile_path, 'w', encoding='utf-8') as log_file:
                                        LOG =  "対象ファイル名：" + torrent.name + "\ntorrent取得方法：「" + input_str + "」で検索"+ "\n取得元：" + torrent_url + "\nサイト上で表記されていたアップロード日時：" + formatted_date + "\n証拠フォルダ生成日時：" + folder_time + "\nファイルハッシュ：" + torrent.info_hash
                                        log_file.write(LOG)
                                else:
                                    os.unlink(temp_file_path)
                                    print('フォルダが既に存在します：\n' + new_folder)
            if __name__ == "__main__":
                if new_file:
                    send_notification("P2Pスレイヤー", "検索語「" + input_str + "」について、新しいファイルが検出されました。")
            time.sleep(1)
            
        if last_timestamp > last_crawl_time:
            page += 1
        else:
            page = False
            filename = os.path.basename(file_path)

            if filename == "r18queries.json":
                with open(SETTING_FILE, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data["last_crawl_time"] = fetch_time()
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=4)

with open(SETTING_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

interval = data["interval"]
site_urls = data["site_urls"]
r18_site_urls = data["r18_site_urls"]

for url in site_urls:
    scraper(url, QUERIES_FILE)
for url in r18_site_urls:
    scraper(url, R18_QUERIES_FILE)

time.sleep(1)