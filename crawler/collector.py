# 対象フォルダのsource.torrentをもとに、本体ファイルのDLとピース収集を行うモジュール
# 標準ライブラリ
import json
import logging
import os
import time

# サードパーティライブラリ
from torrent.client import Client

# 独自モジュール
from utils.binary_matcher import BinaryMatcher
from utils.config import Config
import utils.time as ut


def execute():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger = logging.getLogger("torrent.collector")

    # Configクラスのインスタンスを作成
    current_dir = os.path.dirname(os.path.abspath(__file__))
    con = Config(base_path=current_dir, level=1)

    version = con.version
    EVI_FOLDER = con.EVI_FOLDER
    SETTING_FILE = con.SETTING_FILE

    folder_list = []  # 「.process」ファイルを含む証拠フォルダパスのリスト

    # フォルダ内のすべてのサブフォルダをチェック
    for root, dirs, files in os.walk(EVI_FOLDER):
        # 各ファイルに対してチェック
        for file in files:
            # ファイル名が「.process」であるかどうかを確認
            if file == ".process":
                # 「.process」ファイルを含むフォルダパスを証拠採取の対象リストに追加
                folder_list.append(root)
                break

    source_files = []  # 証拠採取の対象とする「source.torrent」ファイルへのパスを格納するリスト

    # 「folder_list」内の各フォルダパスを取得
    for folder in folder_list:
        # 「source.torrent」へのパスを生成
        source_file_path = os.path.join(folder, "source.torrent")
        # パスを「source_files」リストに追加
        source_files.append(source_file_path)

    # JSON ファイルを開き、データを読み込む
    with open(SETTING_FILE, "r", encoding="utf-8") as file:
        settings = json.load(file)
        max_list_size = settings.get("max_list_size")

    client = Client()

    for i in range(len(source_files)):
        # 本体ファイルをダウンロード
        download_result = client.download(source_files[i], folder_list[i])

        # ダウンロードの成否をチェック
        if not download_result:
            logger.info("本体ファイルがダウンロードできていないため、ピア取得をスキップします。")
            logger.info(ut.get_jst_str().split(".", 1)[0])
            continue  # 存在しない、またはダウンロード失敗の場合は以降の処理をスキップ

        # ピースの収集対象とするピアの一覧を取得
        logger.info("ピアの一覧を取得しています...")
        peers = client.fetch_peer_list(source_files[i], max_list_size)
        logger.info("採取対象ピア数: " + str(len(peers)))

        # 日本国内からのみダウンロードするなど、各種設定を行ったセッションを作成
        session, info, ip_filter = client.setup_session(source_files[i])

        # ピースごとにバイナリマッチ検査を行うためのインスタンスを作成
        matcher = BinaryMatcher(source_files[i])

        # 取得した各ピアにピースダウンロードを実行
        if peers:
            for peer in peers:
                client.download_piece(
                    session, matcher, info, ip_filter, folder_list[i], peer, version
                )
                time.sleep(1)
            logger.info("ピース収集が完了しました。")
            logger.info(ut.get_jst_str().split(".", 1)[0])
        else:
            logger.info("対象となるピアがありませんでした。")
            logger.info(ut.get_jst_str().split(".", 1)[0])
