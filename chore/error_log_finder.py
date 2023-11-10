# 指定した証拠フォルダ内のピースファイル取得ログに、エラーになった例が存在するどうか確認するモジュール
import os
import tkinter as tk
from tkinter import filedialog


# ファイルダイアログでフォルダ選択
def select_folder():
    root = tk.Tk()
    root.withdraw()  # ルートウィンドウを表示しない
    folder_path = filedialog.askdirectory()  # フォルダ選択ダイアログを開く
    return folder_path


def find_error_logs(folder_path):
    """
    指定されたフォルダ内のサブフォルダを走査し、.logファイル内に「エラー」という文字列が含まれている場合、
    そのファイル名を表示する。
    """
    for subdir, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".log"):
                file_path = os.path.join(subdir, file)
                try:
                    # UTF-8でファイルを開く試み
                    with open(file_path, "r", encoding="utf-8") as f:
                        if "エラー" in f.read():
                            print(f"エラーが含まれるファイル: {file}")
                        else:
                            print("エラーになったピースはありませんでした。")
                except UnicodeDecodeError:
                    try:
                        # UTF-8での読み込みに失敗した場合、cp932で試す
                        with open(file_path, "r", encoding="cp932") as f:
                            if "エラー" in f.read():
                                print(f"エラーが含まれるファイル: {file}")
                    except UnicodeDecodeError:
                        # それでもエラーが発生した場合、エラーを無視して読み込む
                        with open(
                            file_path, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            if "エラー" in f.read():
                                print(f"エラーが含まれるファイル: {file}")


folder_path = select_folder()
if folder_path:
    find_error_logs(folder_path)
else:
    print("フォルダが選択されませんでした。")
