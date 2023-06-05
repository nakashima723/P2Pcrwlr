import os
import bencodepy

class BinaryMatcher:
    def __init__(self, source_folder, piece_folder):
        self.source_folder = source_folder
        self.piece_folder = piece_folder

    def binary_match(self, bin_file):
        # トレントファイルの読み込み
        torrent_file = "source.torrent"
        with open(os.path.join(self.source_folder, torrent_file), 'rb') as f:
            torrent_data = bencodepy.decode(f.read())

        # ダウンロード対象のファイルまたはフォルダ名の取得
        download_file_name = torrent_data[b'info'][b'name'].decode('utf-8')
        download_file = os.path.join(self.source_folder, download_file_name)
        print(download_file)

        # ダウンロードしたファイルまたはフォルダ内の全てのファイルを連結
        if os.path.isdir(download_file):
            concatenated_data = b""
            for root, dirs, files in os.walk(download_file):
                for file in files:
                    with open(os.path.join(root, file), 'rb') as f:
                        concatenated_data += f.read()
        else:
            with open(download_file, 'rb') as f:
                file_data = f.read()
                concatenated_data = file_data

        # binファイルの読み込み
        with open(os.path.join(self.piece_folder, bin_file), 'rb') as f:
            bin_data = f.read()

        # ピースのバイナリマッチングを行う
        # ピースサイズに応じてスライド処理で比較
        chunk_size = self.get_file_size_in_kb(os.path.join(self.piece_folder, bin_file)) * 1024

        for i in range(0, len(concatenated_data) - len(bin_data) + 1, chunk_size):
            chunk = concatenated_data[i:i + chunk_size]
            if bin_data in chunk:
                piece_index = int(i/chunk_size)
                return piece_index
        else:
            return False
        
def get_file_size_in_kb(file_path):
    # ファイルサイズをKB単位で取得
    size_in_bytes = os.path.getsize(file_path)
    size_in_kb = size_in_bytes // 1024
    return size_in_kb
