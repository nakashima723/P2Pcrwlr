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

# completed および false フォルダの作成
folder_types = ['completed', 'false']
for folder_type in folder_types:
    folder_path = os.path.join(torrent_folder, folder_type)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

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
    notebook.add(tab1, text='証拠採取を開始')  

    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text='採取状況')

    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text='誤検出')

    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text='完了一覧')

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

    # 候補テキストエリアのスクロールバー
    info_scrollbar = tk.Scrollbar(info_text_frame, orient=tk.VERTICAL, command=info_text.yview)
    info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    info_text.config(yscrollcommand=info_scrollbar.set, state=tk.DISABLED)
    
    # 編集用ボタン
    button_frame = tk.Frame(tab1)
    button_frame.pack(fill=tk.X, pady=(0, 5))

    bulk_add_button = tk.Button(button_frame, text="ファイルから追加", font=small_font)
    bulk_add_button.pack(side=tk.LEFT, padx=(10, 10))

    # 選択したtorrentファイルから、証拠フォルダを生成するアクション
    mark_button = tk.Button(button_frame, text="誤検出としてマーク", font=small_font)
    mark_button.pack(side=tk.LEFT, padx=(0, 10))

    def start_picking():
        message = ("証拠採取を開始します。\n\n"
                "対象のファイルがあなたの権利物であることをよく確認してください。\n"
                "誤ったファイルをダウンロードした場合、あなたが著作権侵害に問われる場合があります。\n\n"
                "本当によろしいですか？")

        user_choice = messagebox.askyesno("警告", message)

        if user_choice:
            notebook.select(tab2)

    start_button = tk.Button(button_frame, text="証拠採取を開始", font=font,command=start_picking)
    start_button.config(state=tk.DISABLED)
    start_button.pack(side=tk.RIGHT, padx=(0, 10))

    refresh_button = tk.Button(button_frame, text="更新", font=small_font)
    refresh_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    # 採集状況パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab2, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # 採集状況リストボックスを含むフレーム
    process_listbox_frame = tk.Frame(paned_window)
    paned_window.add(process_listbox_frame)

    # 採集状況リストボックス
    process_listbox = tk.Listbox(process_listbox_frame, width=-1, height=9, font=small_font)
    process_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 採集状況スクロールバー
    process_scrollbar = tk.Scrollbar(process_listbox_frame, orient=tk.VERTICAL, command=process_listbox.yview)
    process_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    process_listbox.config(yscrollcommand=process_scrollbar.set)

    # 採集状況テキストエリアを含むキャンバス
    process_canvas = tk.Canvas(paned_window)
    paned_window.add(process_canvas)

    # 採集状況キャンバス内にテキストエリアを含むフレームを配置
    process_text_frame = tk.Frame(process_canvas)
    process_text_frame.pack(fill=tk.BOTH, expand=True)

    # 採集状況テキストエリア
    process_text = tk.Text(process_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font)
    process_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    process_text.insert(tk.END, "ここに、選択したファイルの証拠採取の進行状況が表示されます。\n\n（工事中）今のところは「証拠採取を開始」タブと同じ情報が表示されます。")

    # 採集状況テキストエリアのスクロールバー
    process_scrollbar = tk.Scrollbar(process_text_frame, orient=tk.VERTICAL, command=process_text.yview)
    process_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    process_text.config(yscrollcommand=process_scrollbar.set, state=tk.DISABLED)
    
    # 採集状況の編集用ボタン
    button_frame2 = tk.Frame(tab2)
    button_frame2.pack(fill=tk.X, pady=(0, 5))

    suspend_button = tk.Button(button_frame2, text="証拠採取を一時停止", font=font)
    suspend_button.pack(side=tk.RIGHT, padx=(0, 10))

    # 誤検出パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab3, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # 誤検出リストボックスを含むフレーム
    false_listbox_frame = tk.Frame(paned_window)
    paned_window.add(false_listbox_frame)

    # 誤検出リストボックス
    false_listbox = tk.Listbox(false_listbox_frame, width=-1, height=9, font=small_font)
    false_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 誤検出スクロールバー
    suspect_scrollbar = tk.Scrollbar(false_listbox_frame, orient=tk.VERTICAL, command=false_listbox.yview)
    suspect_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    false_listbox.config(yscrollcommand=suspect_scrollbar.set)

    # 誤検出テキストエリアを含むキャンバス
    false_canvas = tk.Canvas(paned_window)
    paned_window.add(false_canvas)

    # 誤検出キャンバス内にテキストエリアを含むフレームを配置
    false_text_frame = tk.Frame(false_canvas)
    false_text_frame.pack(fill=tk.BOTH, expand=True)

    # 誤検出テキストエリア
    false_text = tk.Text(false_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font)
    false_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    false_text.insert(tk.END, "ここでは、誤検出としてマークされたtorrentファイルの一覧を確認できます。"
                      "\n\n必要に応じてフォルダを削除したり、証拠採取の候補に戻したりすることができます。"
                      "\n\n「P2Pクローラ」の検索機能から生成したフォルダを完全に削除した場合、検出履歴をクリアしない限り、"
                      "クローラで同じファイルを収集することはできなくなりますので注意してください。")
    
    # 誤検出テキストエリアのスクロールバー
    false_scrollbar = tk.Scrollbar(false_text_frame, orient=tk.VERTICAL, command=false_text.yview)
    false_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    false_text.config(yscrollcommand=false_scrollbar.set, state=tk.DISABLED)    

    # 誤検出タブの編集用ボタン
    false_button_frame = tk.Frame(tab3)
    false_button_frame.pack(fill=tk.X, pady=(0, 5))

    delete_button = tk.Button(false_button_frame, text="削除", font=small_font)
    delete_button.pack(side=tk.LEFT, padx=(10, 10)) 
    
    unmark_button = tk.Button(false_button_frame, text="証拠採取の候補にもどす", font=font)
    unmark_button.pack(side=tk.RIGHT, padx=(0, 10))

    # 完了パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab4, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # 完了リストボックスを含むフレーム
    complete_listbox_frame = tk.Frame(paned_window)
    paned_window.add(complete_listbox_frame)

    # 完了リストボックス
    complete_listbox = tk.Listbox(complete_listbox_frame, width=-1, height=9, font=small_font)
    complete_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 完了スクロールバー
    complete_scrollbar = tk.Scrollbar(complete_listbox_frame, orient=tk.VERTICAL, command=complete_listbox.yview)
    complete_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    complete_listbox.config(yscrollcommand=complete_scrollbar.set)

    # 完了テキストエリアを含むキャンバス
    complete_canvas = tk.Canvas(paned_window)
    paned_window.add(complete_canvas)

    # 完了キャンバス内にテキストエリアを含むフレームを配置
    complete_text_frame = tk.Frame(complete_canvas)
    complete_text_frame.pack(fill=tk.BOTH, expand=True)

    # 完了テキストエリア
    complete_text = tk.Text(complete_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font)
    complete_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    complete_text.insert(tk.END, "一覧からファイルを選択すると、証拠採取の結果が表示されます。"
                         "\n\n追加でより長い期間の証拠採取を行う場合は、採取候補の一覧へ戻すことができます。")
 
    # 完了テキストエリアのスクロールバー
    complete_scrollbar = tk.Scrollbar(complete_text_frame, orient=tk.VERTICAL, command=complete_text.yview)
    complete_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    complete_text.config(yscrollcommand=complete_scrollbar.set, state=tk.DISABLED)  

    # 完了タブの編集用ボタン
    complete_button_frame = tk.Frame(tab4)
    complete_button_frame.pack(fill=tk.X, pady=(0, 5))

    restart_button = tk.Button(complete_button_frame, text="追加の証拠採取を行う", font=font)
    restart_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    tab5 = ttk.Frame(notebook)
    notebook.add(tab5, text='設定')    

    def names(suspect_listbox, info_text, start_button, selected_tab=None):
        # torrentファイルに対応するフォルダ名を格納する配列
        folder_names = []
        suspect_listbox.delete(0, tk.END)
        # torrent_folder 内のサブディレクトリを繰り返し処理
        torrent_folder = os.path.join(pathlib.Path(__file__).parents[0], "evidence/torrent")
        if selected_tab=="false":
            torrent_folder = os.path.join(torrent_folder, "false")
        if selected_tab=="completed":
            torrent_folder = os.path.join(torrent_folder, "completed") 

        subdirs = [os.path.join(torrent_folder, folder) for folder in os.listdir(torrent_folder) if os.path.isdir(os.path.join(torrent_folder, folder))]

        for subdir_path in subdirs:
            # サブディレクトリがあるどうかをチェック
            if os.path.isdir(subdir_path):
                if not os.path.isdir(folder_path[0]) or os.path.isdir(folder_path[1]) :             
                    torrent_file_path = os.path.join(subdir_path, "source.torrent")
                    
                    # source.torrent ファイルが存在するかチェック
                    if os.path.exists(torrent_file_path):
                        # Torrent オブジェクトを作成し、ファイル名を抽出
                        torrent = Torrent.from_file(torrent_file_path)
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
            selected_indices = suspect_listbox.curselection()
            if selected_indices:  # 選択された要素が存在する場合
                index = selected_indices[0]                
                torrent_file_path = folder_names[index]
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
            
            selected_indices = suspect_listbox.curselection()
            if selected_indices:
                start_button.config(state=tk.NORMAL)
            else:
                start_button.config(state=tk.DISABLED)

        suspect_listbox.bind("<<ListboxSelect>>", on_select)
    
    # 表示内容を更新
    def update():
        names(complete_listbox, complete_text, restart_button, selected_tab="completed")
        names(process_listbox, process_text, suspend_button, selected_tab="process")
        names(false_listbox, false_text, unmark_button, selected_tab="false")
        names(suspect_listbox, info_text, start_button, selected_tab=None)

    def delete_folder():
        # 1. リストボックス「false_listbox」の選択された要素のインデックスを取得
        selected_indices = false_listbox.curselection()

        # 選択された要素が存在しない場合、処理を終了
        if not selected_indices:
            return

        num = selected_indices[0]

        # 2. num番目のフォルダを削除
        false_folder = os.path.join(torrent_folder, "false/")
        folder_list = [os.path.join(false_folder, d) for d in os.listdir(false_folder) if os.path.isdir(os.path.join(false_folder, d))]
        target_folder = folder_list[num]
        shutil.rmtree(target_folder)
        
        update()

    def mark_folder():
        # リストボックス「suspect_listbox」の選択された要素のインデックスを取得
        selected_indices = suspect_listbox.curselection()

        # 選択された要素が存在しない場合、処理を終了
        if not selected_indices:
            return

        num = selected_indices[0]

        if selected_indices:  # 選択された要素が存在する場合
            index = selected_indices[0]
            selected_text = suspect_listbox.get(index)
        else:
            print("選択されているファイルがありません。")

        # num番目のフォルダをfalseフォルダ内に移動する
        folder_list = [os.path.join(torrent_folder, d) for d in os.listdir(torrent_folder) if os.path.isdir(os.path.join(torrent_folder, d))]
        target_folder = folder_list[num]
        false_folder = os.path.join(torrent_folder, "false")

        # falseフォルダが存在しない場合は作成
        if not os.path.exists(false_folder):
            os.makedirs(false_folder)

        new_folder_path = os.path.join(false_folder, os.path.basename(target_folder))
        os.rename(target_folder, new_folder_path)
        info_text.config(state=tk.NORMAL) 
        info_text.delete(1.0, tk.END)
        info_text.insert(tk.END, "「"+ selected_text +"」を誤検出タブに移動しました。")
        info_text.config(state=tk.DISABLED)

        update()

    def unmark_folder():
        # リストボックス「false_listbox」の選択された要素のインデックスを取得
        selected_indices = false_listbox.curselection()
        
        if selected_indices:  # 選択された要素が存在する場合
            index = selected_indices[0]
            selected_text = false_listbox.get(index)
        else:
            print("選択されているファイルがありません。")
            return

        num = selected_indices[0]

        # falseフォルダ内にあるnum番目のフォルダを、ひとつ上の階層のフォルダに移動する
        false_folder = os.path.join(torrent_folder, "false")
        folder_list = [os.path.join(false_folder, d) for d in os.listdir(false_folder) if os.path.isdir(os.path.join(false_folder, d))]
        target_folder = folder_list[num]

        new_folder_path = os.path.join(torrent_folder, os.path.basename(target_folder))
        os.rename(target_folder, new_folder_path)

        false_text.config(state=tk.NORMAL) 
        false_text.delete(1.0, tk.END)
        false_text.insert(tk.END, "「"+ selected_text +"」を証拠採取の候補タブに戻しました。")
        false_text.config(state=tk.DISABLED)

        update()

    delete_button.config(command=delete_folder)
    mark_button.config(command=mark_folder)
    unmark_button.config(command=unmark_folder)

    update()

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
        
        update()

    bulk_add_button.config(command=on_bulk_add_button_click)    
    refresh_button.config(command=update)

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()
    
if __name__ == '__main__':
    main()