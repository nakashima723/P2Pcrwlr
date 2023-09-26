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
import gzip
import json
import threading
from plyer import notification
import smtplib
from email.message import EmailMessage
import utils.time as ut

file_lock = threading.Lock()
new_file = []


def send_notification(title, message):
    notification.notify(
        title=title,
        message=message,
        app_name="P2Pスレイヤー",
        timeout=1,  # 通知の表示時間（秒）
    )


# x日以内の日付時刻かどうかチェックする関数
def is_within_days(datetime_utc):
    # 入力文字列をUTCでdatetimeオブジェクトに変換
    now_utc = datetime.now(timezone.utc)
    days_ago = now_utc - timedelta(days=7)
    return datetime_utc >= days_ago


# 検索語の正規化
def process_query(query):
    # 半角スペースと全角スペースを半角スペースに統一
    query = query.replace("　", " ")

    # 連続するスペースを1つのスペースに置き換え
    query = " ".join(query.split())

    return query


# pathlib.Path(__file__)でこのファイルの場所を取得し、parents[1] で一階層上を指定する。
# "../"を利用するのと比べて、コードを実行するディレクトリに関係なくevidenceフォルダの位置を決めることができる。
EVIDENCE_FILE_PATH = os.path.join(pathlib.Path(__file__).parents[1], "evi")
SETTING_FOLDER = os.path.join(pathlib.Path(__file__).parents[1], "settings")
QUERIES_FILE = os.path.join(SETTING_FOLDER, "queries.json")
R18_QUERIES_FILE = os.path.join(SETTING_FOLDER, "r18queries.json")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")


def url_in_r18_site_urls(R18_QUERIES_FILE, url):
    # JSONファイルを開き、内容を読み込む
    with open(SETTING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 'r18_site_urls'内に指定されたURLが存在するか確認する
    if url in data["r18_site_urls"]:
        return True
    else:
        return False


def scraper(url, file_path):
    page = 1
    while bool(page):
        with file_lock:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                keywords = [item[0] for item in data]

        if len(keywords) == 0:
            print("「" + url + "」に対する検索語が存在しないため、処理を中断しました。")
            with file_lock:
                with open(SETTING_FILE, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    try:
                        data["last_crawl_time"] = ut.fetch_jst().timestamp()
                    except ut.TimeException:
                        data["last_crawl_time"] = ut.utc_to_jst(
                            datetime.now()
                        ).timestamp()
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=4)
                    f.truncate()
                break
        with file_lock:
            with open(SETTING_FILE, "r", encoding="utf-8") as f:
                date_data = json.load(f)

        if (
            date_data["last_crawl_time"] is not None
            and date_data["last_crawl_time"] != "null"
        ):
            last_crawl_time = date_data["last_crawl_time"]
        else:
            try:
                data["last_crawl_time"] = ut.fetch_jst().timestamp()
            except ut.TimeException:
                data["last_crawl_time"] = ut.utc_to_jst(datetime.now()).timestamp()

        if page > 1:
            url = url.split("?")[0] + "?p=" + str(page)

        print(url.split("?")[0] + " " + str(page) + "ページ目を探索中......")
        response = urllib.request.urlopen(url)

        response_content = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            response_content = gzip.decompress(response_content)

        html_content = response_content.decode(
            response.headers.get_content_charset() or "utf-8"
        )

        soup = BeautifulSoup(html_content, "html.parser")

        for keyword in keywords:
            input_str = process_query(keyword)

            # ページ末尾の'data-timestamp' クラスを持つtd要素を探索
            data_timestamp_elements = soup.find_all(
                "td", attrs={"data-timestamp": True}
            )

            if data_timestamp_elements:
                last_tag = soup.find_all("td", attrs={"data-timestamp": True})[-1]
                last_timestamp_str = last_tag["data-timestamp"]
                last_timestamp = int(last_timestamp_str)
            else:
                print("リストが存在しませんでした。URLや、HTMLの取得方法が間違っている可能性があります。")
                break

            timestamp_elements = []
            torrent_urls = []

            words = input_str.split()

            for td in soup.find_all("td", colspan="2"):
                a_tags = td.find_all("a", title=True)  # 全てのaタグを取得する

                # 各aタグを確認し、条件に合致するものが1つでもあるかを判定
                condition_met = any(
                    all(word in a.get_text() for word in words) for a in a_tags
                )

                if condition_met:
                    # 同じ<tr>タグの中のdata-timestampを探す
                    parent_row = td.find_parent("tr")
                    timestamp_td = parent_row.find("td", {"data-timestamp": True})
                    if timestamp_td:
                        timestamp_elements.append(timestamp_td["data-timestamp"])

                    # td内の最初のaタグを用いて、torrentのURLを生成
                    first_a_tag = a_tags[0]
                    href_value = first_a_tag["href"]
                    href = href_value.split("#")[0]
                    modified_href = href.replace("/view", "download") + ".torrent"
                    modified_url = url.split("?")[0]
                    full_url = modified_url + modified_href
                    torrent_urls.append(full_url)

            if not len(timestamp_elements) == 0:
                if len(timestamp_elements) > 10:
                    timestamp_elements = timestamp_elements[:10]
                    print(
                        "「"
                        + input_str
                        + "」10件以上を検出：誤検出ではない場合、これ以上の採取はサイトから直接行ってください。→"
                        + url
                    )

                latest_dates = []

                for element in timestamp_elements:
                    timestamp_int = int(element)
                    timestamp_str = datetime.fromtimestamp(timestamp_int).replace(
                        tzinfo=timezone.utc
                    )
                    if not is_within_days(timestamp_str):
                        break
                    else:
                        datetime_jst = ut.utc_to_jst(timestamp_str)
                        formatted_date = datetime_jst.strftime(
                            "%Y-%m-%d %H:%M"
                        )  # サイト上でアップされた時刻
                        latest_dates.append(formatted_date)

                print("新たにアップロードされたファイル:" + str(len(latest_dates)) + "件")

                # evidenceフォルダが存在しない場合は作成
                if not os.path.exists(EVIDENCE_FILE_PATH):
                    os.makedirs(EVIDENCE_FILE_PATH)
                torrent_folder = os.path.join(EVIDENCE_FILE_PATH, "tor")
                if not os.path.exists(torrent_folder):
                    os.makedirs(torrent_folder)

                for index, torrent_url in enumerate(torrent_urls):
                    # これまで取得したtorrentファイルを確認
                    logfile_name = input_str + ".log"
                    TORRENT_LOG_FOLDER = os.path.join(SETTING_FOLDER, "torrent_log")
                    logfile_path = os.path.join(TORRENT_LOG_FOLDER, logfile_name)

                    # torrent_logフォルダが存在しない場合、作成
                    if not os.path.exists(TORRENT_LOG_FOLDER):
                        os.makedirs(TORRENT_LOG_FOLDER)

                    # 検索語に対してlogファイルが存在しない場合、作成
                    if not os.path.exists(logfile_path):
                        with open(logfile_path, "w", encoding="utf-8") as log_file:
                            pass

                    # torrent.logファイルの内容を取得し、torrent_urlが存在するか検索
                    with file_lock:
                        with open(logfile_path, "r+", encoding="utf-8") as log_file:
                            content = log_file.read()

                            # まだ存在しないファイルだった場合、新規にtorrentファイルをダウンロード
                            if torrent_url not in content:
                                new_file.append(input_str)

                                # index番目のリンク先URLからファイルを取得
                                torrent_file = requests.get(torrent_url)
                                time.sleep(1)
                                if torrent_file.status_code != 200:
                                    print(
                                        f"トレントファイルを {torrent_url} からダウンロードすることができませんでした。 Status code: {torrent_file.status_code}"
                                    )
                                    continue  # 次のURLへスキップ

                                # ファイルがtorrentであることを確認し、ファイル名を取得
                                if torrent_url.endswith(".torrent"):
                                    with tempfile.NamedTemporaryFile(delete=False) as f:
                                        temp_file_path = f.name
                                        f.write(torrent_file.content)
                                    with open(temp_file_path, "rb") as f:
                                        torrent = Torrent.from_string(f.read())
                                        log_file.write(torrent_url + "\n")

                                    # フォルダ名に使う現在日時を取得
                                    try:
                                        folder_time = ut.fetch_jst().strftime(
                                            "%Y-%m-%d_%H-%M-%S"
                                        )
                                    except ut.TimeException:
                                        # 現在のエポックタイムを取得
                                        current_time = time.time()

                                        # エポックタイムから datetime オブジェクトを構築し、UTCタイムゾーン情報を付与
                                        current_datetime = datetime.fromtimestamp(
                                            current_time, timezone.utc
                                        )
                                        folder_time = ut.utc_to_jst(
                                            current_datetime
                                        ).strftime("%Y-%m-%d_%H-%M-%S")
                                        print(
                                            "フォルダ生成：NTPサーバーから現在時刻を取得できませんでした。フォルダ名はローカルのシステム時刻を参照しており、正確な生成時刻を示していない可能性があります。"
                                        )
                                    # 新しいフォルダを作成
                                    new_folder = os.path.join(
                                        EVIDENCE_FILE_PATH, "tor", f"{folder_time}"
                                    )
                                    if not os.path.exists(
                                        new_folder
                                    ):  # フォルダが存在しない場合は作成
                                        os.makedirs(new_folder)
                                        print("新しく作成されたフォルダ：\n" + new_folder)

                                        new_file_name = os.path.join(
                                            new_folder, "source.torrent"
                                        )
                                        # torrentファイルを新しいフォルダに移動
                                        shutil.move(temp_file_path, new_file_name)
                                        # torrentファイル取得時の情報を記録
                                        logfile_path = os.path.join(
                                            new_folder, "evi_" + folder_time + ".log"
                                        )
                                        with open(
                                            logfile_path, "w", encoding="utf-8"
                                        ) as log_file:
                                            LOG = (
                                                "対象ファイル名："
                                                + torrent.name
                                                + "\ntorrent取得方法：「"
                                                + input_str
                                                + "」で検索"
                                                + "\n取得元："
                                                + torrent_url
                                                + "\nサイト上で表記されていたアップロード日時："
                                                + formatted_date
                                                + "\n証拠フォルダ生成日時："
                                                + folder_time
                                                + "\nファイルハッシュ："
                                                + torrent.info_hash
                                            )
                                            log_file.write(LOG)
                                        # 成人向け作品をマーク
                                        if url_in_r18_site_urls(R18_QUERIES_FILE, url):
                                            r18_file_path = os.path.join(
                                                new_folder, ".r18"
                                            )
                                            with open(r18_file_path, "w") as f:
                                                pass
                                    else:
                                        os.unlink(temp_file_path)
                                        print("フォルダが既に存在します：\n" + new_folder)
        if last_timestamp > last_crawl_time:
            page += 1
        else:
            page = False
            filename = os.path.basename(file_path)

            if filename == "r18queries.json":
                with file_lock:
                    with open(SETTING_FILE, "r+", encoding="utf-8") as f:
                        data = json.load(f)
                        try:
                            data["last_crawl_time"] = ut.fetch_jst().timestamp()
                        except ut.TimeException:
                            data["last_crawl_time"] = ut.utc_to_jst(
                                datetime.now()
                            ).timestamp()
                        f.seek(0)
                        json.dump(data, f, ensure_ascii=False, indent=4)
                        f.truncate()


with file_lock:
    with open(SETTING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
interval = data["interval"]
site_urls = data["site_urls"]
r18_site_urls = data["r18_site_urls"]
mail_user = data["mail_user"]
mail_pass = data["mail_pass"]

for url in site_urls:
    scraper(url, QUERIES_FILE)
    time.sleep(1)
for url in r18_site_urls:
    scraper(url, R18_QUERIES_FILE)
    time.sleep(1)

if __name__ == "__main__":
    if new_file:
        unique_list = list(set(new_file))
        new_file_wrapped = ["「" + s + "」" for s in unique_list]
        new_file_str = "".join(new_file_wrapped)
        notification_str = (
            new_file_str + "について、新しいファイルが" + str(len(new_file)) + "件検出されました。"
        )
        send_notification("P2Pスレイヤー", notification_str)

        # 送信元に使うメールアドレスが設定されている場合
        if mail_user is not None and mail_user != "null":
            # メールの内容を設定
            msg = EmailMessage()
            msg.set_content(notification_str + "\nただちにP2Pスレイヤーを起動し、証拠採取を行ってください。")

            msg["Subject"] = "【P2Pスレイヤー】新しいファイルが検出されました"
            msg["From"] = mail_user
            msg["To"] = mail_user

            # GmailのSMTPサーバーに接続してメールを送信
            try:
                server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
                server.login(mail_user, mail_pass)
                server.send_message(msg)
                server.quit()
                print("メールが送信されました。")
            except Exception as e:
                print(f"メールの送信に失敗しました: {e}")


time.sleep(1)
