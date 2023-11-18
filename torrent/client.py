# 標準ライブラリ
import csv
from datetime import datetime
import hashlib
import ipaddress
from ipaddress import ip_address, ip_network
import json
import logging
import os
import random
import re
import shutil
import socket
import tempfile
import time
import urllib.parse

# サードパーティライブラリ
import libtorrent as lt
import requests
from requests.exceptions import RequestException

# 独自モジュール
from utils.config import Config
import utils.time as ut


class Client:
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        con = Config(base_path=current_dir, level=1)
        self.my_port = con.MY_PORT
        self.version = con.version
        self.logger = logging.getLogger(__name__)
        self.piece_download = read_piece_download_setting()

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
            return False

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
        if (
            os.path.exists(target_file_path)
            and get_size(target_file_path) == info.total_size()
        ):
            self.logger.info("本体ファイルDL済： %s", os.path.basename(target_file_path))
            return True

        session = lt.session(
            {"listen_interfaces": f"0.0.0.0:{self.my_port},[::]:{self.my_port}"}
        )
        self.logger.info("本体ファイル" + target_file_path + "のダウンロードを行います。")

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({"ti": info, "save_path": save_path})

        # 進捗を追跡する変数
        last_downloaded = 0

        # 現在の時刻を記録
        last_time = time.time()

        self.logger.info("starting %s", handle.status().name)

        while not handle.status().is_seeding:
            current_status = handle.status()
            _print_download_status(current_status, self.logger)

            # 現在の進捗を取得
            current_downloaded = current_status.total_done

            # 現在の時刻を取得
            current_time = time.time()

            # 1分経過したかどうかを確認
            if current_time - last_time >= 30:
                # 進捗があるかどうかを確認
                if current_downloaded == last_downloaded:
                    self.logger.info("ダウンロードが進捗していないため、スキップします。")
                    return False

                # 進捗と時刻を更新
                last_downloaded = current_downloaded
                last_time = current_time

            time.sleep(1)

        self.logger.info("complete %s", handle.status().name)
        self.logger.info(
            "File Hash: %s, File size: %d, Time: %s"
            % (
                handle.info_hash(),
                info.total_size(),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        )
        return True

    def get_peer_log(
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
        session = lt.session(
            {"listen_interfaces": f"0.0.0.0:{self.my_port},[::]:{self.my_port}"}
        )

        info = lt.torrent_info(torrent_path)

        # 自分のIPを取得する_get_public_ips()を呼び出し、結果を2つの変数に格納
        ipv4, ipv6 = _get_public_ips()

        # IPv6アドレスの最初の4つのセクションを取得して除外リストに追加
        if ipv6:
            excluded_ipv6_network = get_excluded_ipv6(ipv6)

        ipv4_ranges = load_ip_ranges(4)
        ipv6_ranges = load_ip_ranges(6)

        # IP範囲ファイルが両方とも存在しない場合に、すべてのピアを追加するフラグ
        add_all_peers = not ipv4_ranges and not ipv6_ranges

        if not add_all_peers:
            ip_filter = _default_ip_filter(torrent_path)
            # IPv4とIPv6の範囲を許可リストに追加
            _add_ip_ranges_to_filter(ip_filter, ipv4_ranges, allow=True)
            _add_ip_ranges_to_filter(ip_filter, ipv6_ranges, allow=True)

            # excluded_ipv6_networkを禁止リストに追加
            if excluded_ipv6_network:
                start = str(excluded_ipv6_network[0])
                end = str(excluded_ipv6_network[-1])
                ip_filter.add_rule(start, end, 1)  # 1は禁止を意味する
            if ipv4:
                ip_filter.add_rule(ipv4, ipv4, 1)
            if ipv6:
                ip_filter.add_rule(ipv6, ipv6, 1)

        # ピア情報の取得時に使う一時フォルダの格納場所を、TORRENT_FOLDER内に作成
        torrent_folder = os.path.dirname(torrent_path)
        tmp_path = os.path.join(os.path.dirname(torrent_folder), "tmp")
        if not os.path.exists(tmp_path):
            os.makedirs(tmp_path, exist_ok=True)  # 自動削除に失敗しても、まとめて消せる格納用フォルダ

        peers: list[tuple[str, int]] = []  # 判定用にピアのIP（p.ip）だけを格納するリスト
        RETRY_COUNTER = 10
        log = []

        try:
            with tempfile.TemporaryDirectory(prefix="tmp", dir=tmp_path) as tmpdir:
                # 一時ファイルとして対象ファイルを作成し、ダウンロードの進捗0％からスタート
                handle = session.add_torrent({"ti": info, "save_path": tmpdir})
                handle.set_upload_limit(100000)  # アップロード速度を10KB/sに設定
                valid_piece = True  # 破損ピースが検出されていなければTrue

                # アラートをポーリングして破損したピースがあるかチェック
                alerts = session.pop_alerts()
                for alert in alerts:
                    if isinstance(alert, lt.hash_failed_alert):
                        valid_piece = False
                        break

                cnt = 0
                while cnt < RETRY_COUNTER:
                    try:
                        peer_info_list = handle.get_peer_info()  # 接続済みピアの情報を取得
                        timestamp = ut.get_jst_str()

                        for p in peer_info_list:
                            if not p.seed:
                                continue  # シーダーでなければ収録しない

                            key = (p.ip[0], p.ip[1])
                            if key in peers and p.last_active == 0:
                                p.timestamp = timestamp
                                p.valid = valid_piece
                                log.append(p)
                                continue  # すでに存在するピアは、最終接続時刻（int秒前）が0なら追加収録

                            peer_ip = p.ip[0]
                            if peer_ip == ipv4 or peer_ip == ipv6:
                                continue  # 自分自身のIPと一致する場合は収録しない

                            if (
                                not p.last_active == 0  # 最終接続時刻が0秒前のデータのみ収録
                                or p.up_speed <= 20  # プロトコルメッセージのみ（数KB）の通信である可能性を排除
                            ):
                                continue

                            # IPアドレスが同じでポート番号が異なるピアは、同じ周回では重複して収録しない
                            if any(peer[0] == peer_ip for peer in peers):
                                continue

                            if add_all_peers:  # IP範囲を問わず、シーダーをすべて収録する場合
                                if p.ip not in peers:
                                    p.timestamp = timestamp
                                    p.valid = valid_piece
                                    log.append(p)
                                    peers.append(p.ip)
                                    continue

                            if ip_address(peer_ip).version == 4:  # IPv4アドレスの場合
                                if p.ip not in peers and _ip_in_range(
                                    peer_ip, ipv4_ranges
                                ):
                                    p.timestamp = timestamp
                                    p.valid = valid_piece
                                    log.append(p)
                                    peers.append(p.ip)

                            elif ip_address(peer_ip).version == 6:
                                # excluded_ipv6_networkがNoneでないかどうかを確認
                                is_not_in_self_network = True
                                if excluded_ipv6_network is not None:
                                    is_not_in_self_network = (
                                        ip_address(peer_ip) not in excluded_ipv6_network
                                    )

                                # その他の条件と組み合わせる
                                if is_not_in_self_network and _ip_in_range(
                                    peer_ip, ipv6_ranges
                                ):
                                    p.timestamp = timestamp
                                    p.valid = valid_piece
                                    log.append(p)
                                    peers.append(p.ip)
                    except Exception as e:
                        self.logger.warning(f"ループ中に例外が発生: {e}")

                    cnt += 1
                    if len(peers) == max_list_size:
                        self.logger.info("取得ピア数の上限に達しました。")
                        break

                    if _over_progress(handle):
                        self.logger.info(
                            "ダウンロードの進捗が50%を超えたため、ピア取得を中断します。(ループ" + str(cnt + 1) + "回目)"
                        )
                        break

                    time.sleep(3)

        except Exception:
            logging.info("一時ファイルの削除を試行中...")
            try:
                parent_dir = os.path.dirname(tmpdir)
                # 親ディレクトリを削除
                if os.path.exists(parent_dir):
                    shutil.rmtree(parent_dir)

            except Exception as e:
                logging.warning(f"一時ファイルの削除に失敗しました: {e}")

        logging.info("取得ピア数：" + str(len(peers)))
        logging.info("ログを記録しています...")
        if log:
            save_path = os.path.dirname(torrent_path)
            _save_peer_log(log, info, save_path, self.version)

        return log

    def download_piece(
        self,
        session,
        matcher,
        info,
        ip_filter,
        save_path: str,
        peer: tuple[str, int],
        version: str,
    ) -> None:
        """
        指定したピアからピースをダウンロードする。

        Parameters
        ----------
        session : lt.session
            ダウンロード用のセッション。
        matcher : Binarymatcher
            ピースのバイナリマッチ検査用インスタンス。
        info : lt.torrent_info
            トレント情報。
        ip_filter : lt.ip_filter
            IPフィルタ。
        save_path : str
            ピースを保存するディレクトリのパス。
        peer : tuple[str, int]
            ピースをダウンロードするピア。
        version : str
            P2Pクローラのバージョン情報。
        """

        # 指定されたピアのみからダウンロード
        ip_filter.add_rule(peer[0], peer[0], 0)
        session.set_ip_filter(ip_filter)

        # Debug log
        self.logger.debug(f"IP Filter added for peer: {peer[0]}")

        handle = session.add_torrent({"ti": info, "save_path": save_path})

        # Debug log
        self.logger.debug(f"Torrent handle status: {handle.status()}")

        # 全てのピースからランダムに1つ選ぶ
        piece_index = random.randint(0, info.num_pieces() - 1)

        # 指定したindexのみpriorityを非ゼロにする
        pp = [0] * info.num_pieces()
        pp[piece_index] = 1
        handle.prioritize_pieces(pp)

        a = handle.read_piece(piece_index)

        for _ in range(10):  # 10回リトライ
            alerts = session.pop_alerts()
            for a in alerts:
                if isinstance(a, lt.read_piece_alert):
                    # ピースのデータを取得
                    a = a.buffer
                    break
            else:
                time.sleep(1)  # 1秒待機して再度アラートを確認
                continue
            break
        else:
            self.logger.warning("read_piece_alert が受信されませんでした。")
            return

        # ダウンロードが完了した瞬間のタイムスタンプを記録
        completed_timestamp = ut.get_jst_str()

        error_prefix = ""
        log_error_message = ""
        valid_piece = False

        # ピースサイズが0かどうかをチェック
        if a is None or len(a) == 0:
            self.logger.warning("ピースサイズが0でした。通信エラーがあった可能性があります。")
            error_prefix = "BLANK_"
            log_error_message = " エラー：ピースダウンロード失敗 "

        else:
            # ダウンロードしたピースのハッシュを計算
            downloaded_piece_hash = _calculate_piece_hash(a)
            # 元の.torrentファイルのハッシュを取得
            original_piece_hash = info.hash_for_piece(piece_index)

            # 二つのハッシュを比較
            if downloaded_piece_hash != original_piece_hash:
                self.logger.warning("ダウンロードしたピースのハッシュが一致しません。ピースが破損している可能性があります。")
                error_prefix = "FALSE_"
                log_error_message = " エラー：ピースハッシュ不一致 "
            else:
                match_result = matcher.instant_binary_match(a, piece_index)
                # instant_binary_matchの結果に基づいて処理を分岐
                if match_result is False:
                    self.logger.warning(
                        "ダウンロードしたピースのバイナリが一致しません。Torrentファイル、または本体ファイルの内容が不正な可能性があります。"
                    )
                    error_prefix = "INVALID_"
                    log_error_message = " エラー：バイナリ不一致 "
                elif isinstance(match_result, (int, float)):
                    self.logger.info(f"{peer[0]}からピース{piece_index}のダウンロードに成功。")
                    valid_piece = True

        # ピア・ピースの情報を文字列として整理
        peer_modified = peer[0].replace(":", "-") if ":" in peer[0] else peer[0]

        file_path = os.path.join(
            save_path,
            f"{peer_modified}_{str(peer[1])}",
            "{}{:05}_{}_{}_{}.bin".format(
                error_prefix, piece_index, peer_modified, peer[1], info.info_hash()
            ),
        )

        # 証拠フォルダ内のピアを一覧するためのデータ、peer_(info_hash).csvを編集
        csv_path = os.path.join(save_path, "peer_" + str(info.info_hash()) + ".csv")
        log_path = os.path.join(
            save_path,
            f"{peer_modified}_{str(peer[1])}",
            "{}_{}_{}.log".format(peer_modified, str(peer[1]), info.info_hash()),
        )
        if not os.path.exists(log_path):
            provider = _query_jpnic_whois(peer[0])
            time.sleep(5)
        else:
            provider = ""

        peer_csv = _save_peers_info(
            peer,
            provider,
            completed_timestamp,
            valid_piece,
            csv_path,
        )

        if not peer_csv:
            return

        unique_file_path = _get_unique_filename(file_path)

        # 保存オプションがONのとき、ピース実物を保存
        if self.piece_download:
            _write_piece_to_file(a, unique_file_path)

        _write_piece_log(
            info,
            peer,
            piece_index,
            log_path,
            provider,
            completed_timestamp,
            log_error_message,
            version,
        )


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _default_ip_filter(torrent_path: str) -> tuple:
    # IPフィルタを作成
    ip_filter = lt.ip_filter()
    # 最初にすべてのアドレスを禁止し、以降は許可した範囲とだけ接続する
    ip_filter.add_rule("0.0.0.0", "255.255.255.255", 1)
    ip_filter.add_rule("::", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", 1)

    # torrentファイルを読み込む
    info = lt.torrent_info(torrent_path)

    # トラッカーの一覧を取得
    trackers = info.trackers()

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
            # ホスト名を解決できない場合、スキップ
            pass
    return ip_filter


def _add_ip_ranges_to_filter(ip_filter, ip_ranges, allow=True):
    # IPフィルタに範囲を追加する関数
    for ip_range in ip_ranges:
        # IPアドレス範囲の開始と終了を取得
        start = str(ip_range[0])
        end = str(ip_range[-1])
        # 許可する場合は0、禁止する場合は1を使用
        ip_filter.add_rule(start, end, 0 if allow else 1)


def _format_timestamp_str(timestamp):
    timestamp = timestamp.replace(" ", "-")
    timestamp = timestamp.replace(":", "-")
    formatted_timestamp = timestamp.split(".")[0]
    return formatted_timestamp


def _save_peer_log(log, info, save_path: str, version: str):
    # save_path内のファイルをリストアップ
    csv_name = f"peers_{info.info_hash()}.csv"
    csv_path = os.path.join(save_path, csv_name)

    # ログの生データを記録
    for p in log:
        peer = p.ip
        _make_peers_list(peer, p.timestamp, p.valid, csv_path)

    # ピア別のログ記録
    for p in log:
        peers_folder = os.path.join(save_path, "peers")
        if not os.path.exists(peers_folder):
            os.makedirs(peers_folder, exist_ok=True)

        # peer_infoオブジェクトの値を文字列に変換
        port = str(p.ip[1])
        client = p.client.decode("utf-8")
        speed = str(p.up_speed)
        if not p.valid:
            validity_str = "破損ピース：あり"
        else:
            validity_str = ""  # 破損ピースがなかった場合、なにも記入しない

        log_line = (
            p.timestamp + "　" + client + "　速度：" + speed + " KB/s　" + validity_str + "\n"
        )

        # ファイル名を決定
        peer_modified = p.ip[0].replace(":", "-") if ":" in p.ip[0] else p.ip[0]
        peer_file_name = (
            peer_modified + "_" + port + "_" + str(info.info_hash()) + ".log"
        )

        peer_file_path = os.path.join(peers_folder, peer_file_name)
        if not os.path.exists(peer_file_path):
            file_mode = "w"
        else:
            file_mode = "a"

        with open(peer_file_path, file_mode) as f:
            if file_mode == "w":
                # 新規ファイルの場合はヘッダーを書き込み
                f.write(f"IPアドレス：{p.ip[0]}\n")
                f.write(f"ポート番号：{port}\n")
                f.write(f"クライアント：{client}\n")
                f.write("プロバイダ：未取得\n")
                f.write(f"ファイル名：{info.name()}\n")
                f.write(f"ファイルハッシュ: {info.info_hash()}\n")
                f.write(f"証拠収集開始時刻: {p.timestamp}\n")
                f.write(f"P2Pクローラ {version}\n")
                f.write("------------------------------------\n")

            f.write(log_line)


def _over_progress(handle):
    status = handle.status()  # トレントの現在の状態を取得
    # ダウンロード進捗状況（割合）を計算
    progress = status.progress * 100  # 進捗状況をパーセンテージで表す
    # 進捗が50%以上の場合、いったん一時ファイルを削除
    if progress >= 50.0:
        return True


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


def _calculate_piece_hash(piece_data: bytes) -> bytes:
    """
    ピースのデータからSHA-1ハッシュを計算する。
    Parameters
    ----------
    piece_data : bytes
        ピースのデータ。
    Returns
    -------
    bytes
        計算されたSHA-1ハッシュ。
    """
    sha1 = hashlib.sha1()
    sha1.update(piece_data)
    return sha1.digest()


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


def _write_piece_log(
    info,
    peer,
    piece_index,
    log_path,
    provider,
    completed_timestamp,
    log_error_message="",
    version="",
):
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

    # ファイルを開く前にディレクトリの存在を確認
    save_dir = os.path.dirname(log_path)
    if not os.path.exists(save_dir):
        os.makedirs(save_dir, exist_ok=True)

    if not os.path.exists(log_path):
        file_mode = "w"
    else:
        file_mode = "a"

    with open(log_path, file_mode) as f:
        if file_mode == "w":
            # 新規ファイルの場合はヘッダーを書き込み
            f.write(f"IPアドレス：{peer[0]}\n")
            f.write(f"ポート番号：{peer[1]}\n")
            f.write(f"プロバイダ：{provider}\n")
            f.write(f"ファイル名：{info.name()}\n")
            f.write(f"ファイルハッシュ: {info.info_hash()}\n")
            f.write(f"証拠収集開始時刻: {completed_timestamp}\n")
            f.write(f"P2Pクローラ {version}\n")
            f.write("---\n")

        f.write(
            f"piece{piece_index}{log_error_message} 完了時刻: {completed_timestamp} {version}\n"
        )


def _make_peers_list(
    peer: tuple[str, int], timestamp: str, valid_piece: bool, csv_path: str
) -> None:
    """
    ピアの一覧をファイルに記録または更新する。

    Parameters
    ----------
    peer : (str, int)
        ピアを表すタプル。
    timestamp : str
        完了タイムスタンプ。
    valid_piece : bool
        取得できたのが正常なピースかどうか。
    csv_path : str
        記録ファイルのパス。
    """
    provider = "未取得"
    remote_host = "未取得"
    num = 1 if valid_piece else 0
    updated = False

    new_data = []

    try:
        if os.path.exists(csv_path):
            with open(csv_path, "r+", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if row[:2] == [peer[0], str(peer[1])]:
                        row[4] = str(int(row[4]) + num) if valid_piece else row[4]
                        row[6] = timestamp
                        updated = True
                    new_data.append(row)

                f.seek(0)  # ファイルポインタを先頭に戻す
                f.truncate()  # ファイル内容を削除

                writer = csv.writer(f)
                for row in new_data:
                    writer.writerow(row)

                if not updated:
                    # ピアが新規である場合は追加
                    writer.writerow(
                        peer + (provider, remote_host, num, timestamp, timestamp)
                    )
        else:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    peer + (provider, remote_host, num, timestamp, timestamp)
                )

    except PermissionError:
        logger.warning("パーミッションエラー：ピア履歴のcsvに書き込みできません。ファイルが開かれている場合は閉じてください。")
        return False  # download_pieceを中断するための戻り値


def _save_peers_info(
    peer: tuple[str, int],
    provider: str,
    completed_timestamp: str,
    valid_piece: bool,
    csv_path: str,
) -> None:
    """
    ピアの一覧をファイルに記録または更新する。

    Parameters
    ----------
    peer : (str, int)
        ピアを表すタプル。
    provider : str
        プロバイダ情報。
    completed_timestamp : str
        完了タイムスタンプ。
    valid_piece : bool
        取得できたのが正常なピースかどうか。
    save_path : str
        記録ファイルのパス。
    """
    updated = False
    new_data = []

    if valid_piece:
        num = 1
    else:
        num = 0

    if os.path.exists(csv_path):
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                # peerのIPアドレスとポート番号が一致する行を見つけたら
                if row[:2] == [peer[0], str(peer[1])]:
                    # 5列目のみcompleted_timestampで更新
                    row[5] = completed_timestamp
                    updated = True
                new_data.append(row)

    try:
        # ピアが既存であった場合は、更新されたデータでファイルを上書き
        if updated:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                for row in new_data:
                    # peerが一致し、valid_pieceがTrueの場合に3列目を更新
                    if row[:2] == [peer[0], str(peer[1])] and valid_piece:
                        try:
                            # 4列目を数値に変換して1を加える
                            row[3] = str(int(row[3]) + 1)
                        except ValueError:
                            # 3列目が数値でなければエラーメッセージを表示
                            logger.warning("csvデータ上の値が数値ではないため、書き込みできませんでした。")
                            continue  # 次の行の処理を続ける
                    writer.writerow(row)
        else:
            # ピアが新規である場合は追加
            with open(csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                # 新しいピア情報を追加
                writer.writerow(
                    peer + (provider, num, completed_timestamp, completed_timestamp)
                )

        return True

    except PermissionError:
        logger.warning("パーミッションエラー：ピア履歴のcsvに書き込みできません。ファイルが開かれている場合は閉じてください。")
        return False  # download_pieceを中断するための戻り値


def get_excluded_ipv6(ipv6):
    # IPv6アドレスの第4セグメントまでを抽出する関数
    ipv6_segments = ipv6.split(":")[:4]  # IPv6アドレスの最初の4つのセグメントを取得
    # すべてのセグメントが空でないことを確認
    if all(segment for segment in ipv6_segments):
        return ip_network(":".join(ipv6_segments) + "::/64")
    else:
        # 条件に合致しない場合の処理
        return None


# IPv6アドレスの第4セグメントまでを抽出する関数
def extract_ipv6_segment(ipv6):
    try:
        segments = ip_address(ipv6).exploded.split(":")[:4]
        return ":".join(segments)
    except ValueError:
        return None


# peersリストに同じIPv6セグメントが存在するか確認する関数
def is_segment_in_peers(ipv6, peers_list):
    segment_to_check = extract_ipv6_segment(ipv6)
    if segment_to_check is None:
        return False
    for peer in peers_list:
        if extract_ipv6_segment(peer[0]) == segment_to_check:
            return True
    return False


def read_piece_download_setting():
    # IP範囲をファイルから読み込む
    current_dir = os.path.dirname(os.path.abspath(__file__))
    con = Config(base_path=current_dir, level=1)

    SETTING_FILE = con.SETTING_FILE

    # ファイルを開いて、JSONをパース
    with open(SETTING_FILE, "r", encoding="utf-8") as f:
        settings = json.load(f)

    # "piece_download" の値を取得して返す
    return settings.get("piece_download", None)


def load_ip_ranges(version: int) -> list:
    # IP範囲をファイルから読み込む
    current_dir = os.path.dirname(os.path.abspath(__file__))
    con = Config(base_path=current_dir, level=1)

    SETTING_FOLDER = con.SETTING_FOLDER

    ip_range_file = os.path.join(
        SETTING_FOLDER, "ipv4.txt" if version == 4 else "ipv6.txt"
    )

    if not os.path.exists(ip_range_file):
        return []

    with open(ip_range_file, "r") as f:
        ip_ranges = [
            ipaddress.ip_network(line.strip(), strict=False) for line in f.readlines()
        ]

    return ip_ranges


def _ip_in_range(ip: str, ip_ranges: list) -> bool:
    """
    指定されたIPアドレスが、設定ファイル（ipv4.txt, ipv6.txt）の範囲に収まっているかを返す。

    Parameters
    ----------
    ip : str
        判定対象のIPアドレス。
    ip_ranges : list
        load_ip_rangesで取得したIPアドレス範囲の設定。
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
    except ValueError:
        logger.warning(f"{ip} はIPアドレスとして不正な形式です。")
        return False

    for ip_range in ip_ranges:
        if ip_obj in ip_range:
            return True

    return False


def _get_remote_host(ip_str):
    try:
        # IPアドレスの形式を確認（IPv4またはIPv6）
        ip = ipaddress.ip_address(ip_str)

        # リバースDNSルックアップを実行してホスト名を取得
        host_name = socket.gethostbyaddr(ip_str)[0]
        return host_name
    except ValueError:
        return "取得失敗"
    except Exception as e:
        logger.warnin(f"ホスト名の取得に失敗しました: {e}")
        return "取得失敗"


def _get_public_ips() -> tuple[str, str]:
    """
    現在のIPv4とIPv6アドレスを取得する。

    Returns
    -------
    tuple:
        現在のIPv4, IPv6アドレスのタプル。
    """
    ipv4, ipv6 = None, None
    # IPv4アドレスの取得
    try:
        response_ipv4 = requests.get("https://api.ipify.org?format=json")
        response_ipv4.raise_for_status()
        ipv4 = response_ipv4.json().get("ip")
        time.sleep(1)
    except RequestException as e:
        logger.warning(f"IPv4の取得に失敗しました: {e}")

    # IPv6アドレスの取得
    try:
        response_ipv6 = requests.get("https://api6.ipify.org?format=json")
        response_ipv6.raise_for_status()
        ipv6 = response_ipv6.json().get("ip")
    except RequestException as e:
        logger.warning(f"IPv6の取得に失敗しました: {e}")

    return ipv4, ipv6


def _query_jpnic_whois(ip_address):
    # JPNICのWHOISサービスに接続
    whois_server = "whois.nic.ad.jp"
    whois_port = 43

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((whois_server, whois_port))
        sock.send((ip_address + "\r\n").encode("utf-8"))

        data = b""
        while True:
            buffer = sock.recv(4096)
            if not buffer:
                break
            data += buffer
    except ConnectionResetError:
        logger.warning("プロバイダ取得エラー：Whoisサーバーによって接続がリセットされました。")
        return "取得失敗（Whoisサーバーからの拒否）"
    except socket.error as e:
        logger.warning(f"プロバイダ取得エラー：ソケットエラーが発生しました: {e}")
        return "取得失敗（ソケットエラー）"
    finally:
        sock.close()

    result = data.decode("iso-2022-jp", "ignore")

    match = re.search(r"\[組織名\]\s+(.+)", result)
    if match:
        provider = match.group(1)
        if provider == "":
            provider = "取得失敗（不明）"
        return provider
    else:
        return "取得失敗(JPNIC管理外)"


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
