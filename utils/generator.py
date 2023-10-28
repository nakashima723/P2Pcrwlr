# 各種設定ファイルが存在しない場合に、初期設定を生成するモジュール
import json
import os
import threading
from utils.config import Config


class SettingsGenerator:
    def __init__(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        con = Config(base_path=current_dir, level=1)
        self.SETTING_FOLDER = con.SETTING_FOLDER
        self.SETTING_FILE = con.SETTING_FILE
        self.KEYS_FOLDER = con.KEYS_FOLDER

        self.file_lock = threading.Lock()

        # 設定ファイルが存在しない場合は生成
        self.make_setting_json()

    def make_setting_json(self):
        if not os.path.exists(self.SETTING_FOLDER):
            os.makedirs(self.SETTING_FOLDER)

        if not os.path.exists(self.SETTING_FILE):
            data = {
                "interval": 1800,
                "piece_interval": 3600,
                "last_crawl_time": "null",
                "max_list_size": 50,
                "ip_last_modified": 0,
                "piece_download": "true",
                "mail_user": "null",
                "mail_pass": "null",
                "site_urls": ["https://nyaa.si/"],
                "r18_site_urls": ["https://sukebei.nyaa.si/"],
            }
            with self.file_lock:
                with open(self.SETTING_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)

    def make_keys_json(self):
        if not os.path.exists(self.KEYS_FOLDER):
            os.makedirs(self.KEYS_FOLDER)


class QueryGenerator:
    def __init__(self, queries_file):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        con = Config(base_path=current_dir, level=1)
        self.QUERIES_FILE = con.QUERIES_FILE
        self.file_lock = threading.Lock()

    def make_query_json(self):
        if not os.path.exists(self.QUERIES_FILE):
            data = []
            with self.file_lock:
                with open(self.QUERIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
