import bencodepy

# Torrentファイルの読み込み
with open("example.torrent", "rb") as f:
    torrent_data = f.read()

# bencodepyライブラリを使用して、Torrentファイルの情報をデコードする
torrent = bencodepy.decode(torrent_data)

# Torrentファイルから抽出した情報を格納する辞書を作成する
torrent_info = {
    "announce": torrent[b"announce"].decode(),
    "info": {
        "name": torrent[b"info"][b"name"].decode(),
        "piece length": torrent[b"info"][b"piece length"]
    },
    "creation date": torrent.get(b"creation date", None),
    "created by": torrent.get(b"created by", None),
    "comment": torrent.get(b"comment", None)
}

# 辞書の内容を表示する
print(torrent_info)
