from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import os
import shutil
import pathlib
import time
import ntplib
from torrentool.api import Torrent
from plyer import notification

# 証拠ディレクトリへのパスを定義
torrent_folder = os.path.join(pathlib.Path(__file__).parents[0], "evidence/torrent")

#NTPサーバからUNIX時刻を取得し、JSTに変換して返却する。
def fetch_jst():
    ntp_server = 'ntp.nict.jp'

    # NTPサーバからUNIX時刻を取得する
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request(ntp_server)
    unix_time = response.tx_time

    # UNIX時刻をJSTに変換する
    jst = timezone(timedelta(hours=+9), 'JST')
    jst_time = datetime.fromtimestamp(unix_time, jst)

    return jst_time

def is_info_hash_duplicate(torrent_folder, torrent_files):
    # Traverse through all the subfolders in the torrent_folder
    for entry in os.listdir(torrent_folder):
        subfolder_path = os.path.join(torrent_folder, entry)

        if os.path.isdir(subfolder_path):
            # Iterate through the files in the subfolder
            for file in os.listdir(subfolder_path):
                if file.endswith(".torrent"):
                    existing_torrent_path = os.path.join(subfolder_path, file)
                    existing_torrent = Torrent.from_file(existing_torrent_path)
                    existing_info_hash = existing_torrent.info_hash

                    # Compare the existing torrent's info_hash with the info_hash of all files in the torrent_files list
                    for torrent_file in torrent_files:
                        new_torrent = Torrent.from_file(torrent_file)
                        new_info_hash = new_torrent.info_hash

                        if new_info_hash == existing_info_hash: 
                            print(f"すでに存在しているtorrentファイルです: {torrent_file}")
                            return True
    return False

def main():
    window = tk.Tk()
    window.title('P2Pスレイヤー')
    window.geometry('800x600')
    
   # フォント設定
    font = ('', 17)
    small_font = ('', 14)

    # タブのスタイルをカスタマイズ
    style = ttk.Style()
    style.configure('TNotebook.Tab', font=('TkDefaultFont', 17), padding=(15, 6, 15, 6))    
    style.configure("Large.TRadiobutton",font=font)

    # タブの追加
    notebook = ttk.Notebook(window)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text='証拠採取')    

    # パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab1, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # リストボックスを含むフレーム
    suspect_listbox_frame = tk.Frame(paned_window)
    paned_window.add(suspect_listbox_frame)

    # リストボックス
    suspect_listbox = tk.Listbox(suspect_listbox_frame, width=-1, height=9, font=small_font)
    suspect_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    suspect_scrollbar = tk.Scrollbar(suspect_listbox_frame, orient=tk.VERTICAL, command=suspect_listbox.yview)
    suspect_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    suspect_listbox.config(yscrollcommand=suspect_scrollbar.set)

    def names():
        # torrentファイルに対応するフォルダ名を格納する配列
        folder_names = []
        # 現在の表示をクリア
        suspect_listbox.delete(0, tk.END)
        # torrent_folder 内のサブディレクトリを繰り返し処理
        for subdir in os.listdir(torrent_folder):
            subdir_path = os.path.join(torrent_folder, subdir)
            
            # サブディレクトリかどうかをチェック
            if os.path.isdir(subdir_path):
                torrent_file_path = os.path.join(subdir_path, "source.torrent")
                
                # source.torrent ファイルが存在するかチェック
                if os.path.exists(torrent_file_path):
                    # Torrent オブジェクトを作成し、ファイル名を抽出
                    torrent = Torrent.from_file(torrent_file_path)
                    for file_info in torrent.files:
                        file_name = torrent.name
                    split_string = subdir_path.replace("\\", "/").split("/")
                    subdir_time = split_string[-1]
                    date_parts = subdir_time.split('_')
                    date_elements = date_parts[0].split('-')
                    time_elements = date_parts[1].split('-')
                    subdir_time = f"{date_elements[0]}-{date_elements[1]}-{date_elements[2]} {time_elements[0]}:{time_elements[1]}:{time_elements[2]}"                    
                    list_name = file_name + " - " + subdir_time
                    suspect_listbox.insert(tk.END, list_name)
                    folder_names.append(torrent_file_path)
    
        def on_select(event):
            index = suspect_listbox.curselection()[0]
            torrent_file_path = folder_names[index]

            # Torrent オブジェクトを作成
            torrent = Torrent.from_file(torrent_file_path)

            # トレントファイルに含まれる情報を表示
            info_text.config(state=tk.NORMAL)
            info_text.delete(1.0, tk.END)
            def bytes_to_mb(size_in_bytes):
                size_in_mb = size_in_bytes / (1024 * 1024)
                return round(size_in_mb, 3)
            
            # 元ファイルの取得状況を、フォルダ内のログファイルから抽出
            def extract_log_lines(torrent_file_path):
                log_file = None

                # .logファイルを検索
                for filename in os.listdir(torrent_file_path):
                    if filename.endswith(".log"):
                        log_file = os.path.join(torrent_file_path, filename)
                        break

                if log_file is None:
                    return "注：ログファイルなし：無効な証拠フォルダです。「誤検出」に分類したあと削除してください。\n"

                with open(log_file, "r") as file:
                    lines = file.readlines()

                if len(lines) >= 3:
                    return lines[1].strip() + "\n" + lines[2].strip()+ "\n"
                else:
                    return "ログファイルなし：無効な証拠フォルダです。「誤検出」に分類したあと削除してください。\n"
            directory = os.path.dirname(torrent_file_path)
            torrent_situation = extract_log_lines(directory)

            # トレントファイルに含まれる情報を表示
            info_text.insert(tk.END, f"対象ファイル名：{torrent.name if torrent.name else '不明'}\n\n")            
            info_text.insert(tk.END, f"取得日時：{subdir_time}\n")     
            info_text.insert(tk.END, f"{torrent_situation}\n")
            info_text.insert(tk.END, f"作成日時：{torrent.creation_date if torrent.creation_date else '不明'}\n")
            info_text.insert(tk.END, f"作成者：{torrent.created_by if torrent.created_by else '不明'}\n")
            info_text.insert(tk.END, f"コメント：{torrent.comment if torrent.comment else '不明'}\n") 
            info_text.insert(tk.END, f"ファイルサイズ：{bytes_to_mb(torrent.total_size) if torrent.total_size else '不明'} MB\n")
            info_text.insert(tk.END, f"ハッシュ：{torrent.info_hash if torrent.info_hash else '不明'}\n\n")            
            info_text.insert(tk.END, f"トラッカー：{', '.join([url for sublist in torrent.announce_urls for url in sublist]) if torrent.announce_urls else '不明'}\n")
            info_text.config(state=tk.DISABLED)
        
        suspect_listbox.bind("<<ListboxSelect>>", on_select)
    names()

    # テキストエリアを含むキャンバス
    info_canvas = tk.Canvas(paned_window)
    paned_window.add(info_canvas)

    # キャンバス内にテキストエリアを含むフレームを配置
    info_text_frame = tk.Frame(info_canvas)
    info_text_frame.pack(fill=tk.BOTH, expand=True)

    # テキストエリア
    info_text = tk.Text(info_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font)
    info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    info_text.insert(tk.END, "ここに選択したtorrentファイルの情報が表示されます。\n\n表示内容を見て、証拠採取を開始するかどうか決めてください。")

    # スクロールバー
    info_scrollbar = tk.Scrollbar(info_text_frame, orient=tk.VERTICAL, command=info_text.yview)
    info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    info_text.config(yscrollcommand=info_scrollbar.set, state=tk.DISABLED)

    # 編集用ボタン
    button_frame = tk.Frame(tab1)
    button_frame.pack(fill=tk.X, pady=(0, 5))

    bulk_add_button = tk.Button(button_frame, text="ファイルから追加", font=small_font)
    bulk_add_button.pack(side=tk.LEFT, padx=(10, 10))

    # 選択したtorrentファイルから、証拠フォルダを生成するアクション
    def on_bulk_add_button_click():
        # 1. Open a dialog to select multiple .torrent files from the user's PC
        torrent_files = filedialog.askopenfilenames(filetypes=[("Torrent files", "*.torrent")])

        if not torrent_files:
            # 6. If no torrent file is selected, do nothing
            return
        if not is_info_hash_duplicate(torrent_folder, torrent_files):
            for torrent_file in torrent_files:
                # 2. Create a new folder with the name 'folder_time' in the 'EVIDENCE_FOLDER_PATH'
                folder_time = fetch_jst().strftime('%Y-%m-%d_%H-%M-%S')
                folder_path = os.path.join(torrent_folder, folder_time)
                os.makedirs(folder_path, exist_ok=True)

                # 3. Copy the selected torrent file to the 'folder_time' folder
                dst_file_path = os.path.join(folder_path, os.path.basename(torrent_file))
                shutil.copy2(torrent_file, dst_file_path)

                # 4. Rename the copied torrent file to 'source.torrent'
                src_file_path = os.path.join(folder_path, "source.torrent")
                os.rename(dst_file_path, src_file_path)
                
                # torrentファイル読み込み時の情報を記録
                log_file_path = os.path.join(folder_path, "evidence_" + folder_time +".log")
                with open(log_file_path, "w") as log_file:
                    torrent = Torrent.from_file(dst_file_path)
                    LOG =  "対象ファイル名：" + torrent.name + "\ntorrent取得方法：ローカルに保存されたファイルから"+ "\n取得元：" + dst_file_path + "\n証拠フォルダ生成日時：" + folder_time + "\nファイルハッシュ：" + torrent.info_hash
                    log_file.write(LOG)
                time.sleep(1)
        else:      
            for torrent_file in torrent_files:      
                root = tk.Tk()
                torrent = Torrent.from_file(torrent_file)
                root.withdraw()  # Hide the main window
                messagebox.showinfo("Alert", torrent.name+ "はすでに存在しているファイルです。")
                root.destroy()  # Close the main window
    names()
    bulk_add_button.config(command=on_bulk_add_button_click)

    delete_button = tk.Button(button_frame, text="誤検出としてマーク", font=small_font)
    delete_button.pack(side=tk.LEFT, padx=(0, 10))

    def start_picking():
        message = ("証拠採取を開始します。\n\n"
                "対象のファイルがあなたの権利物であることをよく確認してください。\n"
                "誤ったファイルをダウンロードした場合、あなたが著作権侵害に問われる場合があります。\n\n"
                "本当によろしいですか？")

        user_choice = messagebox.askyesno("警告", message)

        if user_choice:
            notebook.select(tab2)

    start_button = tk.Button(button_frame, text="証拠採取を開始", font=font,command=start_picking)
    start_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    reflesh_button = tk.Button(button_frame, text="更新", font=small_font,command=names)
    reflesh_button.pack(side=tk.RIGHT, padx=(0, 10))    
    
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text='採取状況')

    # パネッドウィンドウの作成
    paned_window2 = ttk.PanedWindow(tab2, orient=tk.VERTICAL)
    paned_window2.pack(fill=tk.BOTH, expand=True)

    # リストボックスを含むフレーム
    tracking_listbox_frame = tk.Frame(paned_window2)
    paned_window2.add(tracking_listbox_frame)

    # リストボックス
    tracking_listbox = tk.Listbox(tracking_listbox_frame, width=-1, height=9, font=small_font)
    tracking_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    tracking_scrollbar = tk.Scrollbar(tracking_listbox_frame, orient=tk.VERTICAL, command=tracking_listbox.yview)
    tracking_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    tracking_listbox.config(yscrollcommand=tracking_scrollbar.set)

    # テキストエリアを含むキャンバス
    process_canvas = tk.Canvas(paned_window2)
    paned_window2.add(process_canvas)

    # キャンバス内にテキストエリアを含むフレームを配置
    process_text_frame = tk.Frame(process_canvas)
    process_text_frame.pack(fill=tk.BOTH, expand=True)

    # テキストエリア
    process_text = tk.Text(process_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font)
    process_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    process_text.insert(tk.END, "ここに、選択したファイルの証拠採取の進行状況が表示されます。\n\nピース収集の進捗は完全にリアルタイムではなく、フォルダ内のログファイルから読み込まれます。\n最新の状況を知りたい場合は「更新」ボタンを押してください。")

    # 編集用ボタン
    button_frame2 = tk.Frame(tab2)
    button_frame2.pack(fill=tk.X, pady=(0, 5))

    restore_button = tk.Button(button_frame2, text="証拠採取を一時停止", font=font)
    restore_button.pack(side=tk.RIGHT, padx=(0, 10))

    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text='誤検出')

    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text='統計')
    
    tab5 = ttk.Frame(notebook)
    notebook.add(tab5, text='設定')    

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()
    
if __name__ == '__main__':
    main()