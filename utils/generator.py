# 各種設定ファイルが存在しない場合に、初期設定を生成するモジュール
import json
import os
import sys
from pathlib import Path
import threading
import time


class SettingsGenerator:
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

        self.EVI_FOLDER = os.path.join(self.application_path, "evi")
        self.TORRENT_FOLDER = os.path.join(self.EVI_FOLDER, "tor")
        self.SETTING_FOLDER = os.path.join(self.application_path, "settings")
        self.KEYS_FOLDER = os.path.join(self.application_path, "keys")
        self.REMOTE_HOST = os.path.join(self.SETTING_FOLDER, "remote_host.csv")
        self.SETTING_FILE = os.path.join(self.SETTING_FOLDER, "setting.json")
        self.QUERIES_FILE = os.path.join(self.SETTING_FOLDER, "queries.json")
        self.R18_QUERIES_FILE = os.path.join(self.SETTING_FOLDER, "r18queries.json")

        self.file_lock = threading.Lock()

    def make_setting_json(self):
        if not os.path.exists(self.SETTING_FOLDER):
            os.makedirs(self.SETTING_FOLDER)

        if not os.path.exists(self.SETTING_FILE):
            timestamp = time.time()
            data = {
                "interval": 600,
                "piece_interval": 600,
                "last_crawl_time": timestamp,
                "port": 6881,
                "max_list_size": 50,
                "max_upload_limit": 100,
                "ip_last_modified": 0,
                "add_all_peers": False,
                "mail_user": "",
                "mail_pass": "",
                "site_urls": ["https://nyaa.si/"],
                "r18_site_urls": ["https://sukebei.nyaa.si/"],
            }
            with self.file_lock:
                with open(self.SETTING_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

    def make_keys_json(self):
        if not os.path.exists(self.KEYS_FOLDER):
            os.makedirs(self.KEYS_FOLDER)

    def make_evi_folder(self):
        if not os.path.exists(self.EVI_FOLDER):
            os.makedirs(self.EVI_FOLDER)

    def make_query_json(self):
        if not os.path.exists(self.QUERIES_FILE):
            data = []
            with self.file_lock:
                with open(self.QUERIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def make_r18_query_json(self):
        if not os.path.exists(self.R18_QUERIES_FILE):
            data = []
            with self.file_lock:
                with open(self.R18_QUERIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    def make_remote_host_csv(self):
        if not os.path.exists(self.REMOTE_HOST):
            # UTF-8で空のCSVファイルを作成
            with open(self.REMOTE_HOST, "w", encoding="utf-8"):
                pass
