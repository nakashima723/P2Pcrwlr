import libtorrent as lt
import time


class Client():

    SAVE_PATH = "torrent/downloads"

    def download(self, torrent_path):
        """
        torrentファイルを読み込み、本体ファイルをダウンロードする。

        Parameters
        ----------
        torrent_path : str
        ダウンロードを行うtorrentファイルへのパス。
        """

        session = lt.session({'listen_interfaces': '0.0.0.0:6881'})

        info = lt.torrent_info(torrent_path)
        handle = session.add_torrent({'ti': info, 'save_path': self.SAVE_PATH})

        print('starting', handle.status().name)

        while not handle.is_seed():
            s = handle.status()

            print("downloading: %.2f%% complete (down: %.1f kB/s, up: %.1f kB/s, peers: %d) %s" % (
                s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000,
                s.num_peers, s.state))

            time.sleep(1)

        print(handle.status().name, 'complete')
