import libtorrent as lt
import time
import os
import threading
from tkinter import Tk, Button, Frame
from tkinter.filedialog import askopenfilename  # この行を追加


class Downloader:
    def __init__(self):
        self.running = True
        self.handle = None

    def download(self, torrent_path: str, save_path: str):
        session = lt.session({"listen_interfaces": "0.0.0.0:40576,[::]:40576"})
        session.apply_settings(
            {
                "user_agent": "μtorrent",
                "enable_dht": True,
                "enable_lsd": True,
                "enable_upnp": True,
                "enable_natpmp": True,
                "announce_to_all_trackers": True,
                "announce_to_all_tiers": True,
                "seeding_outgoing_connections": True,
                "rate_limit_ip_overhead": False,
                "peer_connect_timeout": 5,  # 例: 接続タイムアウトを5秒に設定
                "min_reconnect_time": 2,  # 例: リトライ間隔を2秒に設定
                "max_failcount": 5,  # 例: リトライ回数を5回に設定
            }
        )
        info = lt.torrent_info(torrent_path)
        self.handle = session.add_torrent({"ti": info, "save_path": save_path})

        print("ダウンロードを開始します。")

        while self.running and not self.handle.status().is_seeding:
            s = self.handle.status()
            print(
                f"ダウンロード速度: {s.download_rate / 1000} kB/s, アップロード速度: {s.upload_rate / 1000} kB/s, 進捗: {s.progress * 100:.2f}%"
            )
            time.sleep(1)

        if self.running:
            print("ダウンロードが完了しました。")
        else:
            print("ダウンロードが強制終了されました。")

    def stop(self):
        self.running = False


def main():
    root = Tk()
    root.title("Torrent Downloader")

    frame = Frame(root)
    frame.pack(padx=20, pady=20)

    downloader = Downloader()

    def choose_file():
        torrent_path = askopenfilename(filetypes=[("Torrent files", "*.torrent")])
        if torrent_path:
            save_path = os.getcwd()
            threading.Thread(
                target=downloader.download, args=(torrent_path, save_path)
            ).start()

    def stop_download():
        downloader.stop()

    Button(frame, text="ファイル選択", command=choose_file).grid(row=0, column=0, padx=10)
    Button(frame, text="強制終了", command=stop_download).grid(row=0, column=1, padx=10)

    root.mainloop()


if __name__ == "__main__":
    main()
