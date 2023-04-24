import unittest
import os
import libtorrent as lt
import urllib.request
import client
import csv
import pathlib


class TestClient(unittest.TestCase):
    TEST_DIR = os.path.join(pathlib.Path(__file__).parent,
                            'tests', 'evidence', 'torrent')
    FOLDER_NAME = 'Big Buck Bunny'
    FILE_NAME = 'big-buck-bunny.torrent'

    @classmethod
    def setUpClass(self):
        # テスト用にCreative Commons torrent をダウンロードする
        # Big Buck Bunny
        # Blender Foundation | www.blender.org
        url = 'https://webtorrent.io/torrents/big-buck-bunny.torrent'

        urllib.request.urlretrieve(
            url, os.path.join(self.TEST_DIR, self.FOLDER_NAME, self.FILE_NAME))

    # 現状、各メソッドを実行するだけで、assertionしていない。

    def test_download(self):
        cl = client.Client()
        cl.download(os.path.join(self.TEST_DIR, self.FOLDER_NAME, self.FILE_NAME),
                    os.path.join(self.TEST_DIR, self.FOLDER_NAME))

    def test_download_piece(self):
        cl = client.Client()

        peers = []
        with open(os.path.join(self.TEST_DIR, self.FOLDER_NAME, 'peer.csv'), newline='') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                # (IPアドレス : string, ポート : int) という型のタプルにする
                peers.append((row[0], int(row[1])))

        for p in peers:
            print('download from {}'.format(p))
            cl.download_piece(
                os.path.join(self.TEST_DIR, self.FOLDER_NAME, self.FILE_NAME),
                os.path.join(self.TEST_DIR, self.FOLDER_NAME, f'{p[0]}_{str(p[1])}'),
                0,
                p
            )


if __name__ == "__main__":
    unittest.main()
