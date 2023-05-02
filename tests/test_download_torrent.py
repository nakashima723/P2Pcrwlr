import unittest
import os
import urllib.request
import pathlib
from torrent.client import Client


class TestClient(unittest.TestCase):
    TEST_DIR = os.path.join(pathlib.Path(__file__).parent, 'evidence', 'torrent')
    FOLDER_NAME = 'Big Buck Bunny'
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

    def test_download(self):
        cl = Client()
        cl.download(os.path.join(self.TEST_DIR, self.FILE_NAME),
                    os.path.join(self.TEST_DIR, self.FOLDER_NAME))

    def test_fetch_peer_list(self):
        cl = Client()
        max_list_size = 10
        peers = cl.fetch_peer_list(os.path.join(self.TEST_DIR, self.FILE_NAME), max_list_size)
        print(peers)
        self.assertTrue(len(peers) == max_list_size)

    def test_save_num_complete(self):
        cl = Client()

        cl.save_num_complete(
            os.path.join(self.TEST_DIR, self.FILE_NAME),
            os.path.join(self.TEST_DIR, self.FOLDER_NAME)
        )

    def test_download_piece(self):
        cl = Client()

        peers = cl.fetch_peer_list(os.path.join(self.TEST_DIR, self.FILE_NAME), max_list_size=3)

        for p in peers:
            print('download from {}'.format(p))
            cl.download_piece(
                os.path.join(self.TEST_DIR, self.FILE_NAME),
                os.path.join(self.TEST_DIR, self.FOLDER_NAME),
                0,
                p
            )


if __name__ == "__main__":
    unittest.main()
