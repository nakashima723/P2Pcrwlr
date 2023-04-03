import libtorrent as lt
import time
import ntplib
from datetime import datetime, timezone, timedelta


class Client():

    def download(self, torrent_path, save_path):
        """
        torrentファイルを読み込み、本体ファイルをダウンロードする。

        Parameters
        ----------
        torrent_path : str
        ダウンロードを行うtorrentファイルへのパス。
        save_path : str
        実ファイルのダウンロード先のパス。
        """

        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({'ti': info, 'save_path': save_path})

        print('starting', handle.status().name)

        while not handle.status().is_seeding:
            s = handle.status()

            peer_info = handle.get_peer_info()

            print("downloading: %.2f%% complete (down: %.1f kB/s, up: %.1f kB/s, peers: %d) %s" % (
                s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000,
                len(peer_info), s.state))

            for p in peer_info:
                print("IP address: %s   Port: %d" % (p.ip[0], p.ip[1]))

            time.sleep(1)

        # NTPサーバのアドレスを指定する
        ntp_server = 'ntp.nict.jp'

        # NTPサーバからUNIX時刻を取得する
        ntp_client = ntplib.NTPClient()
        response = ntp_client.request(ntp_server)
        unix_time = response.tx_time

        # UNIX時刻を日本時間に変換する
        jst = timezone(timedelta(hours=+9), 'JST')
        jst_time = datetime.fromtimestamp(unix_time, jst)

        print(handle.status().name, 'complete')
        print("File Hash: %s, File size: %d, Time: %s" % (
            handle.info_hash(), info.total_size(), jst_time.strftime('%Y-%m-%d %H:%M:%S')))
