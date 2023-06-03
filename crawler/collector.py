import os
import pathlib
import libtorrent as lt
from torrent.client import Client

EVIDENCE_FILE_PATH = os.path.join(pathlib.Path(__file__).parents[1], "evidence")
SETTING_FOLDER = os.path.join(pathlib.Path(__file__).parents[1], "settings")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")

folder_list = []  # 「.processing」ファイルを含むフォルダパスのリスト

# フォルダ内のすべてのサブフォルダをチェック
for root, dirs, files in os.walk(EVIDENCE_FILE_PATH):
    # 各ファイルに対してチェック
    for file in files:
        # ファイル名が「.processing」であるかどうかを確認
        if file == ".process":
            # 「.processing」ファイルを含むフォルダパスをリストに追加
            folder_list.append(root)
            break

print(folder_list)

source_files = []  # 「source.torrent」ファイルへのパスを格納するリスト

# 「folder_list」内の各フォルダパスを取得
for folder in folder_list:
    # 「source.torrent」へのパスを生成
    source_file_path = os.path.join(folder, "source.torrent")
    # パスを「source_files」リストに追加
    source_files.append(source_file_path)

print(source_files)

torrent_path = source_files[0]
save_path = folder_list[0]
max_list_size = 10
piece_index = 0

client = Client()

#client.download(torrent_path, save_path)

print("ピアの一覧を取得しています...")
peers = client.fetch_peer_list(torrent_path, max_list_size)
print("peers: " + str(peers))

if(peers != []):
    for i in range(len(peers)):
        client.download_piece(torrent_path, save_path, piece_index, peers[i])
else:
    print("対象となるピアがありませんでした。")