import libtorrent as lt


def show_info(torrent_name):
    """
    トレントファイルの情報を表示する。

    Parameters
    ----------
    torrent_name : str
        トレントファイル名。
    """

    torrent_info = lt.torrent_info(torrent_name)

    # Torrentの名前を取得する
    name = torrent_info.name
    print(f'Torrentの名前: {name}')

    # Torrentのファイル数を取得する
    num_files = torrent_info.num_files()
    print(f'Torrentのファイル数: {num_files}')

    # Torrentの作成者を取得する
    created_by = torrent_info.creator()
    print(f'Torrentの作成者: {created_by}')

    # Torrentの総サイズを取得する
    total_size = torrent_info.total_size()
    print(f'Torrentの総サイズ: {total_size} bytes')
