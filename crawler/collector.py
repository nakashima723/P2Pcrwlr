# 対象フォルダのsource.torrentをもとに、本体ファイルのDLとピース収集を行うモジュール
# 標準ライブラリ
import json
import logging
import os

# サードパーティライブラリ
from torrent.client import Client

# 独自モジュール
from utils.config import Config
import utils.time as ut


def execute():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
    logger = logging.getLogger("torrent.collector")

    # Configクラスのインスタンスを作成
    current_dir = os.path.dirname(os.path.abspath(__file__))
    con = Config(base_path=current_dir, level=1)

    EVI_FOLDER = con.EVI_FOLDER
    MAX_LIST_SIZE = con.MAX_LIST_SIZE

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
        log = client.get_peer_log(source_files[i], MAX_LIST_SIZE)

        if not len(log) == 0:
            logger.info("ピース収集が完了しました。")
            logger.info(ut.get_jst_str().split(".", 1)[0])
        else:
            logger.info("対象となるピアがありませんでした。")
            logger.info(ut.get_jst_str().split(".", 1)[0])
