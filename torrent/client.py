import libtorrent as lt
from datetime import datetime, timezone
import os
import requests
import sys
import time
import tempfile
import logging
import utils.time as ut
import csv
import socket
import urllib.parse
import random
import ipaddress


class Client:
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def download(self, torrent_path: str, save_path: str) -> None:
        """
        指定した.torrentファイルをもとに本体ファイルをダウンロードする。

        Parameters
        ----------
        torrent_path : str
            .torrentファイルへのパス。
        save_path : str
            本体ファイルのダウンロード先のパス。
        """
        info = lt.torrent_info(torrent_path)
        target_file_path = os.path.join(save_path, info.name())

         # .download_skip ファイルのパスを組み立てる
        skip_file_path = os.path.join(save_path, ".download_skip")

        # .download_skip ファイルが存在する場合、ダウンロードを行わない
        if os.path.exists(skip_file_path):
            self.logger.info("本体ファイルのダウンロードをスキップ: %s", target_file_path)
            return

        # すでにDL対象のファイル・フォルダが存在する場合、そのサイズを取得
        def get_size(path: str) -> int:
            if os.path.isfile(path):  # パスが単一のファイルの場合
                return os.path.getsize(path)
            
            total = 0  # パスがディレクトリの場合
            for dirpath, dirnames, filenames in os.walk(path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total += os.path.getsize(fp)
            return total
            
        # 期待されるサイズと一致する場合、新規ダウンロードを行わない
        if os.path.exists(target_file_path) and get_size(target_file_path) == info.total_size():
            self.logger.info("本体ファイルはダウンロード済み %s", target_file_path)
            return

        session = lt.session({"listen_interfaces": "0.0.0.0:6881,[::]:6881"})

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({"ti": info, "save_path": save_path})

        self.logger.info("starting %s", handle.status().name)

        while not handle.status().is_seeding:
            _print_download_status(handle.status(), self.logger)
            time.sleep(1)

        self.logger.info("complete %s", handle.status().name)
        self.logger.info(
            "File Hash: %s, File size: %d, Time: %s"
            % (
                handle.info_hash(),
                info.total_size(),
                ut.utc_to_jst(datetime.now()).strftime("%Y-%m-%d %H:%M:%S"),
            )
        )

    def fetch_peer_list(
        self, torrent_path: str, max_list_size: int = 20
    ) -> list[tuple[str, int]]:
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
        RETRY_COUNTER = 10

        session = lt.session({"listen_interfaces": "0.0.0.0:6881,[::]:6881"})
        info = lt.torrent_info(torrent_path)

        peers: list[tuple[str, int]] = []

        # _get_public_ips()を一度だけ呼び出し、結果を2つの変数に格納
        ipv4, ipv6 = _get_public_ips()

        with tempfile.TemporaryDirectory() as tmpdir:
            handle = session.add_torrent({"ti": info, "save_path": tmpdir})

            cnt = 0
            while cnt < RETRY_COUNTER:
                for p in handle.get_peer_info():
                    # p.ip[0]が自分自身の公開IPv4またはIPv6アドレスではないことを確認
                    if p.seed and p.ip not in peers and p.ip[0] != ipv4 and p.ip[0] != ipv6:
                        if _ip_in_range(p.ip[0]) or (_ip_in_range(p.ip[0]) is None):
                            peers.append(p.ip)
                cnt += 1
                time.sleep(1)
            return peers[:max_list_size]

    def download_piece(
        self, torrent_path: str, save_path: str, peer: tuple[str, int]
    ) -> None:
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
        session = lt.session({"listen_interfaces": "0.0.0.0:6881,[::]:6881"})

        # torrentファイルを読み込む
        info = lt.torrent_info(torrent_path)

        # トラッカーの一覧を取得
        trackers = info.trackers()

        # 指定されたピアのみからダウンロードするために、ipフィルタを作成する
        ip_filter = lt.ip_filter()

        # まずすべてのアドレスを禁止してから、引数で指定したアドレスとトラッカーのアドレスのみ許可する
        ip_filter.add_rule("0.0.0.0", "255.255.255.255", 1)
        ip_filter.add_rule("::", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", 1)
        ip_filter.add_rule(peer[0], peer[0], 0)

        # 各トラッカーのIPアドレスを取得し、許可リストに追加
        for tracker in trackers:
            url = tracker.url
            parsed_url = urllib.parse.urlparse(url)
            hostname = parsed_url.hostname
            port = parsed_url.port
            try:
                addr_infos = socket.getaddrinfo(hostname, port)
                for family, type, proto, canonname, sockaddr in addr_infos:
                    tracker_ip = sockaddr[0]
                    ip_filter.add_rule(tracker_ip, tracker_ip, 0)
            except socket.gaierror:
                # ホスト名を解決できない場合、スキップする
                pass

        session.set_ip_filter(ip_filter)

        with tempfile.TemporaryDirectory() as tmpdir:
            handle = session.add_torrent({"ti": info, "save_path": tmpdir})

            # 全てのピースからランダムに1つ選ぶ
            piece_index = random.randint(0, info.num_pieces() - 1)

            # 指定したindexのみpriorityを非ゼロにする。
            # その他はpriority=0にする（ダウンロードしない）。
            pp = [0] * info.num_pieces()
            pp[piece_index] = 1
            handle.prioritize_pieces(pp)

            self.__wait_for_piece_download(session, handle, piece_index, 10)

            handle.read_piece(piece_index)

            # msで指定する
            session.wait_for_alert(1000)
            alerts = session.pop_alerts()
            for a in alerts:
                if isinstance(a, lt.read_piece_alert):
                    self.logger.info("piece read")
                    _save_prior_peer(peer, os.path.join(save_path, "peer.csv"))
                    peer_modified = (
                        peer[0].replace(":", "-") if ":" in peer[0] else peer[0]
                    )

                    file_path = os.path.join(
                        save_path,
                        f"{peer_modified}_{str(peer[1])}",
                        "{:05}_{}_{}_{}.bin".format(
                            piece_index, peer_modified, peer[1], info.info_hash()
                        ),
                    )

                    unique_file_path = _get_unique_filename(file_path)
                    _write_piece_to_file(a.buffer, unique_file_path)

                    _write_peer_log(
                        info,
                        peer,
                        piece_index,
                        os.path.join(
                            save_path,
                            f"{peer_modified}_{str(peer[1])}",
                            "{}_{}_{}.log".format(
                                peer_modified, str(peer[1]), info.info_hash()
                            ),
                        ),
                    )

    def __wait_for_piece_download(
        self, session, torrent_handle, piece_index: int, max_retries: int
    ):
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
            session.pop_alerts()
            # for a in alerts:
            #    if a.category() & lt.alert.category_t.error_notification:
            #        self.logger.warning(a)

            current_progress = torrent_handle.status().progress_ppm

            if current_progress <= recent_progress:
                # この場合、ダウンロードが進行していないと見なす
                retry_counter += 1

            if retry_counter >= max_retries:
                self.logger.warning("Max retries exceeded")
                break

            recent_progress = current_progress

            time.sleep(1)


def _print_download_status(torrent_status, logger: logging.Logger) -> None:
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
        "%.2f%% complete (down: %.1f kB/s, up: %.1f kB/s, peers: %d)"
        % (
            torrent_status.progress * 100,
            torrent_status.download_rate / 1000,
            torrent_status.upload_rate / 1000,
            torrent_status.num_peers,
        )
    )


def _write_piece_to_file(piece: bytes, save_path: str) -> None:
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
    with open(save_path, "wb") as f:
        f.write(piece)


def _write_peer_log(
    torrent_info, peer: tuple[str, int], piece_index: int, save_path: str
) -> None:
    
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

    def get_jst_str():
        try:
            jst = ut.fetch_jst()
        except ut.TimeException:
            jst = None

        if jst is None:
            return "エラー NTPサーバーから時刻を取得できませんでした。"
        
        return jst.strftime("%Y-%m-%d %H:%M:%S")

    peer_modified = peer[0].replace(":", "-") if ":" in peer[0] else peer[0]
    file_mode = "w" if not os.path.exists(save_path) else "a"
    
    with open(save_path, file_mode) as f:
        if file_mode == "w":
            # 新規ファイルの場合はヘッダーを書き込み
            f.write(f"{peer_modified}_{peer[1]}_{torrent_info.name()}\n")
            f.write(f"ファイルハッシュ: {torrent_info.info_hash()}\n")
            f.write(f"証拠収集開始時刻: {get_jst_str()}\n")
            f.write("---\n")
        
        f.write(f"piece{piece_index} 完了時刻: {get_jst_str()}\n")


def _save_prior_peer(peer: tuple[str, int], save_path: str) -> None:
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
        with open(save_path, "r") as f:
            reader = csv.reader(f)
            # peerは (str, int) 型なので読み込んだ値を型変換する
            existing_peers = [(row[0], int(row[1])) for row in reader]

    if peer not in existing_peers:
        with open(save_path, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(peer)


# 当該IPアドレスが指定した範囲内に存在するかを確認


def _ip_in_range(ip) -> bool:
    """
    指定されたIPアドレスが、設定ファイル（ipv4.txt, ipv6.txt）の範囲に収まっているかを返す。

    Parameters
    ----------
    ip : str
        判定対象のIPアドレス。
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        print(f"The IP address {ip} is invalid.")
        return False

    # 設定フォルダへのパスを指定
    if getattr(sys, "frozen", False):
        SETTING_FOLDER = sys._MEIPASS
    else:
        main_script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        parent_dir = os.path.dirname(main_script_dir)
        SETTING_FOLDER = os.path.join(parent_dir, "settings")

    # IPv4なのかIPv6なのかを判定
    ip_range_file = ""
    if ip_obj.version == 4:
        ip_range_file = os.path.join(SETTING_FOLDER, "ipv4.txt")
    else:
        ip_range_file = os.path.join(SETTING_FOLDER, "ipv6.txt")

    if not os.path.exists(ip_range_file):
        return None

    # ipがファイルの内容に含まれているかを判定
    with open(ip_range_file, "r") as f:
        ip_ranges = f.readlines()

    for ip_range in ip_ranges:
        ip_range = ip_range.strip()
        if (
            ipaddress.ip_network(ip_range, strict=False).network_address
            <= ip_obj
            <= ipaddress.ip_network(ip_range, strict=False).broadcast_address
        ):
            return True
    return False

def _get_public_ips() -> tuple[str, str]:
    ipv4 = None
    ipv6 = None
    try:
        # For IPv4
        response_ipv4 = requests.get("https://api.ipify.org?format=json")
        ipv4 = response_ipv4.json().get("ip")
        # For IPv6
        response_ipv6 = requests.get("https://api6.ipify.org?format=json")
        ipv6 = response_ipv6.json().get("ip")
    except:
        pass
    return ipv4, ipv6

def _get_unique_filename(path):
    """指定されたパスのファイルが存在する場合、連番を追加して新しいパスを返す。"""
    if not os.path.exists(path):
        return path
    else:
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"