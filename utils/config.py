# 各種設定フォルダへのパスを取得するためのモジュール
import json
import os
import sys
from pathlib import Path


class Config:
    def __init__(self, base_path=None, level=0):
        if getattr(sys, "frozen", False):
            # プログラムが実際に実行されている場所を取得
            self.application_path = Path(sys.executable).parent
        else:
            if base_path:
                self.application_path = Path(base_path)
            else:
                self.application_path = Path(
                    os.path.dirname(os.path.abspath(sys.argv[0]))
                )

            for _ in range(level):
                self.application_path = self.application_path.parent

        self.version = "ver.1.0"
        self.EVI_FOLDER = os.path.join(self.application_path, "evi")
        self.TORRENT_FOLDER = os.path.join(self.EVI_FOLDER, "tor")
        self.SETTING_FOLDER = os.path.join(self.application_path, "settings")
        self.KEYS_FOLDER = os.path.join(self.application_path, "keys")
        self.SETTING_FILE = os.path.join(self.SETTING_FOLDER, "setting.json")
        self.QUERIES_FILE = os.path.join(self.SETTING_FOLDER, "queries.json")
        self.R18_QUERIES_FILE = os.path.join(self.SETTING_FOLDER, "r18queries.json")

        # 存在しない場合、Config側で作成
        folders_to_check = [
            self.EVI_FOLDER,
            self.TORRENT_FOLDER,
            self.SETTING_FOLDER,
            self.KEYS_FOLDER,
        ]

        for folder in folders_to_check:
            if not os.path.exists(folder):
                os.makedirs(folder)

        if self.SETTING_FILE:
            with open(self.SETTING_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            # data辞書に"port"キーが存在するかチェック
            if "port" in data:
                self.MY_PORT = data["port"]
            else:
                self.MY_PORT = 6881
        else:
            self.MY_PORT = 6881
