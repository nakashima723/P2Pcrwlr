import os
import hashlib
import bencodepy
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


def get_info_hash(torrent_file):
    with open(torrent_file, 'rb') as f:
        torrent_data = bencodepy.decode(f.read())
        
    info = torrent_data[b'info']
    info_bencoded = bencodepy.encode(info)
    info_hash = hashlib.sha1(info_bencoded).hexdigest()

    return info_hash

def save_webpage_as_html(site_url, output_file, folder_name):
    os.makedirs(folder_name, exist_ok=True)
        
    uri = "?q="
    url = site_url + uri + info_hash
    
    # URLからコンテンツを取得
    response = requests.get(url)

    # リダイレクト先のURLを取得
    redirected_url = response.url

    unique_url = site_url + "view"

    # リダイレクト先のURLが特定の形であるかをチェック
    if redirected_url.startswith(unique_url):
        # レスポンスが成功した場合のみ処理を続行
        if response.status_code == 200:
            # BeautifulSoupを使用してHTMLを整形
            soup = BeautifulSoup(response.content, "html.parser")

            # HTML内のCSSファイルへのリンクを見つける
            for link in soup.find_all("link", rel="stylesheet"):
                css_url = urljoin(redirected_url, link["href"])
                css_response = requests.get(css_url)

                # クエリパラメータを除去してファイル名を抽出
                parsed_css_url = urlparse(css_url)
                css_filename = os.path.basename(parsed_css_url.path)

                css_filepath = os.path.join(folder_name, css_filename)

                # CSSファイルをダウンロードして、指定されたフォルダに保存する
                with open(css_filepath, "wb") as css_file:
                    css_file.write(css_response.content)

                # HTMLファイル内のCSSリンクを更新する
                link["href"] = css_filename

            # HTMLファイルとしてローカルに保存
            output_path = os.path.join(folder_name, output_file)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(str(soup.prettify()))
        else:
            print(f"エラー: Failed to fetch the content with status code {response.status_code}")
    else:
        print("エラー: このファイルの情報は"+ site_url +"内に存在しません。")

torrent_file = 'source.torrent'
info_hash = get_info_hash(torrent_file)
print("Info hash: ", info_hash)

site_url = "https://nyaa.si/"
output_file = "complete_evidence.html"
folder_name = "complete_evidence"

save_webpage_as_html(site_url, output_file, folder_name)