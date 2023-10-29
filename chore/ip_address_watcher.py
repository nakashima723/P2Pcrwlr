import os
import tkinter as tk
import sys
from torrent.client import _get_public_ips
from utils.time import get_jst_str

# ログファイルのパス
if getattr(sys, "frozen", False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(__file__)

log_file_path = os.path.join(application_path, "IP_address_watcher.log")

# ログファイルが存在しない場合、新規作成
if not os.path.exists(log_file_path):
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write("最終記録日時：\n")

# UIウィンドウとラベルを作成
window = tk.Tk()
window.title("IPアドレス監視ツール")
font = ("", 18)
last_recorded_time_label = tk.Label(window, text="最終記録日時：", padx=10, pady=5, font=font)
current_ipv4_label = tk.Label(window, text="", padx=20, pady=5, font=font)
current_ipv6_label = tk.Label(window, text="", padx=30, pady=5, font=font)
last_recorded_time_label.pack()
current_ipv4_label.pack()
current_ipv6_label.pack()


# ログを更新する関数
def update_log():
    current_time = get_jst_str()

    # 現在のIPアドレスを取得（IPv4とIPv6）
    ipv4, ipv6 = _get_public_ips()
    current_ipv4_label.config(text=f"IPv4: {ipv4}")
    current_ipv6_label.config(text=f"IPv6: {ipv6}")

    # ログファイルを開き、最終のIPアドレスを取得
    with open(log_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        last_record = lines[-1].strip() if len(lines) > 1 else None

    # 区切り文字で切り分けてIPアドレス部分だけを比較
    if last_record:
        _, last_ipv4, last_ipv6 = last_record.split(", ")
    else:
        last_ipv4, last_ipv6 = None, None

    if ipv4 != last_ipv4 or ipv6 != last_ipv6:
        # IPアドレスが変わった場合、新しい行に加筆
        current_record = f"{current_time}, {ipv4}, {ipv6}"
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"{current_record}\n")

    with open(log_file_path, "r+", encoding="utf-8") as f:
        lines = f.readlines()
        f.seek(0)
        f.write(f"最終記録日時：{current_time}\n")
        for line in lines[1:]:
            f.write(line)

    last_recorded_time_label.config(text=f"最終記録日時：{current_time}")


# メインループ
def main_loop():
    update_log()
    window.after(60000, main_loop)


if __name__ == "__main__":
    try:
        window.protocol("WM_DELETE_WINDOW", window.quit)
        main_loop()
        window.mainloop()
    except tk.TclError:
        print("プログラムが終了されました。")
