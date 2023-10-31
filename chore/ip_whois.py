import socket
import re  # 正規表現を使用するためのライブラリをインポート


def query_jpnic_whois(ip_address):
    # JPNICのWHOISサービスに接続
    whois_server = "whois.nic.ad.jp"
    whois_port = 43
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((whois_server, whois_port))

    # IPアドレスの問い合わせを行う
    sock.send((ip_address + "\r\n").encode("utf-8"))

    # 結果を受け取る
    data = b""
    while True:
        buffer = sock.recv(4096)
        data += buffer
        if not buffer:
            break
    sock.close()

    # 結果をJISエンコーディングでデコード
    result = data.decode("iso-2022-jp", "ignore")

    # 組織名を抽出
    match = re.search(r"\[組織名\]\s+(.+)", result)
    if match:
        organization_name = match.group(1)
        print(f"組織名は「{organization_name}」です。")
    else:
        print("組織名を取得できませんでした。")

    return result


# 使い方の例
if __name__ == "__main__":
    ip_address = "2001:268:9a93:e163:80d5:b2e8:f1d9:683c"  # 任意の日本のIPアドレス
    query_jpnic_whois(ip_address)
