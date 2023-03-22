import unittest
import os
import libtorrent as lt
import urllib.request
import info


class TestInfo(unittest.TestCase):
    TEST_DIR = 'torrent/tests'

    def test_show_info(self):
        # テスト用にCreative Commons torrentを用いる
        # Big Buck Bunny
        # Blender Foundation | www.blender.org
        url = 'https://webtorrent.io/torrents/big-buck-bunny.torrent'
        save_name = os.path.join(self.TEST_DIR, 'big-buck-bunny.torrent')

        # 現状、プロジェクト直下に.torrentファイルが落ちてくる
        urllib.request.urlretrieve(url, save_name)

        info.show_info(lt.torrent_info(save_name))


if __name__ == "__main__":
    unittest.main()
