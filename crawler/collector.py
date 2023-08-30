import json
import os
import sys
from torrent.client import Client
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstallerが使用する一時ディレクトリ
    application_path = sys._MEIPASS
else:
    application_path = Path(__file__).resolve().parent.parent

EVIDENCE_FOLDER = os.path.join(application_path, "evi")
SETTING_FOLDER = os.path.join(application_path, "settings")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")

folder_list = []  # 「.process」ファイルを含むフォルダパスのリスト

# フォルダ内のすべてのサブフォルダをチェック
for root, dirs, files in os.walk(EVIDENCE_FOLDER):
    # 各ファイルに対してチェック
    for file in files:
        # ファイル名が「.process」であるかどうかを確認
        if file == ".process":
            # 「.process」ファイルを含むフォルダパスをリストに追加
            folder_list.append(root)
            break

source_files = []  # 「source.torrent」ファイルへのパスを格納するリスト

# 「folder_list」内の各フォルダパスを取得
for folder in folder_list:
    # 「source.torrent」へのパスを生成
    source_file_path = os.path.join(folder, "source.torrent")
    # パスを「source_files」リストに追加
    source_files.append(source_file_path)

# JSON ファイルを開き、データを読み込む
with open(SETTING_FILE, 'r', encoding="utf-8") as file:
    settings = json.load(file)
    max_list_size = settings.get('max_list_size')

client = Client()

for i in range(len(source_files)):
    client.download(source_files[i], folder_list[i])
    print("ピアの一覧を取得しています...")
    peers = client.fetch_peer_list(source_files[i], max_list_size)
    print("採取対象ピア数: " + str(len(peers)))

    def process_peer(peer):
        client.download_piece(source_files[i], folder_list[i], peer)

    if peers:
        with ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(process_peer, peers)
        print("ピース収集が完了しました。")
    else:
        print("対象となるピアがありませんでした。")
