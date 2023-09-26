import os
from utils.binary_matcher import BinaryMatcher
import tkinter as tk
from tkinter import filedialog


def select_folder(title=None):
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを非表示にする
    folder_path = filedialog.askdirectory(title=title)  # フォルダ選択ダイアログを表示
    return folder_path


# 検証したいDL対象ファイル本体と、DL元になったtorrentファイルが存在するフォルダの選択
source_folder = select_folder("検証したいDL対象ファイル本体と、DL元になったtorrentファイルが存在するフォルダを選択")

# source_folderの下の.binファイルを含むすべてのサブフォルダのリスト
sub_folders = [
    os.path.join(source_folder, d)
    for d in os.listdir(source_folder)
    if os.path.isdir(os.path.join(source_folder, d))
]
piece_folders_list = [
    f for f in sub_folders if any(fn.endswith(".bin") for fn in os.listdir(f))
]

# 結果を保存するための辞書の初期化
results = {}

print("バイナリマッチを試行中……")

# 各ピースフォルダと.binファイルを反復処理
for piece_folder in piece_folders_list:
    # 各ピースフォルダに対してBinaryMatcherのインスタンスを作成
    matcher = BinaryMatcher(source_folder, piece_folder)

    bin_files = [
        f
        for f in os.listdir(piece_folder)
        if f.endswith(".bin") and os.path.isfile(os.path.join(piece_folder, f))
    ]
    for bin_file in bin_files:
        result = matcher.binary_match(bin_file)
        results[bin_file] = result

# 結果の確認
if not any(isinstance(value, bool) and value is False for value in results.values()):
    print("すべてのピースが元ファイルの内容と一致しました。")
else:
    mismatched_pieces = [
        key
        for key, value in results.items()
        if isinstance(value, bool) and value is False
    ]
    print("次のピースが元ファイルの内容と一致しませんでした：")
    for piece in mismatched_pieces:
        print(piece)
