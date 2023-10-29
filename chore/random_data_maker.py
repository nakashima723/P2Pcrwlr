import os
import zipfile
import random
import string


# 64文字のランダムな文字列を生成する関数
def generate_random_string(length):
    letters = string.ascii_letters + string.digits
    return "".join(random.choice(letters) for i in range(length))


# ファイル名をランダムな64文字の文字列で生成
random_filename = generate_random_string(32)
zipname = random_filename + ".zip"
random_filename = random_filename + ".bin"

# 1MB（10240 * 1024 バイト）のランダムなバイナリデータを生成
random_data = os.urandom(10240 * 1024)

# バイナリデータを一時ファイルに保存
with open(random_filename, "wb") as f:
    f.write(random_data)

# ZIPファイルを作成し、一時ファイルを追加
with zipfile.ZipFile(zipname, "w", zipfile.ZIP_DEFLATED) as zipf:
    zipf.write(random_filename, random_filename)

print("ZIPファイルを生成しました。")
