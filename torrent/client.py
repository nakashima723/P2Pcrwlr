import libtorrent as lt
import os
import time
import tempfile
import logging
import utils.time as ut
import csv


class Client():
    def __init__(self):
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def download(self, torrent_path, save_path):
        """
        指定した.torrentファイルをもとに本体ファイルをダウンロードする。

        Parameters
        ----------
        torrent_path : str
            .torrentファイルへのパス。
        save_path : str
            本体ファイルのダウンロード先のパス。
        """
        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({'ti': info, 'save_path': save_path})

        self.logger.info('starting %s', handle.status().name)

        while not handle.status().is_seeding:
            _print_download_status(handle.status(), self.logger)
            time.sleep(1)

        self.logger.info('complete %s', handle.status().name)
        self.logger.info("File Hash: %s, File size: %d, Time: %s" % (
            handle.info_hash(), info.total_size(), ut.fetch_jst().strftime('%Y-%m-%d %H:%M:%S')))

    def fetch_peer_list(self, torrent_path, max_list_size=20):
        """
        swarmに含まれるpeerのリストを取得する。
        swarm: all peers (including seeds) sharing a torrent

        Parameters
        ----------
        torrent_path : str
            .torrentファイルへのパス。
        max_list_size : int
            取得されるピアのリストの最大長。

        Returns
        -------
        peers : list of (str, int)
            ピアのリスト。
        """
        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})
        info = lt.torrent_info(torrent_path)

        peers = []
        with tempfile.TemporaryDirectory() as tmpdir:
            handle = session.add_torrent({'ti': info, 'save_path': tmpdir})
            while len(peers) < max_list_size:
                for p in handle.get_peer_info():
                    if p.seed and (p.ip not in peers):
                        peers.append(p.ip)
        return peers[:max_list_size]

    def download_piece(self, torrent_path, save_path, piece_index, peer):
        """
        指定した.torrentファイルからひとつのピースをダウンロードする。

        Parameters
        ----------
        torrent_path : str
            .torrentファイルへのパス。
        save_path : str
            ピースを保存するディレクトリのパス。
            この引数で指定したディレクトリの直下に'IP_ポート番号'フォルダが作成され、その中にピースが保存される。
        piece_index : int
            ダウンロードしたいピースのindex。
        peer : (str, int)
            ピースをダウンロードするピア。
        """
        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        # 指定されたピアのみからダウンロードするために、ipフィルタを作成する
        ip_filter = lt.ip_filter()

        # まずすべてのアドレスを禁止してから、引数で指定したアドレスのみ許可する
        # 第三引数の0は許可するアドレス指定、1は禁止するアドレス指定
        ip_filter.add_rule('0.0.0.0', '255.255.255.255', 1)
        ip_filter.add_rule('::', 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', 1)
        ip_filter.add_rule(peer[0], peer[0], 0)

        self.logger.info(ip_filter.export_filter())

        session.set_ip_filter(ip_filter)

        info = lt.torrent_info(torrent_path)

        with tempfile.TemporaryDirectory() as tmpdir:
            handle = session.add_torrent({'ti': info, 'save_path': tmpdir})

            # 指定したindexのみpriorityを非ゼロにする。
            # その他はpriority=0にする（ダウンロードしない）。
            pp = [0]*info.num_pieces()
            pp[piece_index] = 1
            handle.prioritize_pieces(pp)

            self.__wait_for_piece_download(session, handle, piece_index, 10)

            handle.read_piece(piece_index)

            # msで指定する
            session.wait_for_alert(1000)
            alerts = session.pop_alerts()
            for a in alerts:
                if isinstance(a, lt.read_piece_alert):
                    self.logger.info('piece read')
                    _save_prior_peer(peer, os.path.join(save_path, 'peer.csv'))

                    _write_piece_to_file(a.buffer, os.path.join(
                        save_path,
                        f'{peer[0]}_{str(peer[1])}',
                        '{:05}_{}_{}_{}.bin'.format(piece_index, peer[0], peer[1], info.name())
                    ))

                    _write_peer_log(
                        info, peer, piece_index, os.path.join(
                            save_path,
                            f'{peer[0]}_{str(peer[1])}',
                            '{}_{}_{}.log'.format(peer[0], str(peer[1]), info.name())
                        )
                    )

    def __wait_for_piece_download(self, session, torrent_handle, piece_index, max_retries):
        """
        ピースのダウンロードが完了するまで待機する。

        Parameters
        ----------
        session : session
            https://www.libtorrent.org/reference-Session.html#session
        torrent_handle : torrent_handle
            https://www.libtorrent.org/reference-Torrent_Handle.html#torrent_handle
        piece_index : int
            ダウンロードするピースのindex。
        max_retries : int
            ピアからのダウンロードが進行しない場合に、リトライを試みる回数。
        """
        retry_counter = 0
        recent_progress = 0

        while not torrent_handle.status().pieces[piece_index]:
            # torrent_handle.status().piecesの戻り値はboolの配列なので、この条件で判定できる

            _print_download_status(torrent_handle.status(), self.logger)

            # alertの管理を行う
            alerts = session.pop_alerts()
            for a in alerts:
                if a.category() & lt.alert.category_t.error_notification:
                    self.logger.warning(a)

            current_progress = torrent_handle.status().progress_ppm

            if current_progress <= recent_progress:
                # この場合、ダウンロードが進行していないと見なす
                retry_counter += 1

            if retry_counter >= max_retries:
                self.logger.warning('Max retries exceeded')
                break

            recent_progress = current_progress

            time.sleep(1)


def _print_download_status(torrent_status, logger):
    """
    ダウンロード状況を表示する。
    フォーマットは以下の通り。
        x% complete (down: x.x kB/s, up: x.x kB/s, peers: x)

    Parameters
    ----------
    torrent_status : torrent_status
        torrentの状況のスナップショットを保持するクラス。
        https://www.libtorrent.org/reference-Torrent_Status.html#torrent_status

    logger : Logger
        ロガー。
    """
    logger.info(
        "%.2f%% complete (down: %.1f kB/s, up: %.1f kB/s, peers: %d)" % (
            torrent_status.progress * 100,
            torrent_status.download_rate / 1000,
            torrent_status.upload_rate / 1000,
            torrent_status.num_peers
        )
    )


def _write_piece_to_file(piece, save_path):
    """
    ピースを指定されたパスに書き込む.

    Parameters
    ----------
    piece : bytes
        ピースのバイト列。

    save_path : str
        保存先ファイルのパス。
    """
    dir = os.path.dirname(save_path)
    os.makedirs(dir, exist_ok=True)
    with open(save_path, 'wb') as f:
        f.write(piece)


def _write_peer_log(torrent_info, peer, piece_index, save_path):
    """
    ピアごとのピースのダウンロードログを、指定されたファイルに書き込む。
    指定されたファイルがまだ存在しない場合は新規作成してヘッダーを書き込む。
    指定されたファイルがすでに存在する場合は、追記する。

    Parameters
    ----------
    torrent_info : torrent_info
        .torrentファイルの情報を保持するクラス。
        https://www.libtorrent.org/reference-Torrent_Info.html#torrent_info
    peer : (str, int)
        ピアを表すタプル。
    piece_index : int
        ダウンロードするピースのindex。
    save_path : str
        ログを書き込むファイルのパス。
    """
    if not os.path.exists(save_path):
        # ファイルが存在しない場合は作成してヘッダーを書き込み
        with open(save_path, 'w') as f:
            f.write('{}_{}_{}\n'.format(peer[0], str(peer[1]), torrent_info.name()))
            f.write('ファイルハッシュ: {}\n'.format(torrent_info.info_hash()))
            f.write('証拠収集開始時刻: {}\n'.format(ut.fetch_jst().strftime('%Y-%m-%d %H:%M:%S')))
            f.write('---\n')

    with open(save_path, 'a') as f:
        f.write('piece{} 完了時刻: {}\n'
                .format(
                    piece_index,
                    ut.fetch_jst().strftime('%Y-%m-%d %H:%M:%S'),
                ))


def _save_prior_peer(peer, save_path):
    """
    ピアを優先接続の対象としてファイルに記録する。

    Parameters
    ----------
    peer : (str, int)
        ピアを表すタプル。
    save_path : str
        記録ファイルのパス。
    """
    existing_peers = []

    if os.path.exists(save_path):
        # 重複を避けるために、すでにファイルが存在している場合は記録されたピアを読み込む
        with open(save_path, 'r') as f:
            reader = csv.reader(f)
            # peerは (str, int) 型なので読み込んだ値を型変換する
            existing_peers = [(row[0], int(row[1])) for row in reader]

    if peer not in existing_peers:
        with open(save_path, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(peer)
