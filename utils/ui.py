import tkinter as tk

_text_widget = None


def setup_pri_redirector(text_widget):
    global _text_widget
    _text_widget = text_widget


def redirect_pri(*args, **kwargs):
    # オリジナルのprint関数を呼び出す
    print(*args, **kwargs)
    if _text_widget:
        # Textウィジェットに内容を追加
        text = " ".join(map(str, args))
        _text_widget.insert(tk.END, text + "\n")
        # オートスクロール
        _text_widget.see(tk.END)
