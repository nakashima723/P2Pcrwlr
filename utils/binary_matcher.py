import os
import bencodepy


class BinaryMatcher:
    def __init__(self, source_folder, piece_folder):
        self.source_folder = source_folder
        self.piece_folder = piece_folder
        self.torrent_data = self.load_torrent_file()
        self.concatenated_data = self.load_concatenated_data()

    def load_torrent_file(self):
        # トレントファイルの読み込み
        torrent_file = "source.torrent"
        file_path = os.path.join(self.source_folder, torrent_file)

        # ファイル存在チェック
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{torrent_file} が見つかりません。")

        with open(file_path, "rb") as f:
            return bencodepy.decode(f.read())

    def load_concatenated_data(self):
        # ダウンロード対象のファイルまたはフォルダ名の取得
        download_file_name = self.torrent_data[b"info"][b"name"].decode("utf-8", errors='replace')
        download_file = os.path.join(self.source_folder, download_file_name)

        # ファイル存在チェック
        if not os.path.exists(download_file):
            raise FileNotFoundError(f"{download_file_name} が見つかりません。")

        # ダウンロードしたファイルまたはフォルダ内の全てのファイルを連結
        if os.path.isdir(download_file):
            # ディレクトリ内のファイルの並び順をソートして保証
            file_paths = [os.path.join(root, file) for root, _, files in os.walk(download_file) for file in sorted(files)]
            concatenated_data = b"".join(open(file_path, "rb").read() for file_path in file_paths)
        else:
            with open(download_file, "rb") as f:
                concatenated_data = f.read()

        return concatenated_data

    def binary_match(self, bin_file):
        # binファイルの読み込み
        with open(os.path.join(self.piece_folder, bin_file), "rb") as f:
            bin_data = f.read()

        # binファイルが空なら、その時点でFalseを返す        
        if len(bin_data) == 0:
            return False

        # ピースのバイナリマッチングを行う
        piece_length = self.torrent_data[b"info"][b"piece length"]
        for i in range(0, len(self.concatenated_data) - len(bin_data) + 1, piece_length):
            chunk = self.concatenated_data[i : i + piece_length]
            if bin_data == chunk:
                piece_index = int(i / piece_length)
                return piece_index

        return False


class PeerBinaryMatcher:
    def __init__(self, folder):
        self.folder = folder
        self.source_torrent_path = os.path.join(folder, "source.torrent")

    def _get_dl_target_from_torrent(self):
        # トレントファイルからダウンロード対象を取得
        with open(self.source_torrent_path, 'rb') as f:
            content = f.read()
            decoded = bencodepy.decode(content)
            if b'info' in decoded and b'name' in decoded[b'info']:
                return decoded[b'info'][b'name'].decode('utf-8', errors='replace')
        return None

    def binary_match(self):        
        mismatched_files = []  # 不一致だったファイル名を格納するリスト

        if not os.path.exists(self.source_torrent_path):
            print("エラー: source.torrentが存在しません。")
            return

        dl_target = self._get_dl_target_from_torrent()

        if dl_target is None or not os.path.exists(os.path.join(self.folder, dl_target)):
            print("エラー: source.torrentで指定されているDL対象が存在しません。")
            return

        # "_"を含むディレクトリをリスト化
        all_folders = [item for item in os.listdir(self.folder)
                       if os.path.isdir(os.path.join(self.folder, item))
                       and "_" in item]

        matcher = BinaryMatcher(self.folder, None)  # 先にインスタンスを作成

        print("バイナリマッチを実行中...（計" + str(len(all_folders)) + "件）")

        for folder in all_folders:
            if folder == dl_target:
                continue

            current_peer_folder = os.path.join(self.folder, folder)
            log_files = [f for f in os.listdir(current_peer_folder) if f.endswith('.log')]

            if not log_files:
                # ログファイルが存在しない場合、新しいログファイルを作成
                error_log_path = os.path.join(current_peer_folder, f"エラー_ログファイルが存在しません_{folder}.log")
                open(error_log_path, 'w').close()
                continue

            bin_files = [f for f in os.listdir(current_peer_folder) if f.endswith('.bin') and not f.startswith(('V_', 'mis_'))]

            for bin_file in bin_files:
                matcher.piece_folder = current_peer_folder  # ピースフォルダを更新
                result = matcher.binary_match(bin_file)
                new_name = ""

                # ファイル名の変更
                if result is not False:  # 正確に判定
                    new_name = os.path.join(current_peer_folder, f"V_{bin_file}")
                else:
                    new_name = os.path.join(current_peer_folder, f"mis_{bin_file}")
                    mismatched_files.append(new_name)

                os.rename(os.path.join(current_peer_folder, bin_file), new_name)

        print("バイナリマッチによる検証が完了しました。")

        if not mismatched_files:
            print("\nすべてのピースが元ファイルの内容と一致しました。")

        if mismatched_files:
            print("\n不一致だったファイル:")
            for file_path in mismatched_files:
                print(file_path)