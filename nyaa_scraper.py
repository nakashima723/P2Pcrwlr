import functions

input_str = input("検索語を入力してください: ")
output_str = process_query(input_str)
output_str = urllib.parse.quote(output_str)
print('検索語：' + output_str)

url = 'https://nyaa.si/?f=0&c=0_0&q=' + output_str
response = urllib.request.urlopen(url)

# responseオブジェクトからデコード済みのテキストを取得
html_content = response.read().decode(response.headers.get_content_charset())

soup = BeautifulSoup(html_content, 'html.parser')
# 'data-timestamp' クラスを持つtable dataの text contentを抽出
data_timestamp_elements = soup.find_all('td', attrs={'data-timestamp': True})

if len(data_timestamp_elements) == 0:
    print("アップロードされたファイルは見つかりませんでした。")
else:
    converted_dates = []

    for element in data_timestamp_elements:
        timestamp_str = element.get_text()
        timestamp_str = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M').replace(tzinfo=timezone.utc)

        if not is_within_days(timestamp_str):
            break
        else:
            datetime_jst = utc_to_jst(timestamp_str)
            converted_dates.append(datetime_jst)

    print('90日以内にアップロードされたファイル:')
    for date in converted_dates:
        formatted_date = date.strftime('%Y-%m-%d %H:%M')
        print(formatted_date)