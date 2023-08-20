import os
import bencodepy
import shutil

class BinaryMatcher:
    def __init__(self, source_folder, piece_folder):
        self.source_folder = source_folder
        self.piece_folder = piece_folder

    def binary_match(self, bin_file):
        # トレントファイルの読み込み
        torrent_file = "source.torrent"
        with open(os.path.join(self.source_folder, torrent_file), "rb") as f:
            torrent_data = bencodepy.decode(f.read())

        # ダウンロード対象のファイルまたはフォルダ名の取得
        download_file_name = torrent_data[b"info"][b"name"].decode("utf-8")
        download_file = os.path.join(self.source_folder, download_file_name)

        # ダウンロードしたファイルまたはフォルダ内の全てのファイルを連結
        if os.path.isdir(download_file):
            concatenated_data = b""
            for root, dirs, files in os.walk(download_file):
                for file in files:
                    with open(os.path.join(root, file), "rb") as f:
                        concatenated_data += f.read()
        else:
            with open(download_file, "rb") as f:
                file_data = f.read()
                concatenated_data = file_data

        # binファイルの読み込み
        with open(os.path.join(self.piece_folder, bin_file), "rb") as f:
            bin_data = f.read()
            
        # binファイルが空なら、その時点でFalseを返す        
        bin_size = self.get_file_size_in_kb(os.path.join(self.piece_folder, bin_file))
        if bin_size == 0:
            return False

        # ピースのバイナリマッチングを行う
        # ピースサイズに応じてスライド処理で比較
        chunk_size = (
            self.get_file_size_in_kb(os.path.join(self.piece_folder, bin_file)) * 1024
        )
        
        if chunk_size == 0:
            raise ValueError(f"Chunk size for file {bin_file} is 0, which is not expected.")

        for i in range(0, len(concatenated_data) - len(bin_data) + 1, chunk_size):
            chunk = concatenated_data[i : i + chunk_size]
            if bin_data in chunk:
                piece_index = int(i / chunk_size)
                return piece_index
        else:
            return False

    def get_file_size_in_kb(self, file_path):
        # ファイルサイズをKB単位で取得
        size_in_bytes = os.path.getsize(file_path)
        size_in_kb = size_in_bytes // 1024
        return size_in_kb

class PeerBinaryMatcher:
    def __init__(self, folder):
        self.folder = folder
        self.source_torrent_path = os.path.join(folder, "source.torrent")
        self.matched_peers_folder = os.path.join(folder, "matched_peers")
        self.false_peers_folder = os.path.join(folder, "false_peers")
        os.makedirs(self.matched_peers_folder, exist_ok=True)
        os.makedirs(self.false_peers_folder, exist_ok=True)

    def _get_dl_target_from_torrent(self):
        with open(self.source_torrent_path, 'rb') as f:
            content = f.read()
            decoded = bencodepy.decode(content)
            if b'info' in decoded and b'name' in decoded[b'info']:
                return decoded[b'info'][b'name'].decode('utf-8')
        return None

    def binary_match(self):
        dl_target = self._get_dl_target_from_torrent()
        
        # 除外するフォルダ名を定義
        exclude_folders = [self.matched_peers_folder, self.false_peers_folder]
        
        # "_"を含むディレクトリをリスト化し、除外対象のフォルダを除外する
        all_folders = [item for item in os.listdir(self.folder) 
                    if os.path.isdir(os.path.join(self.folder, item)) 
                    and "_" in item 
                    and os.path.join(self.folder, item) not in exclude_folders]

        for folder in all_folders:
            if folder == dl_target:
                continue
                    
            current_peer_folder = os.path.join(self.folder, folder)

            if not any(filename.endswith('.log') for filename in os.listdir(current_peer_folder)):
                print(f"フォルダ {folder} にはログファイルが存在しませんでした。")
                destination_folder = self.false_peers_folder
            else:
                matcher = BinaryMatcher(self.folder, current_peer_folder)
                bin_files = [f for f in os.listdir(current_peer_folder) if f.endswith('.bin')]
                match_success = True

                for bin_file in bin_files:
                    result = matcher.binary_match(bin_file)
                    if result is False:
                        match_success = False
                        break

                destination_folder = self.matched_peers_folder if match_success else self.false_peers_folder
            
            # 移動先に同名のフォルダが存在する場合、元のフォルダ名にサフィックスを追加
            counter = 1
            dest_path = os.path.join(destination_folder, folder)
            while os.path.exists(dest_path):
                dest_path = os.path.join(destination_folder, f"{folder}_{counter}")
                counter += 1
            
            # フォルダの移動を試みる
            try:
                shutil.move(current_peer_folder, dest_path)
            except PermissionError:
                print(f"フォルダ {folder} を {dest_path} に移動する際にPermissionErrorが発生しました。")

        print("バイナリマッチによる検証が完了しました。")