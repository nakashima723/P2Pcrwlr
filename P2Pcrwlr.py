import json
import os
import re
import tkinter as tk
from tkinter import ttk
import tkinter.messagebox as messagebox

def main():
    window = tk.Tk()
    window.title('P2Pクローラ')
    window.geometry('800x600')
    
   # フォント設定
    font = ('', 17)
    small_font = ('', 14)
    tiny_font = ('', 11)

    # タブのスタイルをカスタマイズ
    style = ttk.Style()
    style.configure('TNotebook.Tab', font=('TkDefaultFont', 17), padding=(15, 6, 15, 6))    
    style.configure("Large.TRadiobutton",font=font)

    # タブの追加
    notebook = ttk.Notebook(window)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text='巡回システム')

    # 巡回の間隔
    interval_frame = tk.Frame(tab1)
    interval_frame.pack(pady=(10, 10))

    interval_label = tk.Label(interval_frame, text="巡回の間隔",font=font)
    interval_label.pack(side=tk.LEFT, padx=(50, 10))

    interval_options = ["30分", "1時間", "2時間", "4時間", "6時間"]
    interval_var = tk.StringVar()
    interval_var.set(interval_options[0])

    interval_menu = ttk.Combobox(interval_frame, textvariable=interval_var, values=interval_options, font=font, state="readonly", width=6)
    interval_menu.pack(side=tk.LEFT)
    
    patrol_button = tk.Button(interval_frame, text="いますぐ巡回", font=font)
    patrol_button.pack(side=tk.RIGHT, padx=(30, 0))
    
    crawl_history_frame = tk.Frame(tab1)
    crawl_history_frame.pack(pady=(10, 10))

    crawl_history = tk.Label(crawl_history_frame, text="最後に巡回した日時： 2023年01月01日12時00分59秒", font=small_font)
    crawl_history.pack(side=tk.LEFT, padx=(0, 5))

    # 新しい検索語を追加
    keyword_entry_frame = tk.Frame(tab1)
    keyword_entry_frame.pack(fill=tk.X, pady=(10, 0))

    new_keyword_label = tk.Label(keyword_entry_frame, text="新しい検索語：", font=font)
    new_keyword_label.pack(side=tk.LEFT, padx=(80, 10))

    keyword_entry = tk.Entry(keyword_entry_frame, font=font, insertwidth=3)
    keyword_entry.pack(side=tk.LEFT, fill=tk.X, padx=(0, 10), expand=True)

    add_button = tk.Button(keyword_entry_frame, text="追加",font=font)
    add_button.pack(side=tk.LEFT, padx=(0, 100))

    option_entry_frame = tk.Frame(tab1)
    option_entry_frame.pack(fill=tk.X, pady=(10, 5),)

    creator_label = tk.Label(option_entry_frame, text="作者：", font=small_font)
    creator_label.pack(side=tk.LEFT, padx=(140, 0))

    entry_width = 15  # 両方のEntryウィジェットの横幅を設定

    creator_entry = tk.Entry(option_entry_frame, font=font, insertwidth=3, width=entry_width)
    creator_entry.pack(side=tk.LEFT, padx=(0, 10))

    publisher_label = tk.Label(option_entry_frame, text="版元：", font=small_font)
    publisher_label.pack(side=tk.LEFT, padx=(10, 0))

    publisher_entry = tk.Entry(option_entry_frame, font=font, insertwidth=3, width=entry_width)
    publisher_entry.pack(side=tk.LEFT, padx=(0, 100))

    url_frame = tk.Frame(tab1)
    url_frame.pack(fill=tk.X, pady=(10, 5),)

    url_label = tk.Label(url_frame, text="参考URL：", font=small_font)
    url_label.pack(side=tk.LEFT, padx=(95, 10))

    url_entry = tk.Entry(url_frame, font=font, insertwidth=3)
    url_entry.pack(side=tk.LEFT, fill=tk.X, padx=(0, 160), expand=True)

    # ラジオボタン
    radio_frame = tk.Frame(tab1)
    radio_frame.pack(pady=(10, 5))

    radio_var = tk.StringVar()
    radio_var.set("全年齢")

    radio_all = ttk.Radiobutton(radio_frame, text="全年齢", value="全年齢", variable=radio_var,  style="Large.TRadiobutton")
    radio_all.pack(side=tk.LEFT, padx=(0, 5))

    radio_adult = ttk.Radiobutton(radio_frame, text="成人向け", value="成人向け", variable=radio_var, style="Large.TRadiobutton")
    radio_adult.pack(side=tk.LEFT)

    # 空白
    spacer = tk.Frame(tab1, height=30)
    spacer.pack(fill=tk.X, expand=False)

    # tab1内に新しいタブを追加
    nested_notebook = ttk.Notebook(tab1)
    nested_notebook.pack(fill=tk.BOTH, expand=True)
    
    crawl_history_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(crawl_history_tab, text='履歴')

    # 検出履歴を含むフレーム
    history_frame = tk.Frame(crawl_history_tab)
    history_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # 検出履歴
    crawl_history = tk.Text(history_frame, width=-1, height=7, font=small_font)
    crawl_history.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    scrollbar = tk.Scrollbar(history_frame, orient=tk.VERTICAL, command=crawl_history.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    crawl_history.config(yscrollcommand=scrollbar.set)

    # サイズ変更用ウィジェット
    sizegrip = ttk.Sizegrip(crawl_history_tab)
    sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    sizegrip.lift(aboveThis=history_frame)

    all_age_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(all_age_tab, text='全年齢')

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
    treeview = ttk.Treeview(all_age_frame, columns=("検索語", "作者", "版元", "参考"), show="headings", selectmode="browse")
    treeview.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバーの追加
    scrollbar = ttk.Scrollbar(all_age_frame, orient=tk.VERTICAL, command=treeview.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    treeview.configure(yscrollcommand=scrollbar.set)

    style = ttk.Style()
    style.configure("Treeview", font=small_font)

    r18_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(r18_tab, text='成人向け')
    
    # リストボックスを含むフレーム    
    r18_button_frame = tk.Frame(r18_tab)
    r18_button_frame.pack(fill=tk.X, pady=(0, 5))

    r18_delete_button = tk.Button(r18_button_frame, text="削除", font=small_font)
    r18_delete_button.pack(side=tk.LEFT, padx=(10, 0))    
    
    r18_bulk_add_button = tk.Button(r18_button_frame, text="ファイルからまとめて追加", font=small_font)
    r18_bulk_add_button.pack(side=tk.RIGHT, padx=(0, 10))

    r18_edit_button = tk.Button(r18_button_frame, text="編集する", font=small_font)
    r18_edit_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    r18_frame = tk.Frame(r18_tab)
    r18_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # Treeviewの作成
    r18treeview = ttk.Treeview(r18_frame, columns=("検索語", "作者", "版元", "参考"), show="headings", selectmode="browse")
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
        settings_folder = "settings"
        data_json = filename
        settings_file = os.path.join(settings_folder, data_json)

        if os.path.exists(settings_file) and os.path.getsize(settings_file) > 0:
            with open(settings_file, "r") as f:
                saved_data = json.load(f)
        else:
            saved_data = []

        return saved_data
    
    #指定したタブを表示
    def show_tab(notebook, nested_tab_name):
        for index in range(notebook.index("end")):
            child_widget = notebook.nametowidget(notebook.tabs()[index])
            if isinstance(child_widget, ttk.Notebook):
                nested_notebook = child_widget
                for nested_index in range(nested_notebook.index("end")):
                    if nested_notebook.tab(nested_index, "text") == nested_tab_name:
                        notebook.select(index)
                        nested_notebook.select(nested_index)
                        break

    def populate_treeview(treeview, data):
        # Treeviewの内容をクリア
        for item in treeview.get_children():
            treeview.delete(item)

        # 新しいデータをTreeviewに追加
        for item in data:
            treeview.insert("", "end", values=item)
    
    #「追加」ボタンのコマンドを設定
    def save_data():        
        # 入力されたデータを取得 
        keyword = keyword_entry.get()
        keyword = keyword.strip()  # 文頭のスペースを削除
        keyword = re.sub(r'\s{2,}', ' ', keyword)  # 2つ以上連続しているスペースを1つにする
        keyword = keyword.replace("　", "")  # 全角スペースを削除
        if not keyword:
            messagebox.showerror("エラー", "検索語が入力されていません。")
            edit_button.config(text="編集する", font=small_font)
            return
        creator = creator_entry.get().replace(" ", "").replace("　", "")    
        publisher = publisher_entry.get() .replace(" ", "").replace("　", "")    
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
        new_data = (keyword, creator, publisher, url, age_rating)

        # 保存先フォルダを作成
        settings_folder = "settings"
        if not os.path.exists(settings_folder):
            os.makedirs(settings_folder)

        # 保存先ファイル名をラジオボタンの値に基づいて設定
        if age_rating == "全年齢":
            settings_file = os.path.join(settings_folder, "queries.json")
        else:
            settings_file = os.path.join(settings_folder, "r18queries.json")

        # データを読み込み、新しいデータを追加
        if os.path.exists(settings_file) and os.path.getsize(settings_file) > 0:
            with open(settings_file, "r") as f:
                saved_data = json.load(f)
        else:
            saved_data = []

        saved_data.insert(0, new_data)

        # データをファイルに保存
        with open(settings_file, "w") as f:
            json.dump(saved_data, f, ensure_ascii=False, indent=2)

        # 入力領域をクリア
        keyword_entry.delete(0, tk.END)
        creator_entry.delete(0, tk.END)
        publisher_entry.delete(0, tk.END)
        url_entry.delete(0, tk.END)
        
        crawl_history.configure(state=tk.NORMAL)  # テキストエリアを編集可能にする
        crawl_history.insert("1.0", "「" + keyword + "」を" + age_rating +"の検索語として追加しました。\n")  # 文字列を一番上の行に挿入
        crawl_history.configure(state=tk.DISABLED)  # テキストエリアを再びreadonlyにする
        
        queries_data = load_queries("queries.json")
        r18queries_data = load_queries("r18queries.json")
        populate_treeview(treeview, queries_data)
        populate_treeview(r18treeview, r18queries_data)        
        edit_button.config(text="編集する", font=small_font)
        r18_edit_button.config(text="編集する", font=small_font)

    #クエリ表示タブの削除ボタンのコマンド
    def delete_selected_item(treeview, json_file_name):        
        selected_items = treeview.selection()
        settings_folder = "settings"
        json_file_path = os.path.join(settings_folder, json_file_name)

        if not selected_items:
            edit_button.config(text="編集する", font=small_font)
            r18_edit_button.config(text="編集する", font=small_font)
            return

        selected_values = [treeview.item(item, 'values') for item in selected_items]

        # Treeviewから選択されたアイテムを削除
        for item in selected_items:
            treeview.delete(item)

        # JSONファイルからデータを読み込み、選択されたアイテムを削除
        with open(json_file_path, "r") as f:
            data = json.load(f)

        # 選択されたアイテムを削除
        data = [item for item in data if tuple(item) not in selected_values]

        # JSONファイルを更新
        with open(json_file_path, "w") as f:
            json.dump(data, f)

        first_values = [value[0] for value in selected_values]
        formatted_values = ['「{}」'.format(value) for value in first_values]
        result = "".join(formatted_values)

        #履歴を更新
        crawl_history.configure(state=tk.NORMAL)  # テキストエリアを編集可能にする
        crawl_history.insert("1.0", "検索語" + result + "を削除しました。\n")  # 文字列を一番上の行に挿入
        crawl_history.configure(state=tk.DISABLED)  # テキストエリアを再びreadonlyにする

    def query_edit(edit_button,treeview,json_file_name): 
        selected_item = treeview.selection()
    
        if not selected_item:
            return

        item_values = treeview.item(selected_item[0], 'values')

        keyword_entry.delete(0, tk.END)
        keyword_entry.insert(0, item_values[0])

        creator_entry.delete(0, tk.END)
        creator_entry.insert(0, item_values[1])

        publisher_entry.delete(0, tk.END)
        publisher_entry.insert(0, item_values[2])

        url_entry.delete(0, tk.END)
        url_entry.insert(0, item_values[3])  
        edit_button.config(text="↑編集後、『追加』ボタンを押してください", font=font)
        delete_selected_item(treeview, json_file_name)

    # データを読み込み、各Treeviewに表示
    queries_data = load_queries("queries.json")
    r18queries_data = load_queries("r18queries.json")
    populate_treeview(treeview, queries_data)
    populate_treeview(r18treeview, r18queries_data)
    treeview_set(treeview)
    treeview_set(r18treeview)

    #クエリ表示タブのボタン類にコマンドを設定
    edit_button.config(command=lambda: query_edit(edit_button,treeview, "queries.json"))
    r18_edit_button.config(command=lambda: query_edit(r18_edit_button,r18treeview, "r18queries.json"))
    delete_button.config(command=lambda: delete_selected_item(treeview, "queries.json"))
    r18_delete_button.config(command=lambda: delete_selected_item(r18treeview, "r18queries.json"))

    # クエリ追加ボタンのコマンドを設定
    add_button.config(command=save_data) 

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()

if __name__ == '__main__':
    main()