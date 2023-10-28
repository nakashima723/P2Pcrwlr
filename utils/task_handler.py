# 設定ファイル内のinterval値に応じて、指定したpythonモジュールを繰り返し実行するモジュール
# 標準ライブラリ
import json
import multiprocessing
import os
import time

# 独自モジュール
import crawler.collector
import crawler.fetch_ip_list
import crawler.get_complete_evidence
import crawler.scraper
from utils.config import Config


current_dir = os.path.dirname(os.path.abspath(__file__))
con = Config(base_path=current_dir, level=1)

# 実行対象のタスク
TASKS = [
    crawler.scraper.execute,
    crawler.collector.execute,
    crawler.fetch_ip_list.execute,
    crawler.get_complete_evidence.execute,
]

EVI_FOLDER = con.EVI_FOLDER
SETTING_FOLDER = con.SETTING_FOLDER
SETTING_FILE = con.SETTING_FILE


def wrapper_run_task(task, interval, stop_event):
    while not stop_event.is_set():
        task()
        time.sleep(interval)


class TaskHandler:
    def __init__(self):
        self.processes = []
        self.stop_event = multiprocessing.Event()  # multiprocessing.Eventを使用

    def stop_task(self):
        # 走っているプロセスを強制Kill
        self.stop_event.set()  # multiprocessing.Eventを使用

        # プロセスリストを初期状態にリセットする
        for process in self.processes:
            process.terminate()
            process.join()  # プロセスが終了するのを確認
        self.processes = []
        self.stop_event.clear()

    def run_task(self, task, interval):
        while not self.stop_event.is_set():  # multiprocessing.Eventを使用
            task()
            time.sleep(interval)

    def start_task(self):
        with open(SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for task in TASKS:
            # ファイル名に基づいてインターバルを取得
            if task == crawler.scraper.execute:
                interval = data["interval"]
            elif task == crawler.collector.execute:
                interval = data["piece_interval"]
            elif task == crawler.fetch_ip_list.execute:
                interval = 86400
            else:
                interval = data["interval"]  # デフォルトのインターバルを使用

            process = multiprocessing.Process(
                target=wrapper_run_task, args=(task, interval, self.stop_event)
            )
            process.start()
            self.processes.append(process)
