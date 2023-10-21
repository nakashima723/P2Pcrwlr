# 設定ファイル内のinterval値に応じて、指定したpythonファイルを繰り返し実行するモジュール
import json
import os
import sys
import signal
import subprocess
import threading
from pathlib import Path

if getattr(sys, "frozen", False):
    # PyInstallerが使用する一時ディレクトリ
    application_path = sys._MEIPASS
else:
    application_path = Path(__file__).resolve().parent.parent

SETTING_FOLDER = os.path.join(application_path, "settings")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")


class TaskHandler:
    def __init__(self, task_files):
        if not isinstance(task_files, list):
            task_files = [task_files]

        self.task_files = task_files
        self.processes = []
        self.stop_event = threading.Event()
        self.update_label_callback = None

    def set_update_label_callback(self, callback):
        self.update_label_callback = callback

    def run_task(self, task_file, interval):
        while not self.stop_event.is_set():
            process = subprocess.Popen(
                ["python", task_file],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            # processesリストにプロセスとスレッドを保存
            self.processes.append((process, threading.current_thread()))
            process.wait()  # タスクの終了を待つ
            self.stop_event.wait(timeout=interval)  # 指定された間隔で次のタスクの実行を待つ

    def start_task(self):
        with open(SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for task_file in self.task_files:
            # フルパスからファイル名のみを取得
            file_name = os.path.basename(task_file)
            # ファイル名に基づいてインターバルを取得
            if file_name == "scraper.py":
                interval = data["interval"]
            elif file_name == "collector.py":  # elifを使用して条件を修正
                interval = data["piece_interval"]
            else:
                interval = data["interval"]  # デフォルトのインターバルを使用

            process_thread = threading.Thread(target=self.run_task, args=(task_file, interval))
            process_thread.start()

    def start_repeat_thread(self):
        self.start_task()  # start_taskメソッドを呼び出す

    def stop_repeat_thread(self):
        self.stop_event.set()

    def stop_with_timeout(self, process, timeout=3):
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == "nt":  # Windowsの場合
                process.terminate()
            else:  # Unix系のOSの場合
                process.send_signal(signal.SIGKILL)  # SIGKILLで強制終了

    def stop_task(self):
        self.stop_event.set()  # スレッドを停止

        # handlerが管理する各サブプロセスに対してstop_with_timeoutを呼び出す
        for process, process_thread in self.processes:
            self.stop_with_timeout(process) 

    def restart_task(self):
        self.stop_task()  # 既存のタスクを停止
        for _, process_thread in self.processes:
            process_thread.join()  # 各タスクの終了を待つ
        self.processes.clear()  # processリストをクリア
        self.stop_event.clear()  # stop_eventをリセット
        self.start_repeat_thread()  # タスクを再開