import json
import os
from torrent.client import Client
import time
from utils.config import Config

# Configクラスのインスタンスを作成
current_dir = os.path.dirname(os.path.abspath(__file__))
con = Config(base_path=current_dir, level=1)

EVI_FOLDER = con.EVI_FOLDER
SETTING_FOLDER = con.SETTING_FOLDER
SETTING_FILE = con.SETTING_FILE

folder_list = []  # 「.process」ファイルを含む証拠フォルダパスのリスト

# フォルダ内のすべてのサブフォルダをチェック
for root, dirs, files in os.walk(EVI_FOLDER):
    # 各ファイルに対してチェック
    for file in files:
        # ファイル名が「.process」であるかどうかを確認
        if file == ".process":
            # 「.process」ファイルを含むフォルダパスをリストに追加
            folder_list.append(root)
            break

source_files = []  # ダウンロード対象とする「source.torrent」ファイルへのパスを格納するリスト

# 「folder_list」内の各フォルダパスを取得
for folder in folder_list:
    # 「source.torrent」へのパスを生成
    source_file_path = os.path.join(folder, "source.torrent")
    # パスを「source_files」リストに追加
    source_files.append(source_file_path)

# JSON ファイルを開き、データを読み込む
with open(SETTING_FILE, "r", encoding="utf-8") as file:
    settings = json.load(file)
    max_list_size = settings.get("max_list_size")

client = Client()

for i in range(len(source_files)):
    # 本体ファイルをダウンロード
    client.download(source_files[i], folder_list[i])

    # ピースの収集対象とするピアの一覧を取得
    print("ピアの一覧を取得しています...")
    peers = client.fetch_peer_list(source_files[i], max_list_size)
    print("採取対象ピア数: " + str(len(peers)))

    # 日本国内からのみダウンロードするなどの設定行ったセッションを作成
    session, info, ip_filter = client.setup_session(source_files[i])

    # 取得した各ピアにピースダウンロードを実行
    if peers:
        for peer in peers:
            client.download_piece(session, info, ip_filter, folder_list[i], peer)
            time.sleep(1)
        print("ピース収集が完了しました。")
    else:
        print("対象となるピアがありませんでした。")
