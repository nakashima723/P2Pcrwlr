# P2Pcrwlr
P2Pクローラ

「プロバイダ責任制限法ガイドライン」の認定要件を満たす、P2P違法アップロードの検出ソフトを製作します。

各ユーザーのPC上で動作させられるものにします。

<strong>参考１：P2Pファイル交換ソフトによる権利侵害情報の流通に関する検知システムの認定について</strong>
https://www.telesa.or.jp/consortium/provider/p2ptechreq/

<blockquote>
<strong>１．認定対象</strong>


(ア) 以下のすべての機能を備えているシステムとする。

① Ｐ２Ｐ型ファイル交換ソフトのネットワークに接続する機能
② 当該ネットワークから利用者が指定するファイルをダウンロードする機能
③ ダウンロード時に発信元ノード（ユーザの PC 等）のＩＰアドレス，ポート番
号，ファイルハッシュ値，ファイルサイズ，ダウンロード完了時刻等（以下「メ
タデータ」という。）を自動的にデータベースに記録する機能。


(イ) ダウンロードしたファイルが、一度利用者により権利侵害情報と判定されたファ
イルと同一のファイルであるかどうかを比較検証する機能（以下「比較検証機能」
という）を有する場合、当該機能も認定を受けることができる。


注：ファイル交換ソフトネットワーク上をクローリングし、利用者が指定するキーワー
ドや属性に合致するファイルを自動ダウンロードする機能は必須機能ではない。</blockquote>


<strong>参考２：BitTorrent ネットワークにおける効率的な著作権侵害監視手法について </strong>

http://www.ccif-j.jp/shared/pdf/BitTrrentreport.pdf

<strong>参考３：P2Pソフトを解析し，活用に向けての可能性を探る（日経クロステック） </strong>

https://xtech.nikkei.com/it/article/COLUMN/20080922/315234/

運用メモ：

exe化の際には以下のようなコマンドを推奨する。

pyinstaller --onefile --add-binary "C:\libtorrent\build\Release\libssl-3-x64.dll;." --add-binary "C:\libtorrent\build\Release\libcrypto-3-x64.dll;." --add-binary "C:\libtorrent\build\Release\torrent-rasterbar.dll;." P2Pcrwlr.py

・libtorrentのdllをpyinstallerで収集できない場合、明示的に同梱する必要がある。ファイルパスは一例で、libtorrentのインストール先により変わる。
・アプリUI内にログを表示しないため、コンソールウィンドウは必要。

Windows環境でのlibtorrent導入はかなり手間がかかる。

https://libtorrent.org/building.html

ポイントは
・あらかじめBOOSTを導入しておく
・システム環境変数を適切に設定する

Macの場合は（環境によるかもしれないが）以下２行で済む。

brew install boost --build-from-source
brew install libtorrent-rasterbar
