import os
from utils.inspector import BinaryMatcher
import tkinter as tk
from tkinter import filedialog


def select_folder(title=None):
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを表示させない
    folder_path = filedialog.askdirectory(title=title)  # フォルダ選択ダイアログを表示
    return folder_path

# フォルダパスを指定
source_folder = select_folder("検証したいDL対象ファイル本体と、DL元になったtorrentファイルが存在するフォルダを選択")
piece_folder = select_folder("検証したいピースが格納されたフォルダを選択")

# BinaryMatcherのインスタンスを作成
matcher = BinaryMatcher(source_folder, piece_folder)

# piece_folder直下の.binファイルをリストに格納
bin_files = [f for f in os.listdir(piece_folder) if f.endswith('.bin') and os.path.isfile(os.path.join(piece_folder, f))]

# 各.binファイルに対してbinary_matchを実行
results = {}
for bin_file in bin_files:
    result = matcher.binary_match(bin_file)
    results[bin_file] = result

print(results)

if not any(value == False for value in results.values()):
    print("すべてのピースが元ファイルの内容と一致しました。")