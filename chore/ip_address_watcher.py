from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.clock import Clock
from torrent.client import _get_public_ips
from utils.time import get_jst_str
import os

# ログファイルの設定
application_path = (
    App.get_running_app().user_data_dir
    if App.get_running_app()
    else os.path.dirname(__file__)
)
log_file_path = os.path.join(application_path, "IP_address_watcher.log")

# ログファイルが存在しない場合、新規作成
if not os.path.exists(log_file_path):
    with open(log_file_path, "w", encoding="utf-8") as f:
        f.write("Last Update:\n")


class IPAddressWatcherApp(App):
    def build(self):
        layout = BoxLayout(orientation="vertical")

        # UI部品の定義
        self.last_recorded_time_label = Label(text="Last Update:", font_size=18)
        self.current_ipv4_label = Label(text="", font_size=18)
        self.current_ipv6_label = Label(text="", font_size=18)
        scroll_view = ScrollView(size_hint=(1, None), size=(400, 400))
        self.log_display_label = Label(text="", font_size=14, size_hint_y=None)
        self.log_display_label.bind(texture_size=self.log_display_label.setter("size"))
        scroll_view.add_widget(self.log_display_label)

        # 「ログ表示」ボタンの定義
        show_log_button = Button(text="Show LOG", size_hint_y=None, height=50)
        show_log_button.bind(on_press=self.show_logs)

        # UI部品をレイアウトに追加
        layout.add_widget(self.last_recorded_time_label)
        layout.add_widget(self.current_ipv4_label)
        layout.add_widget(self.current_ipv6_label)
        layout.add_widget(show_log_button)
        layout.add_widget(scroll_view)

        # アプリ起動直後にも一度呼び出す
        self.update_log(0)

        # 1分ごとにupdate_logを呼び出す
        Clock.schedule_interval(self.update_log, 10)

        return layout

    # ログを表示する関数
    def show_logs(self, instance):
        with open(log_file_path, "r", encoding="utf-8") as f:
            display_text = f.read()
        self.log_display_label.text = display_text

    def __init__(self, **kwargs):
        super(IPAddressWatcherApp, self).__init__(**kwargs)
        self.last_ipv4 = None
        self.last_ipv6 = None

    def update_log(self, dt):
        current_time = get_jst_str()
        ipv4, ipv6 = _get_public_ips()
        self.current_ipv4_label.text = f"IPv4: {ipv4}"
        self.current_ipv6_label.text = f"IPv6: {ipv6}"

        # 前回のIPアドレスと現在のIPアドレスを比較
        if ipv4 != self.last_ipv4 or ipv6 != self.last_ipv6:
            # ログファイルに書き込む
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(f"{current_time}, {ipv4}, {ipv6}\n")

            # 現在のIPアドレスを「前回のIPアドレス」として保持
            self.last_ipv4 = ipv4
            self.last_ipv6 = ipv6

        self.last_recorded_time_label.text = f"Last Update:{current_time}"
        self.show_logs(Button)


if __name__ == "__main__":
    IPAddressWatcherApp().run()
