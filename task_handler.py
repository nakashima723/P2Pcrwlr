# 設定ファイル内のinterval値に応じて、指定したpythonファイルを繰り返し実行するモジュール
import json
import os
import signal
import subprocess
import threading
import pathlib

SETTING_FOLDER = os.path.join(pathlib.Path(__file__).parents[0], "settings")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")


class TaskHandler:
    def __init__(self, task_files):
        # task_filesがリストでない場合、リストとして処理するための変換
        if not isinstance(task_files, list):
            task_files = [task_files]

        self.task_files = task_files
        self.processes = []
        self.stop_event = threading.Event()
        self.repeat_thread = threading.Thread(target=self.repeat_function)
        self.update_label_callback = None

    def set_update_label_callback(self, callback):
        self.update_label_callback = callback

    def start_task(self):
        # すべてのタスクを開始
        for task_file in self.task_files:
            process = subprocess.Popen(
                ["python", task_file],
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            self.processes.append(process)

        # 設定ファイルからインターバルを取得
        with open(SETTING_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            interval = data["interval"]

        # インターバル中にタスクを実行
        for _ in range(interval):
            if self.stop_event.wait(timeout=1):  # 1秒待機、stop_event がセットされたら中断
                break
            if self.update_label_callback:
                self.update_label_callback()  # タスクの実行中にコールバックを呼び出す

    def stop_task(self):
        for process in self.processes:
            if process:
                if os.name == "nt":  # Windowsの場合
                    process.send_signal(signal.CTRL_C_EVENT)
                else:  # それ以外のOSの場合
                    process.send_signal(signal.SIGINT)  # SIGINT シグナルを送信
                process.wait()
        self.processes = []

    def repeat_function(self):
        while not self.stop_event.is_set():
            self.start_task()

    def start_repeat_thread(self):
        self.repeat_thread.start()

    def stop_repeat_thread(self):
        self.stop_event.set()

    def restart_task(self):
        if self.repeat_thread:
            self.stop_task()
            self.stop_repeat_thread()
            self.repeat_thread.join()  # 追加: スレッドが終了するまで待機
        self.stop_event.clear()  # 追加: stop_event をリセット
        self.repeat_thread = threading.Thread(target=self.repeat_function)
        self.repeat_thread.start()
