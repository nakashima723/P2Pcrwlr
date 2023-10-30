# APNICのサイトからIPアドレス範囲リストを取得し、日本国内のIP範囲一覧を作成して
# 設定ファイルを自動更新するモジュール
import ipaddress
import json
import math
import os
import urllib.request
from email.utils import parsedate_to_datetime
from utils.config import Config

current_dir = os.path.dirname(os.path.abspath(__file__))
con = Config(base_path=current_dir, level=1)

EVI_FOLDER = con.EVI_FOLDER
SETTING_FOLDER = con.SETTING_FOLDER
SETTING_FILE = con.SETTING_FILE
TORRENT_FOLDER = con.TORRENT_FOLDER

# URLを指定
url = "https://ftp.apnic.net/apnic/stats/apnic/delegated-apnic-extended-latest"


def merge_ip_ranges(ip_ranges):
    if not ip_ranges:  # 入力が空かどうかをチェック
        print("IP範囲が指定されていません。")
        return []

    # IP範囲のリストを生成し、無効な範囲があればエラーを出力
    try:
        ip_ranges_obj = []
        for ip_range in ip_ranges:
            ip_ranges_obj.append(ipaddress.ip_network(ip_range))
    except ValueError as e:
        print(f"エラーが発生したIP範囲: {ip_range}")
        print(f"具体的なエラー: {e}")
        return []

    # ソート
    ip_ranges_obj.sort(key=lambda x: x.network_address)

    # 合成処理
    merged_ranges = []
    current = ip_ranges_obj[0]

    for next_range in ip_ranges_obj[1:]:
        if (
            current.overlaps(next_range)
            or current.broadcast_address + 1 == next_range.network_address
        ):
            # collapse_addressesの結果をリストに変換し、最初の要素を取得
            current = list(ipaddress.collapse_addresses([current, next_range]))[0]
        else:
            merged_ranges.append(str(current))
            current = next_range

    merged_ranges.append(str(current))


def process_data(lines):
    ipv4_output = []  # IPv4アドレス範囲を保存するリスト
    ipv6_output = []  # IPv6アドレス範囲を保存するリスト

    # 最後に見つかった国のコードを保存する変数
    last_country = None

    # ファイルから読み取った各行に対する処理
    for line in lines:
        parts = line.split("|")

        # 最初の欄が 'apnic' でない場合、この行はスキップする
        if parts[0] != "apnic":
            continue

        # 国のコードが空白でなければ更新、空白であれば最後に見つかった国のコードを使用
        country = parts[1] if parts[1] != "" else last_country

        ip_type = parts[2]
        ip_start = parts[3]
        try:
            ip_size = int(parts[4])
        except ValueError:
            print(f"エラーが発生した行: {line}")
            continue

        # 日本（JP）のIPアドレス範囲の場合
        if country == "JP":
            if ip_type == "ipv4":
                # CIDR表記を計算する
                ip_net = ipaddress.ip_network(
                    f"{ip_start}/{32-int(math.log2(ip_size))}", strict=False
                )
                ipv4_output.append(str(ip_net))
            elif ip_type == "ipv6":
                # 修正: ip_sizeがプレフィックス長そのものであるため、そのまま使用する
                ip_net = ipaddress.ip_network(f"{ip_start}/{ip_size}", strict=False)
                ipv6_output.append(str(ip_net))

        # 最後に見つかった国のコードを更新
        last_country = country

    return ipv4_output, ipv6_output  # IPv4とIPv6のアドレス範囲を返す


def update_data_and_settings(settings, fetched_unix_timestamp):
    # 新しいデータを取得し、整理する
    try:
        with urllib.request.urlopen(url) as response:
            raw_data = response.read().decode("utf-8")
            # コメント行を削除する
            data_lines = [
                line
                for line in raw_data.split("\n")
                if not line.startswith("#") and line
            ]
            ipv4_output, ipv6_output = process_data(data_lines)
        # ipv4_output, ipv6_output = merge_ip_ranges(ipv4_output), merge_ip_ranges(
        #    ipv6_output
        # )

    except Exception as e:
        print(f"データの取得と処理中にエラーが発生しました: {e}")
        return  # エラーが発生した場合、関数を終了する

    # 整理されたデータを保存する
    with open(os.path.join(SETTING_FOLDER, "ipv4.txt"), "w", encoding="utf-8") as file:
        file.write("\n".join(ipv4_output))
    with open(os.path.join(SETTING_FOLDER, "ipv6.txt"), "w", encoding="utf-8") as file:
        file.write("\n".join(ipv6_output))

    # setting.jsonを更新する
    settings["ip_last_modified"] = fetched_unix_timestamp
    with open(SETTING_FILE, "w", encoding="utf-8") as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)
        print("IPアドレス範囲のデータを更新しました。")


def execute():
    try:
        # HTTPSリクエストを送信し、ヘッダーを取得
        with urllib.request.urlopen(url) as response:
            last_modified = response.headers.get("Last-Modified")

        if last_modified:
            # 'Last-Modified'ヘッダーの日付をUNIXタイムコードに変換
            last_modified_datetime = parsedate_to_datetime(last_modified)
            fetched_unix_timestamp = int(last_modified_datetime.timestamp())

            # setting.jsonファイルを読み込む
            if os.path.exists(SETTING_FILE):
                with open(SETTING_FILE, "r", encoding="utf-8") as file:
                    settings = json.load(file)

                # 'ip_last_modified'項目を比較する
                existing_unix_timestamp = settings.get("ip_last_modified")
                if existing_unix_timestamp:
                    if fetched_unix_timestamp > existing_unix_timestamp:
                        update_data_and_settings(settings, fetched_unix_timestamp)
                    elif fetched_unix_timestamp == existing_unix_timestamp:
                        print("IPアドレス一覧の更新はありませんでした。")
                    else:
                        print("エラー: setting.json内のIPアドレス更新日時のほうが新しい状態です。")
                else:
                    print("新たにIPアドレス一覧を取得しています...")
                    update_data_and_settings(settings, fetched_unix_timestamp)
            else:
                print(f"エラー: {SETTING_FILE}が存在しません。")

        else:
            print('エラー: このURLでは"Last-Modified"ヘッダーは利用できません。')

    except Exception as e:
        print(f"エラーが発生しました: {e}")
