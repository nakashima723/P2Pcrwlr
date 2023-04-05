import libtorrent as lt
import time
import ntplib
from datetime import datetime, timezone, timedelta


class Client():

    def download(self, torrent_path, save_path):
        """
        指定した.torrentファイルをもとに本体ファイルをダウンロードする。

        Parameters
        ----------
        torrent_path : str
            ダウンロードを行うtorrentファイルへのパス。
        save_path : str
            本体ファイルのダウンロード先のパス。
        """

        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({'ti': info, 'save_path': save_path})

        print('starting', handle.status().name)

        while not handle.status().is_seeding:
            print_download_status(handle.status(), handle.get_peer_info())

            for p in handle().get_peer_info():
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

    def download_piece(self, torrent_path, save_path, piece_index):
        """
        指定した.torrentファイルからひとつのピースをダウンロードする。

        Parameters
        ----------
        torrent_path : str
            .torrentファイルへのパス。
        save_path : str
            ファイルの保存場所のパス。
        piece_index : int
            ダウンロードしたいピースのindex。
        """

        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({'ti': info, 'save_path': save_path})

        initial_pieces_state = handle.status().pieces

        # deadlineに0を指定することで、指定したピースが優先的にダウンロードされるようにする
        handle.set_piece_deadline(piece_index, 0)

        while not handle.status().pieces[piece_index]:

            print_download_status(handle.status(), handle.get_peer_info())

            time.sleep(1)

        # ピースのダウンロードが完了したら、ピースの状態を出力
        last_pieces_state = handle.status().pieces
        print(f'piece {piece_index} downloaded')
        print(f'pieces state before: {initial_pieces_state}')
        print(f'pieces state after: {last_pieces_state}')


def print_download_status(torrent_status, peer_info):
    print(
        "downloading: %.2f%% complete (down: %.1f kB/s, up: %.1f kB/s, peers: %d) %s" % (
            torrent_status.progress * 100,
            torrent_status.download_rate / 1000,
            torrent_status.upload_rate / 1000,
            len(peer_info), torrent_status.state)
    )
