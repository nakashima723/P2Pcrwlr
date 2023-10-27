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

if not piece_folders_list:
    print("マッチ対象となるフォルダ・ピースファイルが見つかりませんでした。\n「ピースファイルをサブフォルダ内に含む」フォルダを選択してください。")
else:
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
        print(piece_folder)
        for bin_file in bin_files:
            result = matcher.binary_match(bin_file)

            # resultが0で、かつbin_fileの中身がすべて空白である場合
            if result == 0:
                with open(os.path.join(piece_folder, bin_file), "rb") as f:
                    file_content = f.read()
                if all(
                    b == 0x20 or b == 0x00 for b in file_content
                ):  # すべてのバイトが空白（0x20）またはNullバイト（0x00）であるか
                    result = None

            results[bin_file] = result

    # 結果の確認
    # valueがFalseであるresults.items()の中身をmismatched_piecesとしてリストに収録
    mismatched_pieces = [
        key
        for key, value in results.items()
        if isinstance(value, bool) and value is False
    ]

    # valueがNoneであるresults.items()の中身をblank_piecesとしてリストに収録
    blank_pieces = [key for key, value in results.items() if value is None]

    # mismatched_piecesとblank_piecesが存在しない場合、すべてのピースが一致したと表示
    if not mismatched_pieces and not blank_pieces:
        print("すべてのピースが元ファイルの内容と一致しました。")
    else:
        if mismatched_pieces:
            print("次のピースは元ファイルの内容と一致しませんでした：")
            for piece in mismatched_pieces:
                print(piece)

        if blank_pieces:
            print("次のピースは空白で占められたファイルでした。piece_indexが0ではないなら、通信エラーの可能性があります。")
            for piece in blank_pieces:
                print(piece)
