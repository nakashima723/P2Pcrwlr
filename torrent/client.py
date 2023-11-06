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

        session = lt.session({"listen_interfaces": "0.0.0.0:6881,[::]:6881"})
        self.logger.info("本体ファイル" + target_file_path + "のダウンロードを行います。")

        # 最大アップロード速度を0KB/sに設定
        session.set_upload_rate_limit(0)

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

        # 最大アップロード速度を0KB/sに設定
        session.set_upload_rate_limit(0)

        peers: list[tuple[str, int]] = []

        # 自分のIPを取得する_get_public_ips()を呼び出し、結果を2つの変数に格納
        ipv4, ipv6 = _get_public_ips()

        # IPv6アドレスの最初の4つのセクションを取得して除外リストに追加
        if ipv6:
            excluded_ipv6_network = ip_network(":".join(ipv6.split(":")[:4]) + "::/64")

        # 対象をIPアドレスリストの範囲に限定（IPv4とIPv6）
        ipv4_ranges = load_ip_ranges(4)
        ipv6_ranges = load_ip_ranges(6)

        # IP範囲ファイルが両方とも存在しない場合にすべてのピアを追加するフラグ
        add_all_peers = not ipv4_ranges and not ipv6_ranges

        # 一時ディレクトリの削除に関するエラーハンドリングを追加する
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                handle = session.add_torrent({"ti": info, "save_path": tmpdir})
                cnt = 0
                while cnt < RETRY_COUNTER:
                    try:
                        peer_info_list = handle.get_peer_info()
                        for p in peer_info_list:
                            peer_ip = p.ip[0]

                            # 全てのピアを追加するフラグが真の場合、条件を無視して追加
                            if add_all_peers:
                                if p.seed and p.ip not in peers:
                                    peers.append(p.ip)
                            else:
                                if (
                                    p.seed
                                    and p.ip not in peers
                                    and peer_ip != ipv4
                                    and (
                                        not ipv6
                                        or not ip_address(peer_ip)
                                        in excluded_ipv6_network
                                    )
                                ):  # 除外範囲のチェック
                                    # 範囲フィルタリング
                                    if _ip_in_range(
                                        peer_ip, ipv4_ranges
                                    ) or _ip_in_range(peer_ip, ipv6_ranges):
                                        peers.append(p.ip)

                    except Exception as e:
                        self.logger.warning(f"ループ中に例外が発生: {e}")

                    cnt += 1
                    time.sleep(1)
                return peers[:max_list_size]

        except Exception as e:
            # 一時ディレクトリの削除に失敗した場合、ログに表示する
            logging.error(f"一時ファイルの削除に失敗しました。: {e}")
            # 処理を続行するために、例外をここでキャッチして処理をスキップする
            return peers[:max_list_size]

        finally:
            # finallyブロックで一時ディレクトリの削除を確実に実行
            if tmpdir and os.path.exists(tmpdir):
                try:
                    shutil.rmtree(tmpdir)
                except Exception as e:
                    logging.error(f"明示的な一時ファイルの削除に失敗しました。: {e}")

    def setup_session(self, torrent_path: str) -> tuple:
        """
        ピースダウンロード用に、torrentファイルと関連する初期設定を行う。

        Parameters
        ----------
        torrent_path : str
            .torrentファイルへのパス。

        Returns
        -------
        tuple:
            セッション、トレント情報、IPフィルタのタプル。
        """
        # 基本のセッションとIPフィルタを定義
        session = lt.session({"listen_interfaces": "0.0.0.0:6881,[::]:6881"})

        # アップロード量を0に設定
        session.set_upload_rate_limit(0)

        # torrentファイルを読み込む
        info = lt.torrent_info(torrent_path)

        # トラッカーの一覧を取得
        trackers = info.trackers()

        # IPフィルタを作成
        ip_filter = lt.ip_filter()
        # すべてのアドレスを禁止
        ip_filter.add_rule("0.0.0.0", "255.255.255.255", 1)
        ip_filter.add_rule("::", "ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff", 1)

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
        return session, info, ip_filter

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
            time.sleep(1)
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

        _write_peer_log(
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


def _write_peer_log(
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
