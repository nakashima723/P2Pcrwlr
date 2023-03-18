import tkinter as tk
from tkinter import ttk

def main():
    window = tk.Tk()
    window.title('ウィンドウ表示テスト')
    window.geometry('800x600')

    # タブのスタイルをカスタマイズ
    style = ttk.Style()
    style.configure('TNotebook.Tab', font=('TkDefaultFont', 15), padding=(15, 6, 15, 6))


    # タブの追加
    notebook = ttk.Notebook(window)
    notebook.pack(fill=tk.BOTH, expand=True)

    tab1 = ttk.Frame(notebook)
    notebook.add(tab1, text='巡回システム')

    tab2 = ttk.Frame(notebook)
    notebook.add(tab2, text='証拠採取')

    window.protocol("WM_DELETE_WINDOW", window.quit)

    window.mainloop()

if __name__ == '__main__':
    main()