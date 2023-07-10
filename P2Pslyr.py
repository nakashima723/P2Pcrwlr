from datetime import datetime, timedelta, timezone
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
import os
import re
import shutil
import sys
import pathlib
import time
from torrentool.api import Torrent
from plyer import notification
import utils.time as ut
from pathlib import Path
from utils.generator import SettingsGenerator

if getattr(sys, 'frozen', False):
    # PyInstallerが使用する一時ディレクトリ
    application_path = sys._MEIPASS
else:
    application_path = Path(__file__).resolve().parent

EVIDENCE_FOLDER = os.path.join(application_path, "evi")
SETTING_FOLDER = os.path.join(application_path, "settings")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")

#設定ファイルが存在しないときは生成
settings_manager = SettingsGenerator()
settings_manager.make_setting_json()

def is_info_hash_duplicate(torrent_folder, torrent_files):
#読み込んだTorrentファイルが、すでにevidenceフォルダに存在するかどうか検証する。
# torrent_folder内の全てのサブフォルダを巡回
    for entry in os.listdir(torrent_folder):
        subfolder_path = os.path.join(torrent_folder, entry)

        if os.path.isdir(subfolder_path):
            # サブフォルダ内のファイルを一つずつ調べる
            for file in os.listdir(subfolder_path):
                if file.endswith(".torrent"):
                    existing_torrent_path = os.path.join(subfolder_path, file)
                    existing_torrent = Torrent.from_file(existing_torrent_path)
                    existing_info_hash = existing_torrent.info_hash

                    # 既存のトレントのinfo_hashと、torrent_filesリスト内の全てのファイルのinfo_hashを比較する
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

    bulk_add_button = tk.Button(button_frame, text="全年齢で追加", font=small_font)
    bulk_add_button.pack(side=tk.LEFT, padx=(10, 10))
    
    r18_bulk_add_button = tk.Button(button_frame, text="R18で追加", font=small_font)
    r18_bulk_add_button.pack(side=tk.LEFT, padx=(0, 10))

    # 選択したtorrentファイルから、証拠フォルダを生成するアクション
    mark_button = tk.Button(button_frame, text="誤検出としてマーク", font=small_font)
    mark_button.pack(side=tk.LEFT, padx=(0, 10))

    start_button = tk.Button(button_frame, text="証拠採取を開始", font=font)
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
        torrent_folder = os.path.join(EVIDENCE_FOLDER, "tor")        

        subdirs = [os.path.join(torrent_folder, folder) for folder in os.listdir(torrent_folder) if os.path.isdir(os.path.join(torrent_folder, folder))]

        if selected_tab=="false":
            subdirs = [subdir for subdir in subdirs if os.path.isfile(os.path.join(subdir, '.false'))] 
        if selected_tab=="process":
            subdirs = [subdir for subdir in subdirs if os.path.isfile(os.path.join(subdir, '.process'))] 
        if selected_tab=="completed":
            subdirs = [subdir for subdir in subdirs if os.path.isfile(os.path.join(subdir, '.comlpleted'))] 
        if selected_tab==None:
            subdirs = [subdir for subdir in subdirs if not (os.path.isfile(os.path.join(subdir, '.process')) or os.path.isfile(os.path.join(subdir, '.false')) or os.path.isfile(os.path.join(subdir, '.complete')))]


        for subdir_path in subdirs:
            # サブディレクトリがあるどうかをチェック
            if os.path.isdir(subdir_path):
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

                    with open(log_file, "r", encoding='utf-8') as file:
                        lines = file.readlines()

                    if len(lines) >= 3:
                        return lines[1].strip() + "\n" + lines[2].strip()+ "\n"
                    else:
                        return "ログファイルなし：無効な証拠フォルダです。「誤検出」に分類したあと削除してください。\n"
                    
                directory = os.path.dirname(torrent_file_path)
                torrent_situation = extract_log_lines(directory)

                match = re.search(r'\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}', folder_names[index]) 
                datetime_str = match.group().replace('_', ' ').replace('-', ':')                
                dt = datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')

                # トレントファイルに含まれる情報を表示
                info_text.insert(tk.END, f"対象ファイル名：{torrent.name if torrent.name else '不明'}\n\n")            
                info_text.insert(tk.END, f"torrent取得日時：{dt}\n")     
                info_text.insert(tk.END, f"{torrent_situation}\n")
                info_text.insert(tk.END, f"【torrentファイル内の情報】\n")
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
        torrent_folder = os.path.join(pathlib.Path(__file__).parents[0], "evi/tor")        
        subdirs = [os.path.join(torrent_folder, folder) for folder in os.listdir(torrent_folder) if os.path.isdir(os.path.join(torrent_folder, folder))]
        folder_list = [subdir for subdir in subdirs if os.path.isfile(os.path.join(subdir, '.false'))] 
        target_folder = folder_list[num]
        shutil.rmtree(target_folder)
        
        update()

    def mark_folder(listbox, text,status):
        # リストボックス「suspect_listbox」の選択された要素のインデックスを取得
        selected_indices = listbox.curselection()
        
        if selected_indices:  # 選択された要素が存在する場合
            index = selected_indices[0]
            selected_text = listbox.get(index)
        else:
            print("選択されているファイルがありません。")

        num = selected_indices[0]

        # num番目のフォルダを.falseファイルでマークする 
        torrent_folder = os.path.join(pathlib.Path(__file__).parents[0], "evi/tor")        
        subdirs = [os.path.join(torrent_folder, folder) for folder in os.listdir(torrent_folder) if os.path.isdir(os.path.join(torrent_folder, folder))]
        folder_list = [subdir for subdir in subdirs if not os.path.isfile(os.path.join(subdir, status))]
        target_folder = folder_list[num]

        if not os.path.isfile(os.path.join(target_folder, status)):
            with open(os.path.join(target_folder, status), 'w', encoding='utf-8') as false_file:
                pass

        if status == ".false":
            tab_name = "を誤検出"
        if status == ".process":
            tab_name = "の証拠採取を開始し、採取状況"

        text.config(state=tk.NORMAL) 
        text.delete(1.0, tk.END)
        text.insert(tk.END, "「"+ selected_text +"」" + tab_name + "タブに移動しました。")
        text.config(state=tk.DISABLED)

        update()

    def unmark_folder(listbox,text,status):
        # リストボックス「false_listbox」の選択された要素のインデックスを取得
        selected_indices = listbox.curselection()
        
        if selected_indices:  # 選択された要素が存在する場合
            index = selected_indices[0]
            selected_text = listbox.get(index)
        else:
            print("選択されているファイルがありません。")
            return

        num = selected_indices[0]

        # num番目のフォルダの.falseファイルを削除する
        torrent_folder = os.path.join(pathlib.Path(__file__).parents[0], "evi/tor")        
        subdirs = [os.path.join(torrent_folder, folder) for folder in os.listdir(torrent_folder) if os.path.isdir(os.path.join(torrent_folder, folder))]
        folder_list = [subdir for subdir in subdirs if os.path.isfile(os.path.join(subdir, status))] 
        target_folder = folder_list[num]

        if os.path.isfile(os.path.join(target_folder, status)):
            os.remove(os.path.join(target_folder, status))

        text.config(state=tk.NORMAL) 
        text.delete(1.0, tk.END)
        text.insert(tk.END, "「"+ selected_text +"」を証拠採取の候補タブに戻しました。")
        text.config(state=tk.DISABLED)

        update()

    def start_picking():
        message = ("証拠採取を開始します。\n\n"
                "対象のファイルがあなたの権利物であることをよく確認してください。\n"
                "誤ったファイルをダウンロードした場合、あなたが著作権侵害に問われる場合があります。\n\n"
                "本当によろしいですか？")

        user_choice = messagebox.askyesno("警告", message)
        
    def on_bulk_add_button_click(age):
    # 1. ユーザーのPCから複数の.torrentファイルを選択するためのダイアログを開く
        torrent_files = filedialog.askopenfilenames(filetypes=[("Torrentファイルを選択して追加", "*.torrent")])        
        torrent_folder = os.path.join(EVIDENCE_FOLDER, 'tor')

        if not torrent_files:
            # 6. torrentファイルが選択されていない場合は何もせずに戻る
            return
        if not is_info_hash_duplicate(EVIDENCE_FOLDER, torrent_files):
            for torrent_file in torrent_files:          
                # 2. 'folder_time'という名前の新しいフォルダを'EVIDENCE_FOLDER'内に作成する
                folder_time = ut.fetch_jst().strftime('%Y-%m-%d_%H-%M-%S')     

                folder_path = os.path.join(torrent_folder, folder_time)
                os.makedirs(folder_path, exist_ok=True)

                if age == 'r18':
                    r18_file_path = os.path.join(folder_path, ".r18")
                    with open(r18_file_path, 'w') as f:
                        pass
                
                # 3. 選択されたtorrentファイルを'folder_time'フォルダにコピーする
                dst_file_path = os.path.join(folder_path, os.path.basename(torrent_file))
                shutil.copy2(torrent_file, dst_file_path)

                # 4. コピーされたtorrentファイルの名前を'source.torrent'に変更する
                src_file_path = os.path.join(folder_path, "source.torrent")
                os.rename(dst_file_path, src_file_path)
                
                # torrentファイルの読み込み時の情報を記録
                log_file_path = os.path.join(folder_path, "evi_" + folder_time +".log")

                with open(log_file_path, "w", encoding='utf-8') as log_file:
                    torrent = Torrent.from_file(src_file_path)
                    LOG =  "対象ファイル名：" + torrent.name + "\ntorrent取得方法：ローカルに保存されたtorrentファイルから"+ "\n取得元：" + dst_file_path + "\n証拠フォルダ生成日時：" + folder_time + "\nファイルハッシュ：" + torrent.info_hash
                    log_file.write(LOG)
                time.sleep(1)
        else:      
            for torrent_file in torrent_files:      
                root = tk.Tk()
                torrent = Torrent.from_file(torrent_file)
                root.withdraw()  # メインウィンドウを隠す
                messagebox.showinfo("Alert", torrent.name+ "はすでに存在しているファイルです。")
                root.destroy()  # メインウィンドウを閉じる
        
        update()

    def combined_commands():
        start_picking()
        mark_folder(suspect_listbox, info_text, ".process")
    
    start_button.config(command=combined_commands)
    mark_button.config(command=lambda: mark_folder(suspect_listbox, info_text,".false"))
    unmark_button.config(command=lambda: unmark_folder(false_listbox, false_text,".false"))
    suspend_button.config(command=lambda: unmark_folder(process_listbox, process_text,".process"))    
    delete_button.config(command=delete_folder)
    bulk_add_button.config(command=lambda:on_bulk_add_button_click("all"))    
    r18_bulk_add_button.config(command=lambda:on_bulk_add_button_click("r18"))    
    refresh_button.config(command=update)

    update()

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()
    
if __name__ == '__main__':
    main()
