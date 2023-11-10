# 指定したTorrentファイル内の各種情報をprintするモジュール
import tkinter as tk
from tkinter import filedialog
import bencodepy

# ファイルダイアログでTorrentファイルを選択
root = tk.Tk()
root.withdraw()
file_path = filedialog.askopenfilename(filetypes=[("Torrent files", "*.torrent")])

# Torrentファイルの内容を読み込む
with open(file_path, "rb") as f:
    torrent_data = f.read()

# Torrentファイルをデコード
decoded = bencodepy.decode(torrent_data)


# デコードしたデータを項目ごとに表示する関数
def print_dict(d, indent=0):
    for key, value in d.items():
        # ピースハッシュなど、データ量が大きい項目は除外
        if key == b"pieces":
            continue

        # 辞書やリストの場合は再帰的に処理
        if isinstance(value, dict):
            print("  " * indent + f"{key.decode('utf-8')}:")
            print_dict(value, indent + 1)
        elif isinstance(value, list):
            print("  " * indent + f"{key.decode('utf-8')}:")
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    print("  " * (indent + 1) + f"[{i}]")
                    print_dict(item, indent + 2)
                else:
                    print("  " * (indent + 1) + f"{item}")
        else:
            print("  " * indent + f"{key.decode('utf-8')}: {value}")


# トップレベルの項目を表示
print("全体の情報:")
print_dict(decoded)

# info辞書内の項目を表示
if b"info" in decoded:
    print("\ninfo辞書内の情報:")
    print_dict(decoded[b"info"])

print("解析が完了しました。")
