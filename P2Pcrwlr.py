import tkinter as tk
from tkinter import ttk

def main():
    window = tk.Tk()
    window.title('P2Pクローラ')
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
    new_keyword_label = tk.Label(tab1, text="新しい検索語を追加", font=font)
    new_keyword_label.pack(pady=(10, 0))

    keyword_entry_frame = tk.Frame(tab1)
    keyword_entry_frame.pack(fill=tk.X, pady=(10, 0))

    keyword_entry = tk.Entry(keyword_entry_frame, font=font, insertwidth=3)
    keyword_entry.pack(side=tk.LEFT, fill=tk.X, padx=(160, 10), expand=True)

    add_button = tk.Button(keyword_entry_frame, text="追加",font=font)
    add_button.pack(side=tk.LEFT, padx=(0, 100))

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
    nested_notebook.add(crawl_history_tab, text='検出履歴')

    crawl_history_button_frame = tk.Frame(crawl_history_tab)
    crawl_history_button_frame.pack(fill=tk.X, pady=(0, 5))

    crawl_history_clear_button = tk.Button(crawl_history_button_frame, text="履歴をクリア", font=small_font)
    crawl_history_clear_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    # リストボックスを含むフレーム
    listbox_frame = tk.Frame(crawl_history_tab)
    listbox_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # リストボックス
    crawl_history_listbox = tk.Listbox(listbox_frame, width=-1, height=7, font=font)
    crawl_history_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=crawl_history_listbox.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    crawl_history_listbox.config(yscrollcommand=scrollbar.set)

    # サイズ変更用ウィジェット
    sizegrip = ttk.Sizegrip(crawl_history_tab)
    sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    sizegrip.lift(aboveThis=listbox_frame)

    all_age_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(all_age_tab, text='全年齢')

    button_frame = tk.Frame(all_age_tab)
    button_frame.pack(fill=tk.X, pady=(0, 5))

    delete_button = tk.Button(button_frame, text="削除する", font=small_font)
    delete_button.pack(side=tk.RIGHT, padx=(0, 10))

    bulk_add_button = tk.Button(button_frame, text="ファイルからまとめて追加", font=small_font)
    bulk_add_button.pack(side=tk.RIGHT, padx=(0, 10))

    # リストボックスを含むフレーム
    all_age_listbox_frame = tk.Frame(all_age_tab)
    all_age_listbox_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # リストボックス
    keyword_listbox = tk.Listbox(all_age_listbox_frame, width=-1, height=7, font=font)
    keyword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    all_age_scrollbar = tk.Scrollbar(all_age_listbox_frame, orient=tk.VERTICAL, command=keyword_listbox.yview)
    all_age_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    keyword_listbox.config(yscrollcommand=all_age_scrollbar.set)

    # サイズ変更用ウィジェット
    all_age_sizegrip = ttk.Sizegrip(all_age_tab)
    all_age_sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    all_age_sizegrip.lift(aboveThis=all_age_listbox_frame)

    r18_tab = ttk.Frame(nested_notebook)
    nested_notebook.add(r18_tab, text='成人向け')
    
    r18_button_frame = tk.Frame(r18_tab)
    r18_button_frame.pack(fill=tk.X, pady=(0, 5))

    r18_delete_button = tk.Button(r18_button_frame, text="削除する", font=small_font)
    r18_delete_button.pack(side=tk.RIGHT, padx=(0, 10))
    
    r18_bulk_add_button = tk.Button(r18_button_frame, text="ファイルからまとめて追加", font=small_font)
    r18_bulk_add_button.pack(side=tk.RIGHT, padx=(0, 10))

    # リストボックスを含むフレーム
    r18_listbox_frame = tk.Frame(r18_tab)
    r18_listbox_frame.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # リストボックス
    r18_keyword_listbox = tk.Listbox(r18_listbox_frame, width=-1, height=7, font=font)
    r18_keyword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    r18_scrollbar = tk.Scrollbar(r18_listbox_frame, orient=tk.VERTICAL, command=r18_keyword_listbox.yview)
    r18_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    r18_keyword_listbox.config(yscrollcommand=r18_scrollbar.set)

    # サイズ変更用ウィジェット
    r18_sizegrip = ttk.Sizegrip(r18_tab)
    r18_sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    r18_sizegrip.lift(aboveThis=r18_listbox_frame)

    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text='設定')    

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()

if __name__ == '__main__':
    main()