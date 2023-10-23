import os
import sys
from pathlib import Path


class Config:
    def __init__(self, base_path=None, level=0):
        if getattr(sys, "frozen", False):
            self.application_path = Path(sys._MEIPASS)
        else:
            if base_path:
                self.application_path = Path(base_path)
            else:
                self.application_path = Path(os.path.dirname(os.path.abspath(sys.argv[0])))
            
            for _ in range(level):
                self.application_path = self.application_path.parent

        self.EVI_FOLDER = os.path.join(self.application_path, "evi")
        self.TORRENT_FOLDER = os.path.join(self.EVI_FOLDER, "tor")
        self.SETTING_FOLDER = os.path.join(self.application_path, "settings")
        self.SETTING_FILE = os.path.join(self.SETTING_FOLDER, "setting.json")
        self.QUERIES_FILE = os.path.join(self.SETTING_FOLDER, "queries.json")
        self.R18_QUERIES_FILE = os.path.join(self.SETTING_FOLDER, "r18queries.json")
        self.SCRAPER_FILE = os.path.join(self.application_path, "crawler/scraper.py")
        self.COLLECTOR_FILE = os.path.join(self.application_path, "crawler/collector.py")
        self.FETCH_IP_FILE = os.path.join(self.application_path, "crawler/fetch_ip_list.py")
        self.COMPLETE_EVI_FILE = os.path.join(self.application_path, "crawler/get_complete_evidence.py")
