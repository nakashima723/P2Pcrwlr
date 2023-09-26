# 標準ライブラリ
import csv
import json
import glob
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
import time

# サードパーティライブラリ
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from torrentool.api import Torrent

# 独自モジュール
from utils.binary_matcher import PeerBinaryMatcher
from utils.task_handler import TaskHandler
import utils.time as ut
from utils.generator import SettingsGenerator, QueryGenerator


if getattr(sys, "frozen", False):
    # PyInstallerが使用する一時ディレクトリ
    application_path = sys._MEIPASS
else:
    application_path = Path(__file__).resolve().parent

EVIDENCE_FOLDER = os.path.join(application_path, "evi")
SETTING_FOLDER = os.path.join(application_path, "settings")
SETTING_FILE = os.path.join(SETTING_FOLDER, "setting.json")
SCRAPER_FILE = os.path.join(application_path, "crawler/scraper.py")
COLLECTOR_FILE = os.path.join(application_path, "crawler/collector.py")

# 設定ファイルが存在しないときは生成
settings_manager = SettingsGenerator()
settings_manager.make_setting_json()
query_manager = QueryGenerator("queries.json")
query_manager.make_query_json()
r18query_manager = QueryGenerator("r18queries.json")
r18query_manager.make_query_json()

task_files = [SCRAPER_FILE, COLLECTOR_FILE]

handler = TaskHandler(task_files)
handler.start_repeat_thread()


def main():
    window = tk.Tk()
    window.title("P2Pクローラ")
    window.geometry("800x600")

    def on_window_close():
        handler.stop_event.set()  # スレッドを停止

        # handlerが管理する各サブプロセスに対してstop_with_timeoutを呼び出す
        for process in handler.processes:
            handler.stop_with_timeout(process)

        window.quit()  # ウィンドウを閉じる

    # フォント設定
    font = ("", 17)
    small_font = ("", 14)
    tiny_font = ("", 11)

    # タブのスタイルをカスタマイズ
    style = ttk.Style()
    style.configure("TNotebook.Tab", font=("TkDefaultFont", 17), padding=(15, 6, 15, 6))
    style.configure("Large.TRadiobutton", font=font)

    # タブの追加
    notebook = ttk.Notebook(window)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab0 = ttk.Frame(notebook)
    notebook.add(tab0, text="Torrent収集")

    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text="証拠採取を開始")

    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text="採取中")

    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text="完了一覧")

    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text="誤検出")

    tab5 = ttk.Frame(notebook)
    notebook.add(tab5, text="設定")

    # メール通知の設定欄
    mail_frame = tk.Frame(tab5)
    mail_frame.pack(fill=tk.X, pady=(30, 0))

    mail_label = tk.Label(mail_frame, text="通知先アドレス：", font=font)
    mail_label.pack(side=tk.LEFT, padx=(80, 10))

    mail_entry = tk.Entry(mail_frame, font=font, insertwidth=3)
    mail_entry.pack(side=tk.LEFT, fill=tk.X, padx=(0, 80), expand=True)

    pass_frame = tk.Frame(tab5)
    pass_frame.pack(fill=tk.X, pady=(10, 0))

    pass_label = tk.Label(pass_frame, text="アプリパスワード：", font=font)
    pass_label.pack(side=tk.LEFT, padx=(80, 10))

    pass_entry = tk.Entry(pass_frame, font=font, insertwidth=3)
    pass_entry.pack(side=tk.LEFT, fill=tk.X, padx=(0, 20), expand=True)

    piece_interval_frame = tk.Frame(tab5)
    piece_interval_frame.pack(pady=(40, 10))

    piece_interval_label = tk.Label(piece_interval_frame, text="ピース収集の間隔：", font=font)
    piece_interval_label.pack(side=tk.LEFT, padx=(0, 10))

    piece_interval_var = tk.StringVar()

    # 巡回の間隔
    interval_frame = tk.Frame(tab0)
    interval_frame.pack(pady=(10, 10))

    interval_label = tk.Label(interval_frame, text="巡回の間隔", font=font)
    interval_label.pack(side=tk.LEFT, padx=(50, 10))

    options_list = [
        ("1分", 60),
        ("3分", 180),
        ("5分", 300),
        ("10分", 600),
        ("20分", 1200),
        ("30分", 1800),
        ("1時間", 3600),
        ("2時間", 7200),
        ("4時間", 14400),
        ("6時間", 21600),
    ]

    interval_options = options_list[:]
    piece_interval_options = options_list[:]

    interval_var = tk.StringVar()

    # intervalとメール設定の値を設定ファイルから読み込み
    with open(SETTING_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    mail_user = data["mail_user"]
    mail_pass = data["mail_pass"]

    interval_value = data["interval"]
    piece_interval_value = data["piece_interval"]

    # メール設定欄に、現在の設定ファイルの値を設定
    mail_entry.insert(0, mail_user)
    pass_entry.insert(0, mail_pass)

    for option, value in interval_options:
        if value == interval_value:
            interval_var.set(option)
            break

    for option, value in piece_interval_options:
        if value == piece_interval_value:
            piece_interval_var.set(option)
            break

    if data["last_crawl_time"] is not None and data["last_crawl_time"] != "null":
        try:
            jst = ut.fetch_jst()
        except ut.TimeException:
            jst = ut.utc_to_jst(datetime.now())
        time_str = jst.strftime("%Y年%m月%d日 %H時%M分%S秒")
    else:
        time_str = "未登録"

    last_crawl_time_str = tk.StringVar()
    last_crawl_time_str.set("最後に巡回した日時：" + str(time_str))

    def on_option_changed(event, var, options):
        selected_option = var.get()
        for option, value in options:
            if selected_option == option:
                # JSONファイルを読み込む
                with open(SETTING_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # intervalの値を更新
                data["interval"] = value

                # ファイルを書き込みモードで開いて、更新されたデータを書き込む
                with open(SETTING_FILE, "w", encoding="utf-8") as f:
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=2)

                break

    interval_menu = ttk.Combobox(
        interval_frame,
        textvariable=interval_var,
        values=[option for option, value in interval_options],
        width=6,
        font=font,
    )

    piece_interval_menu = ttk.Combobox(
        piece_interval_frame,
        textvariable=piece_interval_var,
        values=[option for option, value in piece_interval_options],
        width=6,
        font=font,
    )

    interval_menu.bind(
        "<<ComboboxSelected>>",
        lambda event, var=interval_var, options=interval_options: on_option_changed(
            event, var, options
        ),
    )
    interval_menu.pack(side=tk.LEFT, padx=(0, 10))
    piece_interval_menu.pack(side=tk.LEFT, padx=(0, 10))

    crawl_history_frame = tk.Frame(tab0)
    crawl_history_frame.pack(pady=(10, 10))

    crawl_history = tk.Label(
        crawl_history_frame, textvariable=last_crawl_time_str, font=small_font
    )
    crawl_history.pack(side=tk.LEFT, padx=(0, 5))

    def get_last_crawl_time():
        with open(SETTING_FILE, "r") as json_file:
            data = json.load(json_file)
        last_crawl_time = data.get("last_crawl_time", None)
        if last_crawl_time is not None or "null":
            jst = datetime.fromtimestamp(last_crawl_time)
            time_str = jst.strftime("%Y年%m月%d日 %H時%M分%S秒")
        else:
            time_str = "未登録"
        return "最後に巡回した日時：" + str(time_str)

    def update_label():
        last_crawl_time_str.set(get_last_crawl_time())

    def combined_actions():
        handler.set_update_label_callback(update_label)
        handler.restart_task()

    patrol_button = tk.Button(
        interval_frame, text="いますぐ巡回", font=font, command=combined_actions
    )
    patrol_button.pack(side=tk.RIGHT, padx=(30, 0))

    # 新しい検索語を追加
    keyword_entry_frame = tk.Frame(tab0)
    keyword_entry_frame.pack(fill=tk.X, pady=(10, 0))

    new_keyword_label = tk.Label(keyword_entry_frame, text="新しい検索語：", font=font)
    new_keyword_label.pack(side=tk.LEFT, padx=(80, 10))

    keyword_entry = tk.Entry(keyword_entry_frame, font=font, insertwidth=3)
    keyword_entry.pack(side=tk.LEFT, fill=tk.X, padx=(0, 10), expand=True)

    add_button = tk.Button(keyword_entry_frame, text="追加", font=font)
    add_button.pack(side=tk.LEFT, padx=(0, 100))

    option_entry_frame = tk.Frame(tab0)
    option_entry_frame.pack(
        fill=tk.X,
        pady=(10, 5),
    )

    creator_label = tk.Label(option_entry_frame, text="作者：", font=small_font)
    creator_label.pack(side=tk.LEFT, padx=(140, 0))

    entry_width = 15  # 両方のEntryウィジェットの横幅を設定

    creator_entry = tk.Entry(
        option_entry_frame, font=font, insertwidth=3, width=entry_width
    )
    creator_entry.pack(side=tk.LEFT, padx=(0, 10))

    publisher_label = tk.Label(option_entry_frame, text="版元：", font=small_font)
    publisher_label.pack(side=tk.LEFT, padx=(10, 0))

    publisher_entry = tk.Entry(
        option_entry_frame, font=font, insertwidth=3, width=entry_width
    )
    publisher_entry.pack(side=tk.LEFT, padx=(0, 100))

    url_frame = tk.Frame(tab0)
    url_frame.pack(
        fill=tk.X,
        pady=(10, 5),
    )

    url_label = tk.Label(url_frame, text="参考URL：", font=small_font)
    url_label.pack(side=tk.LEFT, padx=(95, 10))

    url_entry = tk.Entry(url_frame, font=font, insertwidth=3)
    url_entry.pack(side=tk.LEFT, fill=tk.X, padx=(0, 160), expand=True)

    # ラジオボタン
    radio_frame = tk.Frame(tab0)
    radio_frame.pack(pady=(10, 5))

    radio_var = tk.StringVar()
    radio_var.set("全年齢")

    radio_all = ttk.Radiobutton(
        radio_frame,
        text="全年齢",
        value="全年齢",
        variable=radio_var,
        style="Large.TRadiobutton",
    )
    radio_all.pack(side=tk.LEFT, padx=(0, 5))

    radio_adult = ttk.Radiobutton(
        radio_frame,
        text="成人向け",
        value="成人向け",
        variable=radio_var,
        style="Large.TRadiobutton",
    )
    radio_adult.pack(side=tk.LEFT)

    # 空白
    spacer = tk.Frame(tab0, height=30)
    spacer.pack(fill=tk.X, expand=False)

    # tab0内に新しいタブを追加
    nested_notebook = ttk.Notebook(tab0)
    nested_notebook.pack(fill=tk.BOTH, expand=True)

    crawl_history_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(crawl_history_tab, text="履歴")

    # 検出履歴を含むフレーム
    history_frame = tk.Frame(crawl_history_tab)
    history_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # 検出履歴
    crawl_history = tk.Text(history_frame, width=-1, height=7, font=small_font)
    crawl_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    scrollbar = tk.Scrollbar(
        history_frame, orient=tk.VERTICAL, command=crawl_history.yview
    )
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    crawl_history.config(yscrollcommand=scrollbar.set)

    # サイズ変更用ウィジェット
    sizegrip = ttk.Sizegrip(crawl_history_tab)
    sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    sizegrip.lift(aboveThis=history_frame)

    all_age_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(all_age_tab, text="検索語（全年齢）")

    button_frame = tk.Frame(all_age_tab)
    button_frame.pack(fill=tk.X, pady=(0, 5))

    delete_button = tk.Button(button_frame, text="削除", font=small_font)
    delete_button.pack(side=tk.LEFT, padx=(10, 0))

    bulk_add_button = tk.Button(button_frame, text="ファイルからまとめて追加", font=small_font)
    bulk_add_button.pack(side=tk.RIGHT, padx=(0, 10))

    edit_button = tk.Button(button_frame, text="編集する", font=small_font)
    edit_button.pack(side=tk.RIGHT, padx=(0, 10))

    # Treeviewを含むフレーム
    all_age_frame = tk.Frame(all_age_tab)
    all_age_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # Treeviewの作成
    treeview = ttk.Treeview(
        all_age_frame,
        columns=("検索語", "作者", "版元", "参考"),
        show="headings",
        selectmode="browse",
    )
    treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバーの追加
    scrollbar = ttk.Scrollbar(all_age_frame, orient=tk.VERTICAL, command=treeview.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    treeview.configure(yscrollcommand=scrollbar.set)

    style = ttk.Style()
    style.configure("Treeview", font=small_font)

    r18_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(r18_tab, text="検索語（成人向け）")

    # リストボックスを含むフレーム
    r18_button_frame = tk.Frame(r18_tab)
    r18_button_frame.pack(fill=tk.X, pady=(0, 5))

    r18_delete_button = tk.Button(r18_button_frame, text="削除", font=small_font)
    r18_delete_button.pack(side=tk.LEFT, padx=(10, 0))

    r18_bulk_add_button = tk.Button(
        r18_button_frame, text="ファイルからまとめて追加", font=small_font
    )
    r18_bulk_add_button.pack(side=tk.RIGHT, padx=(0, 10))

    r18_edit_button = tk.Button(r18_button_frame, text="編集する", font=small_font)
    r18_edit_button.pack(side=tk.RIGHT, padx=(0, 10))

    r18_frame = tk.Frame(r18_tab)
    r18_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # Treeviewの作成
    r18treeview = ttk.Treeview(
        r18_frame,
        columns=("検索語", "作者", "版元", "参考"),
        show="headings",
        selectmode="browse",
    )
    r18treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバーの追加
    scrollbar = ttk.Scrollbar(r18_frame, orient=tk.VERTICAL, command=treeview.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    r18treeview.configure(yscrollcommand=scrollbar.set)

    # サイズ変更用ウィジェット
    r18_sizegrip = ttk.Sizegrip(r18_tab)
    r18_sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    r18_sizegrip.lift(aboveThis=r18_frame)

    style = ttk.Style()
    style.configure("Treeview", font=small_font)
    style.configure("Treeview.Heading", font=tiny_font)

    # カラムの設定
    def treeview_set(treeview):
        treeview.heading("検索語", text="検索語")
        treeview.column("検索語", width=200)

        treeview.heading("作者", text="作者")
        treeview.column("作者", width=60)

        treeview.heading("版元", text="版元")
        treeview.column("版元", width=60)

        treeview.heading("参考", text="参考URL")
        treeview.column("参考", width=180)

    def load_queries(filename):
        settings_file = os.path.join(SETTING_FOLDER, filename)

        if not os.path.exists(settings_file):
            with open(settings_file, "w", encoding="utf-8") as f:
                f.write("[]")  # 空のリストをJSON形式で書き込む

        if os.path.exists(settings_file) and os.path.getsize(settings_file) > 0:
            with open(settings_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
        else:
            saved_data = []

        return saved_data

    def populate_treeview(treeview, data):
        # Treeviewの内容をクリア
        for item in treeview.get_children():
            treeview.delete(item)

        # 新しいデータをTreeviewに追加
        for item in data:
            treeview.insert("", "end", values=item)

    def save_data():
        # 入力されたデータを取得
        keyword = keyword_entry.get()
        keyword = keyword.strip()  # 文頭のスペースを削除
        keyword = re.sub(r"\s{2,}", " ", keyword)  # 2つ以上連続しているスペースを1つにする
        keyword = keyword.replace("　", "")  # 全角スペースを削除
        if not keyword:
            messagebox.showerror("エラー", "検索語が入力されていません。")
            edit_button.config(text="編集する", font=small_font)
            return
        creator = creator_entry.get().replace(" ", "").replace("　", "")
        publisher = publisher_entry.get().replace(" ", "").replace("　", "")
        url = url_entry.get().replace(" ", "").replace("　", "")
        if url and not url.startswith("https://"):
            messagebox.showerror("エラー", "「参考URL」に入力された値はURLではありません。")
            edit_button.config(text="編集する", font=small_font)
            return

        age_rating = radio_var.get()

        if age_rating == "全年齢":
            nested_notebook.select(all_age_tab)
        if age_rating == "成人向け":
            nested_notebook.select(r18_tab)

        # 新しいデータをタプルとして作成
        new_data = (keyword, creator, publisher, url)

        # 保存先ファイル名をラジオボタンの値に基づいて設定
        if age_rating == "全年齢":
            settings_file = os.path.join(SETTING_FOLDER, "queries.json")
        else:
            settings_file = os.path.join(SETTING_FOLDER, "r18queries.json")

        # データを読み込み、新しいデータを追加
        if os.path.exists(settings_file) and os.path.getsize(settings_file) > 0:
            with open(settings_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)
        else:
            saved_data = []

        # Check if the keyword already exists in the saved_data
        for data_row in saved_data:
            if data_row[0] == keyword:
                messagebox.showinfo("情報", f"検索語「{keyword}」はすでに追加済みです。")
                return

        saved_data.insert(0, new_data)

        # データをファイルに保存
        with open(settings_file, "w", encoding="utf-8") as f:
            json.dump(saved_data, f, ensure_ascii=False, indent=2)

        # 入力領域をクリア
        keyword_entry.delete(0, tk.END)
        creator_entry.delete(0, tk.END)
        publisher_entry.delete(0, tk.END)
        url_entry.delete(0, tk.END)

        crawl_history.configure(state=tk.NORMAL)  # テキストエリアを編集可能にする
        crawl_history.insert(
            "1.0", "「" + keyword + "」を" + age_rating + "の検索語として追加しました。\n"
        )  # 文字列を一番上の行に挿入
        crawl_history.configure(state=tk.DISABLED)  # テキストエリアを再びreadonlyにする

        queries_data = load_queries("queries.json")
        r18queries_data = load_queries("r18queries.json")
        populate_treeview(treeview, queries_data)
        populate_treeview(r18treeview, r18queries_data)
        edit_button.config(text="編集する", font=small_font)
        r18_edit_button.config(text="編集する", font=small_font)

    # クエリ表示タブの削除ボタンのコマンド
    def delete_selected_item(treeview, json_file_name):
        selected_items = treeview.selection()
        json_file_path = os.path.join(SETTING_FOLDER, json_file_name)

        if not selected_items:
            edit_button.config(text="編集する", font=small_font)
            r18_edit_button.config(text="編集する", font=small_font)
            return

        selected_values = [treeview.item(item, "values") for item in selected_items]

        # Treeviewから選択されたアイテムを削除
        for item in selected_items:
            treeview.delete(item)

        # JSONファイルからデータを読み込み、選択されたアイテムを削除
        with open(json_file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 選択されたアイテムを削除
        data = [item for item in data if tuple(item) not in selected_values]

        # JSONファイルを更新
        with open(json_file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        first_values = [value[0] for value in selected_values]
        formatted_values = ["「{}」".format(value) for value in first_values]
        result = "".join(formatted_values)

        # 履歴を更新
        crawl_history.configure(state=tk.NORMAL)  # テキストエリアを編集可能にする
        crawl_history.insert("1.0", "検索語" + result + "を削除しました。\n")  # 文字列を一番上の行に挿入
        crawl_history.configure(state=tk.DISABLED)  # テキストエリアを再びreadonlyにする

    def query_edit(edit_button, treeview, json_file_name):
        selected_item = treeview.selection()

        if not selected_item:
            return

        item_values = treeview.item(selected_item[0], "values")

        keyword_entry.delete(0, tk.END)
        keyword_entry.insert(0, item_values[0])

        creator_entry.delete(0, tk.END)
        creator_entry.insert(0, item_values[1])

        publisher_entry.delete(0, tk.END)
        publisher_entry.insert(0, item_values[2])

        url_entry.delete(0, tk.END)
        url_entry.insert(0, item_values[3])
        edit_button.config(text="↑編集後、『追加』ボタンを押してください")
        delete_selected_item(treeview, json_file_name)

    def process_input_file(input_file):
        processed_data = []
        empty_url = 0

        with open(input_file, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) == 0 or row[0].strip() == "":
                    continue
                row += [""] * (4 - len(row))
                keyword = row[0].strip()
                keyword = re.sub(r"\s{2,}", " ", keyword)
                keyword = keyword.replace("　", " ")
                row[0] = keyword
                creator = row[1].strip().replace(" ", "").replace("　", "")
                row[1] = creator
                publisher = row[2].strip().replace(" ", "").replace("　", "")
                row[2] = publisher
                url = row[3].strip().replace(" ", "").replace("　", "")
                if not url or url is None or not url.startswith("https://"):
                    url = ""
                    if "empty_url" not in locals():
                        empty_url = 0
                row[3] = url
                processed_data.append(row)
        return processed_data, empty_url

    def update_json_file(json_file, input_data):
        added_count = 0
        duplicated_keywords = []
        saved_data = []

        with open(json_file, "r", encoding="utf-8", errors="replace") as f:
            saved_data = json.load(f)

        added_count = 0
        duplicated_keywords = []
        for row in input_data:
            keyword = row[0]
            if any(saved_row[0] == keyword for saved_row in saved_data):
                duplicated_keywords.append(keyword)
            else:
                saved_data.append(row)
                added_count += 1

        with open(json_file, "w", encoding="utf-8", errors="replace") as f:
            json.dump(saved_data, f, ensure_ascii=False, indent=2)

        return added_count, duplicated_keywords

    def import_data_to_json(json_file):
        json_file_path = os.path.join(SETTING_FOLDER, json_file)

        messagebox.showinfo(
            "ファイルから検索語を追加",
            "以下のような形式で記述された.txt、または.csvファイルを選んでください。"
            "\n1行ごとに1つの検索語を登録できます。"
            "\n\n　検索語1,　作者1,　版元1,　参考URL1\n　検索語2,　作者2,　版元2,　参考URL2\n　検索語3,　作者3,　版元3,　参考URL3"
            "\n\n「検索語」以外の要素は無くてもかまいません。",
        )

        input_file = filedialog.askopenfilename(
            filetypes=[("Text files", "*.txt;*.csv")]
        )
        if not input_file:
            return

        input_data, empty_url = process_input_file(input_file)
        added_count, duplicated_keywords = update_json_file(json_file_path, input_data)

        # 入力結果を表示
        file_input_str = ""
        if not added_count or "added_count" not in locals():
            file_input_str = "ファイル内容が不正、またはすべての検索語がすでに入力ずみのものだったため、新しく追加された検索語はありません。"
            messagebox.showinfo("入力を行いませんでした", file_input_str)
            return
        else:
            file_input_str = f"{added_count}件の検索語を入力しました。"

        if "duplicated_keywords" in locals() and duplicated_keywords:
            file_input_str += (
                f"\n\n検索語「{'」「'.join(duplicated_keywords)}」はすでに存在していたため、入力しませんでした。"
            )

        if "empty_url" in locals() and empty_url:
            file_input_str += (
                f"\n\n{empty_url}件のURLについて、「https://」から始まる内容ではなかったため、入力内容から除外しました。"
            )

        messagebox.showinfo("入力結果", file_input_str)

        queries_data = load_queries("queries.json")
        r18queries_data = load_queries("r18queries.json")
        populate_treeview(treeview, queries_data)
        populate_treeview(r18treeview, r18queries_data)

    # メール通知設定を更新するボタンの関数
    def save_mail_settings():
        # エントリウィジェットから値を取得
        mail_user = mail_entry.get()
        mail_password = pass_entry.get()

        # 設定を読み込む
        with open(SETTING_FILE, "r") as f:
            settings = json.load(f)

        # 設定を更新
        settings["mail_user"] = mail_user
        settings["mail_pass"] = mail_password

        # 設定を保存
        with open(SETTING_FILE, "w") as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)

    # ボタンに関数を紐付け
    mail_set_button = tk.Button(
        pass_frame, text="更新", font=font, command=save_mail_settings
    )
    mail_set_button.pack(side=tk.LEFT, padx=(0, 100))

    # データを読み込み、各Treeviewに表示
    queries_data = load_queries("queries.json")
    r18queries_data = load_queries("r18queries.json")
    populate_treeview(treeview, queries_data)
    populate_treeview(r18treeview, r18queries_data)
    treeview_set(treeview)
    treeview_set(r18treeview)

    # クエリ表示タブのボタン類にコマンドを設定
    edit_button.config(
        command=lambda: query_edit(edit_button, treeview, "queries.json")
    )
    r18_edit_button.config(
        command=lambda: query_edit(r18_edit_button, r18treeview, "r18queries.json")
    )
    delete_button.config(command=lambda: delete_selected_item(treeview, "queries.json"))
    r18_delete_button.config(
        command=lambda: delete_selected_item(r18treeview, "r18queries.json")
    )
    bulk_add_button.config(command=lambda: import_data_to_json("queries.json"))
    r18_bulk_add_button.config(command=lambda: import_data_to_json("r18queries.json"))

    # クエリ追加ボタンのコマンドを設定
    add_button.config(command=save_data)

    # ここからピースダウンロード関連
    # パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab1, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # リストボックスを含むフレーム
    suspect_listbox_frame = tk.Frame(paned_window)
    paned_window.add(suspect_listbox_frame)

    # リストボックス
    suspect_listbox = tk.Listbox(
        suspect_listbox_frame, width=-1, height=9, font=small_font
    )
    suspect_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    suspect_scrollbar = tk.Scrollbar(
        suspect_listbox_frame, orient=tk.VERTICAL, command=suspect_listbox.yview
    )
    suspect_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    suspect_listbox.config(yscrollcommand=suspect_scrollbar.set)

    # テキストエリアを含むキャンバス
    info_canvas = tk.Canvas(paned_window)
    paned_window.add(info_canvas)

    # キャンバス内にテキストエリアを含むフレームを配置
    info_text_frame = tk.Frame(info_canvas)
    info_text_frame.pack(fill=tk.BOTH, expand=True)

    # テキストエリア
    info_text = tk.Text(
        info_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font
    )
    info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    info_text.insert(
        tk.END, "ここに選択したtorrentファイルの情報が表示されます。\n\n表示内容を見て、証拠採取を開始するかどうか決めてください。"
    )

    # 候補テキストエリアのスクロールバー
    info_scrollbar = tk.Scrollbar(
        info_text_frame, orient=tk.VERTICAL, command=info_text.yview
    )
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

    refresh_button1 = tk.Button(button_frame, text="更新", font=small_font)
    refresh_button1.pack(side=tk.RIGHT, padx=(0, 10))

    # 採集状況パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab2, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # 採集状況リストボックスを含むフレーム
    process_listbox_frame = tk.Frame(paned_window)
    paned_window.add(process_listbox_frame)

    # 採集状況リストボックス
    process_listbox = tk.Listbox(
        process_listbox_frame, width=-1, height=9, font=small_font
    )
    process_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 採集状況スクロールバー
    process_scrollbar = tk.Scrollbar(
        process_listbox_frame, orient=tk.VERTICAL, command=process_listbox.yview
    )
    process_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    process_listbox.config(yscrollcommand=process_scrollbar.set)

    # 採集状況テキストエリアを含むキャンバス
    process_canvas = tk.Canvas(paned_window)
    paned_window.add(process_canvas)

    # 採集状況キャンバス内にテキストエリアを含むフレームを配置
    process_text_frame = tk.Frame(process_canvas)
    process_text_frame.pack(fill=tk.BOTH, expand=True)

    # 採集状況テキストエリア
    process_text = tk.Text(
        process_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font
    )
    process_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    process_text.insert(
        tk.END, "ここに、選択したファイルの証拠採取の進行状況が表示されます。\n\n（工事中）今のところは「証拠採取を開始」タブと同じ情報が表示されます。"
    )

    # 採集状況テキストエリアのスクロールバー
    process_scrollbar = tk.Scrollbar(
        process_text_frame, orient=tk.VERTICAL, command=process_text.yview
    )
    process_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    process_text.config(yscrollcommand=process_scrollbar.set, state=tk.DISABLED)

    # 採集状況の編集用ボタン
    button_frame2 = tk.Frame(tab2)
    button_frame2.pack(fill=tk.X, pady=(0, 5))

    suspend_button = tk.Button(button_frame2, text="一時停止", font=small_font)
    suspend_button.pack(side=tk.LEFT, padx=(10, 0))

    complete_button = tk.Button(button_frame2, text="証拠採取を完了", font=font)
    complete_button.pack(side=tk.RIGHT, padx=(0, 10))

    refresh_button2 = tk.Button(button_frame2, text="更新", font=small_font)
    refresh_button2.pack(side=tk.RIGHT, padx=(0, 10))

    # 誤検出パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab4, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # 誤検出リストボックスを含むフレーム
    false_listbox_frame = tk.Frame(paned_window)
    paned_window.add(false_listbox_frame)

    # 誤検出リストボックス
    false_listbox = tk.Listbox(false_listbox_frame, width=-1, height=9, font=small_font)
    false_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 誤検出スクロールバー
    suspect_scrollbar = tk.Scrollbar(
        false_listbox_frame, orient=tk.VERTICAL, command=false_listbox.yview
    )
    suspect_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    false_listbox.config(yscrollcommand=suspect_scrollbar.set)

    # 誤検出テキストエリアを含むキャンバス
    false_canvas = tk.Canvas(paned_window)
    paned_window.add(false_canvas)

    # 誤検出キャンバス内にテキストエリアを含むフレームを配置
    false_text_frame = tk.Frame(false_canvas)
    false_text_frame.pack(fill=tk.BOTH, expand=True)

    # 誤検出テキストエリア
    false_text = tk.Text(
        false_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font
    )
    false_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    false_text.insert(
        tk.END,
        "ここでは、誤検出としてマークされたtorrentファイルの一覧を確認できます。"
        "\n\n必要に応じてフォルダを削除したり、証拠採取の候補に戻したりすることができます。"
        "\n\n「P2Pクローラ」の検索機能から生成したフォルダを完全に削除した場合、検出履歴をクリアしない限り、"
        "クローラで同じファイルを収集することはできなくなりますので注意してください。",
    )

    # 誤検出テキストエリアのスクロールバー
    false_scrollbar = tk.Scrollbar(
        false_text_frame, orient=tk.VERTICAL, command=false_text.yview
    )
    false_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    false_text.config(yscrollcommand=false_scrollbar.set, state=tk.DISABLED)

    # 誤検出タブの編集用ボタン
    false_button_frame = tk.Frame(tab4)
    false_button_frame.pack(fill=tk.X, pady=(0, 5))

    delete_button = tk.Button(false_button_frame, text="削除", font=small_font)
    delete_button.pack(side=tk.LEFT, padx=(10, 10))

    unmark_button = tk.Button(false_button_frame, text="証拠採取の候補にもどす", font=font)
    unmark_button.pack(side=tk.RIGHT, padx=(0, 10))

    refresh_button3 = tk.Button(false_button_frame, text="更新", font=small_font)
    refresh_button3.pack(side=tk.RIGHT, padx=(0, 10))

    # 完了パネッドウィンドウの作成
    paned_window = ttk.PanedWindow(tab3, orient=tk.VERTICAL)
    paned_window.pack(fill=tk.BOTH, expand=True)

    # 完了リストボックスを含むフレーム
    complete_listbox_frame = tk.Frame(paned_window)
    paned_window.add(complete_listbox_frame)

    # 完了リストボックス
    complete_listbox = tk.Listbox(
        complete_listbox_frame, width=-1, height=9, font=small_font
    )
    complete_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # 完了スクロールバー
    complete_scrollbar = tk.Scrollbar(
        complete_listbox_frame, orient=tk.VERTICAL, command=complete_listbox.yview
    )
    complete_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    complete_listbox.config(yscrollcommand=complete_scrollbar.set)

    # 完了テキストエリアを含むキャンバス
    complete_canvas = tk.Canvas(paned_window)
    paned_window.add(complete_canvas)

    # 完了キャンバス内にテキストエリアを含むフレームを配置
    complete_text_frame = tk.Frame(complete_canvas)
    complete_text_frame.pack(fill=tk.BOTH, expand=True)

    # 完了テキストエリア
    complete_text = tk.Text(
        complete_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font
    )
    complete_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    complete_text.insert(
        tk.END,
        "一覧からファイルを選択すると、証拠採取の結果が表示されます。" "\n\n追加でより長期の証拠採取を行う場合は、採取候補の一覧へ戻すことができます。",
    )

    # 完了テキストエリアのスクロールバー
    complete_scrollbar = tk.Scrollbar(
        complete_text_frame, orient=tk.VERTICAL, command=complete_text.yview
    )
    complete_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    complete_text.config(yscrollcommand=complete_scrollbar.set, state=tk.DISABLED)

    # 完了タブの編集用ボタン
    complete_button_frame = tk.Frame(tab3)
    complete_button_frame.pack(fill=tk.X, pady=(0, 5))

    restart_button = tk.Button(complete_button_frame, text="追加の証拠採取を行う", font=font)
    restart_button.pack(side=tk.RIGHT, padx=(0, 10))

    refresh_button4 = tk.Button(complete_button_frame, text="更新", font=small_font)
    refresh_button4.pack(side=tk.RIGHT, padx=(0, 10))

    def names(suspect_listbox, info_text, start_button, selected_tab=None):
        # torrentファイルに対応するフォルダ名を格納する配列
        folder_names = []
        suspect_listbox.delete(0, tk.END)
        # torrent_folder 内のサブディレクトリを繰り返し処理
        torrent_folder = os.path.join(EVIDENCE_FOLDER, "tor")

        subdirs = [
            os.path.join(torrent_folder, folder)
            for folder in os.listdir(torrent_folder)
            if os.path.isdir(os.path.join(torrent_folder, folder))
        ]

        if selected_tab == "false":
            subdirs = [
                subdir
                for subdir in subdirs
                if os.path.isfile(os.path.join(subdir, ".false"))
            ]
        if selected_tab == "process":
            subdirs = [
                subdir
                for subdir in subdirs
                if os.path.isfile(os.path.join(subdir, ".process"))
            ]
        if selected_tab == "complete":
            subdirs = [
                subdir
                for subdir in subdirs
                if os.path.isfile(os.path.join(subdir, ".complete"))
            ]
        if selected_tab is None:
            subdirs = [
                subdir
                for subdir in subdirs
                if not (
                    os.path.isfile(os.path.join(subdir, ".process"))
                    or os.path.isfile(os.path.join(subdir, ".false"))
                    or os.path.isfile(os.path.join(subdir, ".complete"))
                )
            ]

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
                    date_parts = subdir_time.split("_")
                    date_elements = date_parts[0].split("-")
                    time_elements = date_parts[1].split("-")
                    subdir_time = "{}-{}-{} {}:{}:{}".format(
                        date_elements[0],
                        date_elements[1],
                        date_elements[2],
                        time_elements[0],
                        time_elements[1],
                        time_elements[2],
                    )
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

                    with open(log_file, "r", encoding="utf-8") as file:
                        lines = file.readlines()

                    if len(lines) >= 3:
                        return lines[1].strip() + "\n" + lines[2].strip() + "\n"
                    else:
                        return "ログファイルなし：無効な証拠フォルダです。「誤検出」に分類したあと削除してください。\n"

                directory = os.path.dirname(torrent_file_path)
                torrent_situation = extract_log_lines(directory)

                match = re.search(
                    r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", folder_names[index]
                )
                datetime_str = match.group().replace("_", " ").replace("-", ":")
                dt = datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")

                # 取得済みのピア数を表示
                def peer_counter(directory):
                    # peer.csvのパスを組み立てる
                    peer_csv_path = os.path.join(directory, "peer.csv")

                    # ファイルが存在しない場合は0を返す
                    if not os.path.exists(peer_csv_path):
                        return 0

                    # 1列目の要素をリスト化する
                    with open(peer_csv_path, "r") as file:
                        reader = csv.reader(file)
                        first_column_elements = [row[0] for row in reader if row]

                    # 重複を削除
                    unique_elements = set(first_column_elements)

                    return len(unique_elements)

                def count_bin_files(directory):
                    # サブフォルダ内のすべての .bin ファイルのパスを取得
                    bin_files = glob.glob(os.path.join(directory, "*", "*.bin"))

                    return len(bin_files)

                info_text.insert(tk.END, f"【 採取済みピア数：{peer_counter(directory)} 】　")
                info_text.insert(tk.END, f"【 ピース数：{count_bin_files(directory)} 】\n\n")

                # トレントファイルに含まれる情報を表示
                info_text.insert(
                    tk.END, f"対象ファイル名：{torrent.name if torrent.name else '不明'}\n\n"
                )
                info_text.insert(tk.END, f"torrent取得日時：{dt}\n")
                info_text.insert(tk.END, f"{torrent_situation}\n")
                info_text.insert(tk.END, "【torrentファイル内の情報】\n")
                info_text.insert(
                    tk.END,
                    f"作成日時：{torrent.creation_date if torrent.creation_date else '不明'}\n",
                )
                info_text.insert(
                    tk.END,
                    f"作成者：{torrent.created_by if torrent.created_by else '不明'}\n",
                )
                info_text.insert(
                    tk.END, f"コメント：{torrent.comment if torrent.comment else '不明'}\n"
                )
                info_text.insert(
                    tk.END,
                    "ファイルサイズ：{} MB\n".format(
                        bytes_to_mb(torrent.total_size) if torrent.total_size else "不明"
                    ),
                )
                info_text.insert(
                    tk.END,
                    f"ハッシュ：{torrent.info_hash if torrent.info_hash else '不明'}\n\n",
                )
                info_text.insert(
                    tk.END,
                    "トラッカー：{}\n".format(
                        ", ".join(
                            [
                                url
                                for sublist in torrent.announce_urls
                                for url in sublist
                            ]
                        )
                        if torrent.announce_urls
                        else "不明"
                    ),
                )
                info_text.config(state=tk.DISABLED)

            selected_indices = suspect_listbox.curselection()
            if selected_indices:
                start_button.config(state=tk.NORMAL)
            else:
                start_button.config(state=tk.DISABLED)

        suspect_listbox.bind("<<ListboxSelect>>", on_select)

    # 表示内容を更新
    def update():
        names(complete_listbox, complete_text, restart_button, selected_tab="complete")
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
        selected_text = false_listbox.get(num)

        # 2. num番目のフォルダを削除
        torrent_folder = os.path.join(Path(__file__).parents[0], "evi/tor")
        subdirs = [
            os.path.join(torrent_folder, folder)
            for folder in os.listdir(torrent_folder)
            if os.path.isdir(os.path.join(torrent_folder, folder))
        ]
        folder_list = [
            subdir
            for subdir in subdirs
            if os.path.isfile(os.path.join(subdir, ".false"))
        ]
        target_folder = folder_list[num]
        shutil.rmtree(target_folder)

        false_text.config(state=tk.NORMAL)
        false_text.delete(1.0, tk.END)
        false_text.insert(tk.END, "「" + selected_text + "」をフォルダごと削除しました。")
        false_text.config(state=tk.DISABLED)

        update()

    def find_matching_folders(listbox):
        # 日付を抽出
        selected_indices = listbox.curselection()

        if not selected_indices:
            print("選択されている項目がありません。")
            return []

        index = selected_indices[0]
        selected_text = listbox.get(index)

        # 正規表現で末尾の日付形式を抜き出す
        date_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})$"
        match = re.search(date_pattern, selected_text)

        if not match:
            print("日付形式が見つかりませんでした。")
            return []

        date_str = match.group(1)
        # この日付をフォルダ名形式に変換
        folder_date_format = date_str.replace(":", "-").replace(" ", "_")

        # フォルダ内のサブディレクトリを取得
        torrent_folder = os.path.join(Path(__file__).parents[0], "evi/tor")
        subdirs = [
            os.path.join(torrent_folder, folder)
            for folder in os.listdir(torrent_folder)
            if os.path.isdir(os.path.join(torrent_folder, folder))
        ]

        # 日付と一致するフォルダを抽出
        matching_folders = [
            folder for folder in subdirs if folder_date_format in folder
        ]

        return matching_folders

    def mark_folder(listbox, text, status):
        # 日付を抽出
        selected_indices = listbox.curselection()

        if not selected_indices:
            print("選択されている項目がありません。")
            return []

        index = selected_indices[0]
        selected_text = listbox.get(index)

        target_folder = find_matching_folders(listbox)[0]

        if not os.path.isfile(os.path.join(target_folder, status)):
            with open(os.path.join(target_folder, status), "w", encoding="utf-8"):
                pass

        if status == ".false":
            tab_name = "を誤検出"
        if status == ".process":
            tab_name = "の証拠採取を開始し、採取中"
        if status == ".complete":
            tab_name = "の証拠採取を完了し、完了一覧"
            os.remove(os.path.join(target_folder, ".process"))

        text.config(state=tk.NORMAL)
        text.delete(1.0, tk.END)
        text.insert(tk.END, "「" + selected_text + "」" + tab_name + "タブに移動しました。")
        text.config(state=tk.DISABLED)

        update()

    def unmark_folder(listbox, text, status):
        # リストボックスの選択された要素のインデックスを取得
        selected_indices = listbox.curselection()

        if selected_indices:  # 選択された要素が存在する場合
            index = selected_indices[0]
            selected_text = listbox.get(index)
        else:
            print("選択されているファイルがありません。")
            return

        # リストボックスの選択された要素のインデックスを取得
        target_folder = find_matching_folders(listbox)[0]

        if os.path.isfile(os.path.join(target_folder, status)):
            os.remove(os.path.join(target_folder, status))
            if status == ".complete":
                with open(
                    os.path.join(target_folder, ".process"), "w", encoding="utf-8"
                ):
                    pass

        if status == ".complete":
            tab_name = "採取中"
        else:
            tab_name = "証拠採取の候補"

        text.config(state=tk.NORMAL)
        text.delete(1.0, tk.END)
        text.insert(tk.END, "「" + selected_text + "」を" + tab_name + "タブに戻しました。")
        text.config(state=tk.DISABLED)

        update()

    def start_picking():
        message = (
            "証拠採取を開始します。\n\n"
            "対象のファイルがあなたの権利物であることをよく確認してください。\n"
            "誤ったファイルをダウンロードした場合、あなたが著作権侵害に問われる場合があります。\n\n"
            "本当によろしいですか？"
        )

        return messagebox.askyesno("警告", message)

    def is_info_hash_duplicate(torrent_folder, torrent_files):
        # あらかじめtorrent_filesのinfo_hashを取得してリストに格納
        new_info_hashes = []
        for torrent_file in torrent_files:
            new_torrent = Torrent.from_file(torrent_file)
            new_info_hashes.append(new_torrent.info_hash)

        # 指定されたフォルダ内の全てのファイルを巡回
        for foldername, subfolders, filenames in os.walk(torrent_folder):
            for filename in filenames:
                if filename.endswith(".torrent"):
                    existing_torrent_path = os.path.join(foldername, filename)
                    existing_torrent = Torrent.from_file(existing_torrent_path)
                    existing_info_hash = existing_torrent.info_hash

                    # 既存のトレントのinfo_hashと、new_info_hashesリスト内の全てのinfo_hashを比較する
                    if existing_info_hash in new_info_hashes:
                        print(
                            f"すでに存在しているtorrentファイルです: {torrent_files[new_info_hashes.index(existing_info_hash)]}"
                        )
                        return True
        return False

    def on_bulk_add_button_click(age):
        # 1. ユーザーのPCから複数の.torrentファイルを選択するためのダイアログを開く
        torrent_files = filedialog.askopenfilenames(
            filetypes=[("Torrentファイル", "*.torrent")]
        )
        torrent_folder = os.path.join(EVIDENCE_FOLDER, "tor")

        if not torrent_files:
            # torrentファイルが選択されていない場合は何もせずに戻る
            return
        if not is_info_hash_duplicate(EVIDENCE_FOLDER, torrent_files):
            for torrent_file in torrent_files:
                # 2. 'folder_time'という名前の新しいフォルダを'EVIDENCE_FOLDER'内に作成する
                # フォルダ名に使う現在日時を取得
                try:
                    folder_time = ut.fetch_jst().strftime("%Y-%m-%d_%H-%M-%S")
                except ut.TimeException:
                    folder_time = ut.utc_to_jst(datetime.now()).strftime(
                        "%Y-%m-%d_%H-%M-%S"
                    )
                    print(
                        "NTPサーバーから現在時刻を取得できませんでした。フォルダ名はローカルのシステム時刻を参照しており、正確な生成時刻を示していない可能性があります。"
                    )
                folder_path = os.path.join(torrent_folder, folder_time)
                os.makedirs(folder_path, exist_ok=True)

                if age == "r18":
                    r18_file_path = os.path.join(folder_path, ".r18")
                    with open(r18_file_path, "w"):
                        pass

                # 3. 選択されたtorrentファイルを'folder_time'フォルダにコピーする
                dst_file_path = os.path.join(
                    folder_path, os.path.basename(torrent_file)
                )
                shutil.copy2(torrent_file, dst_file_path)

                # 4. コピーされたtorrentファイルの名前を'source.torrent'に変更する
                src_file_path = os.path.join(folder_path, "source.torrent")
                os.rename(dst_file_path, src_file_path)

                # torrentファイルの読み込み時の情報を記録
                log_file_path = os.path.join(folder_path, "evi_" + folder_time + ".log")

                with open(log_file_path, "w", encoding="utf-8") as log_file:
                    torrent = Torrent.from_file(src_file_path)
                    LOG = (
                        "対象ファイル名："
                        + torrent.name
                        + "\ntorrent取得方法：ローカルに保存されたtorrentファイルから"
                        + "\n取得元："
                        + dst_file_path
                        + "\n証拠フォルダ生成日時："
                        + folder_time
                        + "\nファイルハッシュ："
                        + torrent.info_hash
                    )
                    log_file.write(LOG)
                time.sleep(1)
        else:
            for torrent_file in torrent_files:
                root = tk.Tk()
                torrent = Torrent.from_file(torrent_file)
                root.withdraw()  # メインウィンドウを隠す
                messagebox.showinfo("Alert", torrent.name + "はすでに存在しているファイルです。")
                root.destroy()  # メインウィンドウを閉じる

        update()

    def combined_commands():
        if start_picking():
            mark_folder(suspect_listbox, info_text, ".process")

    start_button.config(command=combined_commands)
    mark_button.config(
        command=lambda: mark_folder(suspect_listbox, info_text, ".false")
    )
    unmark_button.config(
        command=lambda: unmark_folder(false_listbox, false_text, ".false")
    )
    suspend_button.config(
        command=lambda: unmark_folder(process_listbox, process_text, ".process")
    )
    complete_button.config(
        command=lambda: mark_folder(process_listbox, process_text, ".complete")
    )
    restart_button.config(
        command=lambda: unmark_folder(complete_listbox, complete_text, ".complete")
    )
    delete_button.config(command=delete_folder)
    bulk_add_button.config(command=lambda: on_bulk_add_button_click("all"))
    r18_bulk_add_button.config(command=lambda: on_bulk_add_button_click("r18"))

    refresh_buttons = [
        refresh_button1,
        refresh_button2,
        refresh_button3,
        refresh_button4,
    ]
    for button in refresh_buttons:
        button.config(command=update)

    update()

    window.protocol("WM_DELETE_WINDOW", on_window_close)

    window.mainloop()


if __name__ == "__main__":
    main()
