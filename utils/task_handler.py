# 設定ファイル内のinterval値に応じて、指定したpythonモジュールを繰り返し実行するモジュール
import json
import os
import time
from utils.config import Config
import crawler.scraper
import crawler.collector
import crawler.fetch_ip_list
import crawler.get_complete_evidence
import multiprocessing


current_dir = os.path.dirname(os.path.abspath(__file__))
con = Config(base_path=current_dir, level=1)

TASKS = [
    crawler.scraper.execute,
    crawler.collector.execute,
    crawler.fetch_ip_list.execute,
    crawler.get_complete_evidence.execute,
]

EVI_FOLDER = con.EVI_FOLDER
SETTING_FOLDER = con.SETTING_FOLDER
SETTING_FILE = con.SETTING_FILE


class TaskHandler:
    def __init__(self):
        self.processes = []

    def stop_task(self):
        # 走っているプロセスを強制Kill
        for process in self.processes:
            process.terminate()

        self.processes = []

    def run_task(self, task, interval):
        while True:
            task()
            time.sleep(interval)

    def start_task(self):
        with open(SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for task in TASKS:
            # ファイル名に基づいてインターバルを取得
            if task == crawler.scraper.execute:
                interval = data["interval"]
            elif task == crawler.collector.execute:  # elifを使用して条件を修正
                interval = data["piece_interval"]
            elif task == crawler.fetch_ip_list.execute:  # elifを使用して条件を修正
                interval = 86400
            else:
                interval = data["interval"]  # デフォルトのインターバルを使用

            process = multiprocessing.Process(
                target=self.run_task, args=(task, interval)
            )
            process.start()

    def restart_task(self):
        self.stop_task()
        self.start_task()  # タスクを再開
