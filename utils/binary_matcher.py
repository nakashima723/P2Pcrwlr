# 対象フォルダ内のsource.torrentの情報をもとに、同フォルダ以下にあるピースと
# 本体ファイルのバイナリマッチを実行するモジュール
import bencodepy
import os


class BinaryMatcher:
    def __init__(self, source_file):
        self.source_file = source_file
        self.torrent_data = self.load_torrent_file()
        self.concatenated_data = self.load_concatenated_data()

    def load_torrent_file(self):
        # ファイル存在チェック
        if not os.path.exists(self.source_file):
            raise FileNotFoundError(f"{self.source_file} が見つかりません。")

        with open(self.source_file, "rb") as f:
            return bencodepy.decode(f.read())

    def load_concatenated_data(self):
        source_folder = os.path.dirname(self.source_file)

        # ダウンロード対象のファイルまたはフォルダ名の取得
        download_file_name = self.torrent_data[b"info"][b"name"].decode(
            "utf-8", errors="replace"
        )
        download_file = os.path.join(source_folder, download_file_name)

        # ファイル存在チェック
        if not os.path.exists(download_file):
            raise FileNotFoundError(f"{download_file_name} が見つかりません。")

        # ダウンロードしたファイルまたはフォルダ内の全てのファイルを連結
        if os.path.isdir(download_file):
            # ディレクトリ内のファイルの並び順をソートして保証
            file_paths = [
                os.path.join(root, file)
                for root, _, files in os.walk(download_file)
                for file in sorted(files)
            ]
            concatenated_data = b"".join(
                open(file_path, "rb").read() for file_path in file_paths
            )
        else:
            with open(download_file, "rb") as f:
                concatenated_data = f.read()

        return concatenated_data

    def binary_match(self, bin_file, piece_folder):
        # binファイルの読み込み
        with open(os.path.join(piece_folder, bin_file), "rb") as f:
            bin_data = f.read()

        # binファイルが空なら、その時点でFalseを返す
        if len(bin_data) == 0:
            return False

        # ピースのバイナリマッチングを行う
        piece_length = self.torrent_data[b"info"][b"piece length"]
        for i in range(
            0, len(self.concatenated_data) - len(bin_data) + 1, piece_length
        ):
            chunk = self.concatenated_data[i : i + piece_length]
            if bin_data == chunk:
                piece_index = int(i / piece_length)
                return piece_index

        return False

    def instant_binary_match(self, bin_data, piece_index):
        # ピースダウンロードメソッド中にバイナリマッチを行う
        # ダウンロード元となったtorrentファイルからピース長の情報を取得
        piece_length = self.torrent_data[b"info"][b"piece length"]

        # 全ピース数を計算
        total_pieces = len(self.concatenated_data) // piece_length

        # 指定されたpiece_indexが全ピース数未満であるか確認
        if piece_index >= total_pieces:
            print("指定されたpiece_indexが範囲外です。")
            return False

        # 指定されたpiece_indexのみを検証する
        start_index = piece_index * piece_length
        end_index = (piece_index + 1) * piece_length

        # 指定された範囲内でバイナリマッチングを試行
        chunk = self.concatenated_data[start_index:end_index]
        if bin_data == chunk:
            return piece_index

        return False
