import libtorrent as lt
import os
import csv
import time
import ntplib
from datetime import datetime, timezone, timedelta


class Client():
    def __init__(self):
        # 重複するピアを記録する必要はないため、集合として定義
        self.peer_info = set()

    def add_peer_info(self, torrent_handle):
        """
        torrent_handleに含まれるピア情報を記録する。

        Parameters
        ----------
        torrent_handle : torrent_handle
        ピア情報を記録する対象のtorrent_handle。
        """
        for p in torrent_handle.get_peer_info():
            self.peer_info.add(p.ip)

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
            self.add_peer_info(handle)
            time.sleep(1)

        with open(os.path.join(save_path, 'peer.csv'), mode='a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for ip in self.peer_info:
                writer.writerow([ip[0], ip[1]])

        print(handle.status().name, 'complete')
        print("File Hash: %s, File size: %d, Time: %s" % (
            handle.info_hash(), info.total_size(), fetch_jst().strftime('%Y-%m-%d %H:%M:%S')))

    def download_piece(self, torrent_path, save_path, piece_index, peer):
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
        peer : (string, int)
            ピースをダウンロードするピア。
        """

        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        # 指定されたピアのみからダウンロードするために、ipフィルタを作成する
        ip_filter = lt.ip_filter()

        # まずすべてのアドレスを禁止してから、引数で指定したアドレスのみ許可。
        # 第三引数の0は許可するアドレス指定、1は禁止するアドレス指定
        ip_filter.add_rule('0.0.0.0', '255.255.255.255', 1)
        ip_filter.add_rule(peer[0], peer[0], 0)

        print(ip_filter.export_filter())

        session.set_ip_filter(ip_filter)

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({'ti': info, 'save_path': save_path})

        initial_pieces_state = handle.status().pieces

        # deadlineに0を指定することで、指定したピースが優先的にダウンロードされるようにする
        handle.set_piece_deadline(piece_index, 0)

        retry_counter = 0
        while not handle.status().pieces[piece_index]:
            # torrent_handle.status().piecesの戻り値はboolの配列なので、この条件で判定できる
            print_download_status(handle.status(), handle.get_peer_info())
            print('piece {}: {}'.format(piece_index, handle.status().pieces[piece_index]))

            # alertの出力を行う
            alerts = session.pop_alerts()
            for a in alerts:
                if a.category() & lt.alert.category_t.error_notification:
                    print(a)

            time.sleep(1)

            if handle.status().num_peers == 0:
                retry_counter += 1

            if retry_counter >= 10:
                print('Max retries exceeded')
                break

        handle.read_piece(piece_index)

        # msで指定する
        session.wait_for_alert(1000)
        alerts = session.pop_alerts()
        for a in alerts:
            if isinstance(a, lt.read_piece_alert):
                print('piece read')
                write_piece_to_file(a.buffer, os.path.join(save_path, 'piece_{}.bin'.format(piece_index)))

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


def write_piece_to_file(piece, save_path):
    """
    ピースを指定されたパスに書き込む.

    Parameters
    ----------
    piece : bytes
        ピースのバイト列。

    save_path : str
        保存先ファイルのパス。
    """
    with open(save_path, 'wb') as f:
        f.write(piece)


def fetch_jst():
    """
    NTPサーバからUNIX時刻を取得し、JSTに変換して返却する。

    Returns
    -------
        jst_time: datetime
        JSTを表すdatetime。
    """
    # NTPサーバのアドレスを指定する
    ntp_server = 'ntp.nict.jp'

    # NTPサーバからUNIX時刻を取得する
    ntp_client = ntplib.NTPClient()
    response = ntp_client.request(ntp_server)
    unix_time = response.tx_time

    # UNIX時刻をJSTに変換する
    jst = timezone(timedelta(hours=+9), 'JST')
    jst_time = datetime.fromtimestamp(unix_time, jst)

    return jst_time
