import json
import os
import sys
from pathlib import Path
import threading


class SettingsGenerator:
    def __init__(self):
        if getattr(sys, "frozen", False):
            # PyInstallerが使用する一時ディレクトリ
            self.application_path = sys._MEIPASS
        else:
            self.application_path = Path(__file__).resolve().parent.parent

        self.SETTING_FOLDER = os.path.join(self.application_path, "settings")
        self.SETTING_FILE = os.path.join(self.SETTING_FOLDER, "setting.json")

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
                "mail_user": "null",
                "mail_pass": "null",
                "site_urls": ["https://nyaa.si/"],
                "r18_site_urls": ["https://sukebei.nyaa.si/"],
            }
            with self.file_lock:
                with open(self.SETTING_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)


class QueryGenerator:
    def __init__(self, queries_file):
        if getattr(sys, "frozen", False):
            # PyInstallerが使用する一時ディレクトリ
            self.application_path = sys._MEIPASS
        else:
            self.application_path = Path(__file__).resolve().parent.parent

        self.QUERIES_FILE = os.path.join(self.application_path, queries_file)
        self.file_lock = threading.Lock()

    def make_query_json(self):
        if not os.path.exists(self.QUERIES_FILE):
            data = []
            with self.file_lock:
                with open(self.QUERIES_FILE, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
