import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

def main():
    window = tk.Tk()
    window.title('P2Pスレイヤー')
    window.geometry('800x600')
    
   # フォント設定nesteda
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
    
    # リストボックスを含むキャンバス
    suspect_canvas = tk.Canvas(tab1)
    suspect_canvas.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # キャンバス内にリストボックスを含むフレームを配置
    suspect_listbox_frame = tk.Frame(suspect_canvas)
    suspect_listbox_frame.pack(fill=tk.BOTH, expand=True)

    # リストボックス
    keyword_listbox = tk.Listbox(suspect_listbox_frame, width=-1, height=4, font=small_font)
    keyword_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # スクロールバー
    suspect_scrollbar = tk.Scrollbar(suspect_listbox_frame, orient=tk.VERTICAL, command=keyword_listbox.yview)
    suspect_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    keyword_listbox.config(yscrollcommand=suspect_scrollbar.set)

    # サイズ変更用ウィジェット
    def on_sizegrip_dragged(event):
        keyword_listbox.config(height=keyword_listbox.size()+int(event.delta/10))

    suspect_sizegrip = ttk.Sizegrip(suspect_listbox_frame)
    suspect_sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    suspect_sizegrip.lift()
    suspect_sizegrip.bind("<B1-Motion>", on_sizegrip_dragged)

    # 編集用ボタン
    button_frame = tk.Frame(tab1)
    button_frame.pack(fill=tk.X, pady=(0, 5))

    bulk_add_button = tk.Button(button_frame, text="ファイルから追加", font=small_font)
    bulk_add_button.pack(side=tk.LEFT, padx=(10, 10))

    url_add_button = tk.Button(button_frame, text="URLから追加", font=small_font)
    url_add_button.pack(side=tk.LEFT, padx=(0, 10))

    delete_button = tk.Button(button_frame, text="削除", font=small_font)
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

    # リストボックスを含むキャンバス
    info_canvas = tk.Canvas(tab1)
    info_canvas.pack(fill=tk.BOTH, padx=(10, 10), pady=(0, 10), expand=True)

    # キャンバス内にリストボックスを含むフレームを配置
    info_text_frame = tk.Frame(info_canvas)
    info_text_frame.pack(fill=tk.BOTH, expand=True)

    # リストボックス
    keyword_text = tk.Text(info_text_frame, wrap=tk.WORD, width=-1, height=7, font=small_font)
    keyword_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    keyword_text.insert(tk.END, "ここにtorrentファイルの情報が表示されます。\nユーザーは表示内容を見て、証拠採取を開始するかどうか決めます。\n\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト\n改行テスト")


    # スクロールバー
    info_scrollbar = tk.Scrollbar(info_text_frame, orient=tk.VERTICAL, command=keyword_text.yview)
    info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    keyword_text.config(yscrollcommand=info_scrollbar.set, state=tk.DISABLED)

    # サイズ変更用ウィジェット
    def on_sizegrip_dragged(event):
        keyword_text.config(height=keyword_text.size()+int(event.delta/10))

    info_sizegrip = ttk.Sizegrip(info_text_frame)
    info_sizegrip.pack(side=tk.BOTTOM, anchor=tk.SE)
    info_sizegrip.lift()
    info_sizegrip.bind("<B1-Motion>", on_sizegrip_dragged)
    
    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text='採取状況')

    tab3 = ttk.Frame(notebook)
    notebook.add(tab3, text='統計')
    
    tab4 = ttk.Frame(notebook)
    notebook.add(tab4, text='設定')    

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()
    

if __name__ == '__main__':
    main()