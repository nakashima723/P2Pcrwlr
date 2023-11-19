# トラッカーサイトに掲載されているCompleteを魚拓するモジュール
# 標準ライブラリ
import bencodepy
import hashlib
import json
import os
import logging
from pathlib import Path
import threading
import time
from urllib.parse import urljoin, urlparse

# サードパーティライブラリ
from bs4 import BeautifulSoup
import requests

# 独自モジュール
from utils.config import Config
import utils.time as ut


current_dir = os.path.dirname(os.path.abspath(__file__))
con = Config(base_path=current_dir, level=1)

EVI_FOLDER = con.EVI_FOLDER
SETTING_FOLDER = con.SETTING_FOLDER
SETTING_FILE = con.SETTING_FILE
TORRENT_FOLDER = con.TORRENT_FOLDER

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("torrent.complete")


# Torrentファイルからinfo_hashを取得
def get_info_hash(torrent_file):
    with open(torrent_file, "rb") as f:
        torrent_data = bencodepy.decode(f.read())

    info = torrent_data[b"info"]
    info_bencoded = bencodepy.encode(info)
    info_hash = hashlib.sha1(info_bencoded).hexdigest()

    return info_hash


def fetch_html(site_url, info_hash):
    try:
        uri = "?q="
        url = site_url + uri + info_hash
        response = requests.get(url)
        if response.status_code == 200:
            return BeautifulSoup(response.content, "html.parser")
        else:
            logger.warning(f"エラー: サイトにアクセスできませんでした。 {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"エラー:  サイトにアクセスできませんでした。 {e}")
        return None


# 「col-md-1」のクラスを持ち、内部テキストが指定されたラベルの次のdivの内部テキストを取得
def find_next_div_text(soup, label, class_name="col-md-1"):
    target_div = soup.find("div", string=label, class_=class_name)
    if target_div:
        next_div = target_div.find_next_sibling("div")
        return next_div.get_text().strip() if next_div else "N/A"
    else:
        return "N/A"


# ログファイルへテキストを書き込む関数
def write_to_log(folder_name, log_file_name, text):
    log_file_path = os.path.join(folder_name, log_file_name)
    with open(log_file_path, "a") as f:  # "a"は追加モード
        f.write(f"\n{text}")


# 取得したinfo_hashに該当するファイルをNyaaのサイト内から検索し、Complete数を取得する
def fetch_complete_evidence(site_url, folder_name, info_hash):
    # URLの組み立て（この部分を追加）
    uri = "?q="
    url = site_url + uri + info_hash

    # 「complete_evidence」サブフォルダの存在チェック
    complete_evidence_folder = os.path.join(folder_name, "complete_evidence")

    # fetch_html関数を使用してHTMLのDOM情報を取得
    soup = fetch_html(site_url, info_hash)

    if soup is not None:
        # 各種テキストを取得
        complete_text = find_next_div_text(soup, "Completed:")
        seeder_text = find_next_div_text(soup, "Seeders:")
        leecher_text = find_next_div_text(soup, "Leechers:")
        log_timestamp = ut.get_jst_str()

        # 「evidence」から始まるログファイルを探して、テキストを追加
        log_files = [
            f
            for f in os.listdir(folder_name)
            if f.startswith("evi") and f.endswith(".log")
        ]
        if log_files:
            write_to_log(
                folder_name,
                log_files[0],
                complete_text
                + " Completed "
                + seeder_text
                + " Seeder "
                + leecher_text
                + " Leecher "
                + log_timestamp
                + " from:"
                + site_url,
            )

        # 「complete_evidence」が存在しない場合のみCSS関連とHTML保存の処理を行う
        if not os.path.exists(complete_evidence_folder):
            os.makedirs(complete_evidence_folder, exist_ok=True)
            save_file_name = f"complete_evidence_{info_hash}.html"
            output_path = os.path.join(complete_evidence_folder, save_file_name)

            # HTML内のCSSファイルへのリンクを見つける
            for link in soup.find_all("link", rel="stylesheet"):
                css_url = urljoin(url, link["href"])
                css_response = requests.get(css_url)

                # クエリパラメータを除去してファイル名を抽出
                parsed_css_url = urlparse(css_url)
                css_filename = os.path.basename(parsed_css_url.path)

                css_filepath = os.path.join(complete_evidence_folder, css_filename)

                # CSSファイルをダウンロードして、指定されたフォルダに保存する
                with open(css_filepath, "wb") as css_file:
                    css_file.write(css_response.content)

                # HTMLファイル内のCSSリンクを更新する
                link["href"] = css_filename

            # HTMLファイルとしてローカルに保存
            output_path = os.path.join(complete_evidence_folder, save_file_name)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(soup.prettify()))


def archive_evidence(urls, folder):
    # .processファイルが存在するかチェック
    process_file = folder / ".process"
    if process_file.exists():
        # source.torrentが存在するかチェック
        torrent_file_path = folder / "source.torrent"
        if torrent_file_path.exists():
            # info_hashを取得
            info_hash = get_info_hash(str(torrent_file_path))

            # 与えられた複数のURLに対してfetch_complete_evidenceを呼び出す
            for url in urls:
                fetch_complete_evidence(url, str(folder), info_hash)
        else:
            logger.warning(f"エラー: フォルダ {folder} に source.torrent が存在しませんでした。")

    time.sleep(3)


def execute():
    time.sleep(60)

    file_lock = threading.Lock()
    with file_lock:
        with open(SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    site_urls = data["site_urls"]
    r18_site_urls = data["r18_site_urls"]

    # TORRENT_FOLDER内のすべてのフォルダをループで処理
    for folder in Path(TORRENT_FOLDER).iterdir():
        if folder.is_dir():
            r18_file = folder / ".r18"

            # .r18ファイルの存在に基づいて、処理するURLリストを決定
            target_urls = r18_site_urls if r18_file.exists() else site_urls
            archive_evidence(target_urls, folder)
