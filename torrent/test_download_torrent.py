import unittest
import os
import libtorrent as lt
import urllib.request
import client


class TestInfo(unittest.TestCase):
    TEST_DIR = 'torrent/tests'
    DOWNLOAD_DIR = 'downloads'
    FILE_NAME = 'big-buck-bunny.torrent'

    @classmethod
    def setUpClass(self):
        # テスト用にCreative Commons torrent をダウンロードする
        # Big Buck Bunny
        # Blender Foundation | www.blender.org
        url = 'https://webtorrent.io/torrents/big-buck-bunny.torrent'

        urllib.request.urlretrieve(
            url, os.path.join(self.TEST_DIR, self.FILE_NAME))

    # 現状、各メソッドを実行するだけで、assertionしていない。

    def test_client(self):
        cl = client.Client()
        cl.download(os.path.join(self.TEST_DIR, self.FILE_NAME),
                    os.path.join(self.TEST_DIR, self.DOWNLOAD_DIR))

    def test_download_piece(self):
        cl = client.Client()
        cl.download_piece(
            os.path.join(self.TEST_DIR, self.FILE_NAME),
            os.path.join(self.TEST_DIR, self.DOWNLOAD_DIR, 'pieces'),
            0
        )


if __name__ == "__main__":
    unittest.main()
