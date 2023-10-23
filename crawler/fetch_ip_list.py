import ipaddress
import math
import os
import json
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
    ip_ranges = [ipaddress.ip_network(ip_range) for ip_range in ip_ranges]
    ip_ranges.sort(key=lambda x: x.network_address)
    merged_ranges = []
    current_range = ip_ranges[0]

    for ip_range in ip_ranges[1:]:
        if (
            current_range.overlaps(ip_range)
            or current_range.broadcast_address + 1 == ip_range.network_address
        ):
            # collapse_addressesの結果をリストに変換し、最初の要素を取得する
            current_range = list(
                ipaddress.collapse_addresses([current_range, ip_range])
            )[0]
        else:
            merged_ranges.append(str(current_range))
            current_range = ip_range

    merged_ranges.append(str(current_range))
    return merged_ranges


def process_data(data):
    ipv4_output = []
    ipv6_output = []

    for line in data:
        fields = line.split("|")

        # データ行のバリデーションチェック: 最初の範囲が'apnic'でなければスキップ、2番目の範囲が'*'であればスキップ
        if fields[0] != "apnic" or fields[1] == "*":
            continue

        country = fields[1]
        ip_type = fields[2]
        ip_start = fields[3]

        # ip_sizeが空または数値でない場合はエラーメッセージを出力してスキップ
        try:
            ip_size = int(fields[4])
        except ValueError:
            print(f"Invalid ip_size value: {line}")
            continue

        if country == "JP":
            if ip_type == "ipv4":
                # CIDR表記を計算する
                ip_net = ipaddress.ip_network(
                    f"{ip_start}/{32-int(math.log2(ip_size))}", strict=False
                )
                ipv4_output.append(str(ip_net))
            elif ip_type == "ipv6":
                # CIDR表記を計算する
                ip_net = ipaddress.ip_network(
                    f"{ip_start}/{128-int(math.log2(ip_size))}", strict=False
                )
                ipv6_output.append(str(ip_net))

    return ipv4_output, ipv6_output


def update_data_and_settings():
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
            ipv4_output, ipv6_output = merge_ip_ranges(ipv4_output), merge_ip_ranges(
                ipv6_output
            )

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
                    update_data_and_settings()
                elif fetched_unix_timestamp == existing_unix_timestamp:
                    print("IPアドレス一覧の更新はありませんでした。")
                else:
                    print("エラー: setting.json内のIPアドレス更新日時のほうが新しい状態です。")
            else:
                print("新たにIPアドレス一覧を取得しています...")
                update_data_and_settings()
        else:
            print(f"エラー: {SETTING_FILE}が存在しません。")

    else:
        print('エラー: このURLでは"Last-Modified"ヘッダーは利用できません。')

except Exception as e:
    print(f"エラーが発生しました: {e}")
