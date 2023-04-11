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

    # スペースの前後にダブルクォートを追加し、先頭と末尾にもダブルクォートを追加
    query = '"' + query.replace(" ", '" "') + '"'

    return query

# pathlib.Path(__file__)でこのファイルの場所を取得し、parents[1] で一階層上を指定する。
# "../"を利用するのと比べて、コードを実行するディレクトリに関係なくevidenceフォルダの位置を決めることができる。
EVIDENCE_FILE_PATH = os.path.join(pathlib.Path(__file__).parents[1], "evidence")
new_file = False

input_str = input("検索語を入力してください: ")
output_str = process_query(input_str)
output_str = urllib.parse.quote(output_str)
print('検索語：' + output_str)


base_url = "https://nyaa.si/"  # スクレイピング対象のウェブサイトのベースURLを記入
search_url = 'https://nyaa.si/?f=0&c=0_0&q=' + output_str
response = urllib.request.urlopen(search_url)

# responseオブジェクトからデコード済みのテキストを取得
html_content = response.read().decode(response.headers.get_content_charset())

soup = BeautifulSoup(html_content, 'html.parser')
# 'data-timestamp' クラスを持つtable dataの text contentを抽出
data_timestamp_elements = soup.find_all('td', attrs={'data-timestamp': True})

if len(data_timestamp_elements) == 0:
    print("「" + input_str + "」アップロードされたファイルなし")
else:
    if len(data_timestamp_elements) > 10:
        data_timestamp_elements = data_timestamp_elements[:10]
        print("「" + input_str + "」10件以上を検出：誤検出ではない場合、これ以上の採取はサイトから直接行ってください。→" + search_url)

    latest_dates = []

    for element in data_timestamp_elements:
        timestamp_str = element.get_text()
        timestamp_str = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)

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
    
    for i, date in enumerate(latest_dates):
        # .torrentで終わるaタグを探す
        torrent_links = [a["href"] for a in soup.find_all("a") if 'href' in a.attrs and a["href"].endswith(".torrent")]
        formatted_date = latest_dates[i]
        
        # これまで取得したtorrentファイルを確認
        log_file_path = os.path.join(torrent_folder, "torrent.log")

        # torrent.logファイルが存在しない場合、作成
        if not os.path.exists(log_file_path):
            with open(log_file_path, "w") as log_file:
                pass

        # torrent.logファイルの内容を取得し、torrent_urlが存在するか検索
        with open(log_file_path, "r+") as log_file:
            content = log_file.read()
            torrent_url = urljoin(base_url, torrent_links[i])
            
            # まだ存在しないファイルだった場合、新規にtorrentファイルをダウンロード
            if torrent_url not in content:
                new_file = True
                     
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
                        log_file_path = os.path.join(new_folder, "evidence_" + folder_time +".log")
                        with open(log_file_path, "w") as log_file:
                            LOG =  "対象ファイル名：" + torrent.name + "\ntorrent取得方法：「" + input_str + "」で検索"+ "\n取得元：" + torrent_url + "\nサイト上で表記されていたアップロード日時：" + formatted_date + "\n証拠フォルダ生成日時：" + folder_time + "\nファイルハッシュ：" + torrent.info_hash
                            log_file.write(LOG)
                    else:
                        os.unlink(temp_file_path)
                        print('フォルダが既に存在します：\n' + new_folder)

if __name__ == "__main__":
    if new_file:
        send_notification("P2Pスレイヤー", "検索語「" + input_str + "」について、新しいファイルが検出されました。")